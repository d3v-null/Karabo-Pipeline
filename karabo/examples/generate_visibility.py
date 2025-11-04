#!/usr/bin/env python3
"""
CLI tool to generate visibility files using Karabo simulation.

This script generates simulated visibility data for a specified telescope,
observation parameters, and outputs either MS or UVFITS format.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from karabo.simulation.interferometer import InterferometerSimulation
from karabo.simulation.observation import Observation
from karabo.simulation.sky_model import SkyModel
from karabo.simulation.telescope import Telescope
from karabo.simulation.telescope_versions import (
    MWAVersion,
    SKAMidAAStarVersions,
)
from karabo.simulator_backend import SimulatorBackend


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate visibility files using Karabo simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate MWA Phase 1 visibility in MS format
  %(prog)s --telescope MWA --telescope-version 1 \\
    --midpoint-time "2020-01-01T12:00:00" \\
    --num-timesteps 10 --mid-frequency 170e6 \\
    --num-channels 16 --time-resolution 8.0 \\
    --frequency-resolution 80e3 --out output.MS

  # Generate MWA Phase 2 extended visibility
  %(prog)s --telescope MWA --telescope-version 2ext \\
    --midpoint-time "2020-01-01T12:00:00" \\
    --num-timesteps 10 --mid-frequency 170e6 \\
    --num-channels 16 --time-resolution 8.0 \\
    --frequency-resolution 80e3 --out output.MS

  # Generate MeerKAT visibility in OSKAR_VIS format
  %(prog)s --telescope MeerKAT \\
    --midpoint-time "2020-04-26T18:36:00" \\
    --num-timesteps 100 --mid-frequency 1.34e9 \\
    --num-channels 256 --time-resolution 8.0 \\
    --frequency-resolution 26123 --out output.vis

  # Generate SKA-LOW-AA0.5 visibility
  %(prog)s --telescope SKA-LOW-AA0.5 \\
    --telescope-version ska-ost-array-config-2.3.1 \\
    --midpoint-time "2025-01-01T00:00:00" \\
    --mid-frequency 181e6 --frequency-resolution 80e3 \\
    --out output.MS
        """,
    )

    parser.add_argument(
        "--telescope",
        required=True,
        help=(
            "Telescope name (e.g., MWA, MeerKAT, ASKAP, SKA-Mid, SKA-Low, "
            "VLA, ALMA, etc.)"
        ),
    )

    parser.add_argument(
        "--telescope-version",
        help=(
            "Telescope version. Examples: "
            "'1' for MWA Phase 1, '2' or '2compact' for MWA Phase 2 compact, "
            "'2ext' or '2extended' for MWA Phase 2 extended, "
            "'AAstar' for SKA variants, "
            "'ska-ost-array-config-2.3.1' for SKA-LOW. "
            "Not required for all telescopes."
        ),
    )

    parser.add_argument(
        "--midpoint-time",
        required=True,
        help=(
            "Midpoint time of observation in ISO format (e.g., "
            "'2020-01-01T12:00:00' or '2020-01-01T12:00:00+00:00')"
        ),
    )

    parser.add_argument(
        "--num-timesteps",
        type=int,
        default=1,
        help="Number of time steps (correlator dumps)",
    )

    parser.add_argument(
        "--mid-frequency",
        type=float,
        required=True,
        help="Middle frequency in Hz (e.g., 170e6 for 170 MHz)",
    )

    parser.add_argument(
        "--num-channels",
        type=int,
        default=1,
        help="Number of frequency channels",
    )

    parser.add_argument(
        "--time-resolution",
        type=float,
        default=1.0,
        help="Time resolution (integration time per timestep) in seconds",
    )

    parser.add_argument(
        "--frequency-resolution",
        type=float,
        required=True,
        help="Frequency resolution (channel bandwidth) in Hz",
    )

    parser.add_argument(
        "--out",
        required=True,
        help=(
            "Output path. Format: .MS (Measurement Set) or .vis (OSKAR visibility). "
            "Note: UVFITS (.uvfits/.uvf) not yet supported with OSKAR backend."
        ),
    )

    parser.add_argument(
        "--phase-center-ra",
        type=float,
        default=0.0,
        help="Phase center Right Ascension in degrees (default: 0.0)",
    )

    parser.add_argument(
        "--phase-center-dec",
        type=float,
        default=-27.0,
        help="Phase center Declination in degrees (default: -27.0)",
    )

    parser.add_argument(
        "--sky-flux",
        type=float,
        default=1.0,
        help="Flux of the point source at phase center in Jy (default: 1.0)",
    )

    parser.add_argument(
        "--backend",
        choices=["OSKAR", "RASCIL"],
        default="OSKAR",
        help="Simulator backend to use (default: OSKAR)",
    )

    parser.add_argument(
        "--station-type",
        default="Isotropic beam",
        help=(
            "Station type for simulation (default: 'Isotropic beam'). "
            "Other options: 'Gaussian beam', 'Aperture array'"
        ),
    )

    parser.add_argument(
        "--use-gpus",
        action="store_true",
        help="Enable GPU acceleration (if available)",
    )

    return parser.parse_args()


def parse_telescope_version(telescope_name: str, version_str: Optional[str]):
    """Parse telescope version string into appropriate enum."""
    if version_str is None:
        return None

    telescope_name_upper = telescope_name.upper()

    # Handle MWA versions
    if "MWA" in telescope_name_upper:
        version_upper = version_str.upper()
        if version_upper in ("1", "ONE"):
            return MWAVersion.ONE
        elif version_upper in ("2", "TWO", "2COMPACT", "TWO_COMPACT", "TWO-COMPACT"):
            return MWAVersion.TWO_COMPACT
        elif version_upper in ("2EXT", "2EXTENDED", "TWO_EXTENDED", "TWO-EXTENDED",
                               "TWO_EXT", "TWO-EXT", "2_EXT", "2-EXT"):
            return MWAVersion.TWO_EXTENDED
        else:
            raise ValueError(
                f"Unknown MWA version: {version_str}. "
                f"Valid options: 1, 2/2compact, 2ext/2extended"
            )

    # Handle SKA-Mid versions
    if "SKA-MID" in telescope_name_upper or "SKAMID" in telescope_name_upper:
        version_upper = version_str.upper()
        if version_upper == "AASTAR":
            return SKAMidAAStarVersions.AAstar
        else:
            raise ValueError(f"Unknown SKA-Mid version: {version_str}")

    # Handle SKA-Low versions (including all AA configs)
    if "SKA-LOW" in telescope_name_upper or "SKALOW" in telescope_name_upper:
        version_upper = version_str.upper()
        # Handle SKA OST array config versions
        if "SKA-OST-ARRAY-CONFIG" in version_upper or "SKA_OST_ARRAY_CONFIG" in version_upper:
            # Import the specific version classes
            from karabo.simulation.telescope_versions import (
                SKALowAA0Point5Versions,
                SKALowAA1Versions,
                SKALowAA2Versions,
                SKALowAA4Versions,
                SKALowAAStarVersions,
            )
            # Normalize the version string to match enum
            version_enum_str = version_str.upper().replace("-", "_")

            # Try to find matching version in the appropriate AA config
            if "AA0.5" in telescope_name_upper or "AA0_5" in telescope_name_upper:
                for ver in SKALowAA0Point5Versions:
                    if ver.value.upper().replace("-", "_") == version_enum_str:
                        return ver
            elif "AASTAR" in telescope_name_upper or "AA_STAR" in telescope_name_upper:
                for ver in SKALowAAStarVersions:
                    if ver.value.upper().replace("-", "_") == version_enum_str:
                        return ver
            elif "AA1" in telescope_name_upper:
                for ver in SKALowAA1Versions:
                    if ver.value.upper().replace("-", "_") == version_enum_str:
                        return ver
            elif "AA2" in telescope_name_upper:
                for ver in SKALowAA2Versions:
                    if ver.value.upper().replace("-", "_") == version_enum_str:
                        return ver
            elif "AA4" in telescope_name_upper:
                for ver in SKALowAA4Versions:
                    if ver.value.upper().replace("-", "_") == version_enum_str:
                        return ver
        raise ValueError(f"Unknown SKA-Low version: {version_str}")

    return None


def validate_output_path(output_path: str, backend: str) -> tuple[str, str]:
    """Validate and normalize output path.

    Returns:
        Tuple of (output_path, visibility_format)
    """
    output_path_lower = output_path.lower()

    if output_path_lower.endswith(".ms"):
        return output_path, "MS"
    elif output_path_lower.endswith(".vis"):
        return output_path, "OSKAR_VIS"
    elif output_path_lower.endswith(".uvfits") or output_path_lower.endswith(".uvf"):
        if backend == "OSKAR":
            raise ValueError(
                "UVFITS format is not yet supported with OSKAR backend. "
                "Please use .MS or .vis format."
            )
        return output_path, "UVFITS"
    else:
        raise ValueError(
            "Output path must end with .MS, .vis, .uvfits, or .uvf"
        )

    return output_path, "MS"


def create_simple_sky_model(
    ra_deg: float, dec_deg: float, flux_jy: float, ref_freq_hz: float
) -> SkyModel:
    """Create a simple sky model with a single point source at phase center."""
    sky = SkyModel()

    # Create point source at phase center
    # Format: [RA, Dec, I, Q, U, V, ref_freq, spectral_index, RM,
    #          major_axis, minor_axis, PA, true_z, obs_z, source_id]
    source = np.array(
        [
            [
                ra_deg,  # RA in degrees
                dec_deg,  # Dec in degrees
                flux_jy,  # Stokes I flux in Jy
                0.0,  # Stokes Q flux
                0.0,  # Stokes U flux
                0.0,  # Stokes V flux
                ref_freq_hz,  # Reference frequency in Hz
                0.0,  # Spectral index
                0.0,  # Rotation measure
                0.0,  # Major axis FWHM (arcsec)
                0.0,  # Minor axis FWHM (arcsec)
                0.0,  # Position angle (deg)
                0.0,  # True redshift
                0.0,  # Observed redshift
                0,  # Source ID
            ]
        ]
    )

    sky.add_point_sources(source)
    return sky


def main():
    """Main function."""
    args = parse_args()

    # Validate output path
    try:
        output_path, visibility_format = validate_output_path(args.out, args.backend)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse backend
    backend = (
        SimulatorBackend.OSKAR
        if args.backend == "OSKAR"
        else SimulatorBackend.RASCIL
    )

    # Parse telescope version
    try:
        telescope_version = parse_telescope_version(
            args.telescope, args.telescope_version
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse midpoint time
    try:
        if "+" in args.midpoint_time or args.midpoint_time.endswith("Z"):
            midpoint_time = datetime.fromisoformat(
                args.midpoint_time.replace("Z", "+00:00")
            )
        else:
            midpoint_time = datetime.fromisoformat(args.midpoint_time).replace(
                tzinfo=timezone.utc
            )
    except ValueError as e:
        print(f"Error parsing midpoint time: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate observation parameters
    total_obs_length = timedelta(seconds=args.num_timesteps * args.time_resolution)
    start_time = midpoint_time - total_obs_length / 2

    # Calculate start frequency from middle frequency
    total_bandwidth = args.num_channels * args.frequency_resolution
    start_frequency = args.mid_frequency - total_bandwidth / 2

    print(f"Telescope: {args.telescope}", end="")
    if telescope_version:
        print(f" (version: {telescope_version})")
    else:
        print()
    print(f"Backend: {backend}")
    print(f"Phase center: RA={args.phase_center_ra}°, Dec={args.phase_center_dec}°")
    print(f"Observation start: {start_time}")
    print(f"Observation length: {total_obs_length}")
    print(f"Number of timesteps: {args.num_timesteps}")
    print(f"Time resolution: {args.time_resolution} s")
    print(
        f"Frequency range: {start_frequency / 1e6:.3f} - "
        f"{(start_frequency + total_bandwidth) / 1e6:.3f} MHz"
    )
    print(f"Number of channels: {args.num_channels}")
    print(f"Frequency resolution: {args.frequency_resolution / 1e3:.3f} kHz")
    print(f"Output: {output_path}")
    print()

    # Create telescope
    print("Creating telescope...")
    try:
        telescope = Telescope.constructor(
            name=args.telescope, version=telescope_version, backend=backend
        )
    except Exception as e:
        print(f"Error creating telescope: {e}", file=sys.stderr)
        sys.exit(1)

    # Create sky model
    print("Creating sky model...")
    sky_model = create_simple_sky_model(
        args.phase_center_ra,
        args.phase_center_dec,
        args.sky_flux,
        args.mid_frequency,
    )
    print(f"Sky model: {len(sky_model.sources)} source(s)")

    # Create interferometer simulation
    print("Setting up interferometer simulation...")
    simulation = InterferometerSimulation(
        channel_bandwidth_hz=args.frequency_resolution,
        station_type=args.station_type,
        use_gpus=args.use_gpus,
    )

    # Create observation
    print("Creating observation...")
    observation = Observation(
        phase_centre_ra_deg=args.phase_center_ra,
        phase_centre_dec_deg=args.phase_center_dec,
        start_date_and_time=start_time,
        length=total_obs_length,
        number_of_time_steps=args.num_timesteps,
        number_of_channels=args.num_channels,
        start_frequency_hz=start_frequency,
        frequency_increment_hz=args.frequency_resolution,
    )

    # Run simulation
    print("Running simulation...")
    print()
    try:
        visibility = simulation.run_simulation(
            telescope,
            sky_model,
            observation,
            backend=backend,
            visibility_format=visibility_format,
            visibility_path=output_path,
        )
        print()
        print(f"✓ Successfully generated visibility file: {output_path}")
        print(f"  Format: {visibility.format}")

    except Exception as e:
        print(f"\n✗ Error during simulation: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
