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

from astropy.table import Table
import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from tabulate import tabulate

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
        default=None,
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
        default=None,
        help="Phase center Right Ascension in degrees (default: use zenith)",
    )

    parser.add_argument(
        "--phase-center-dec",
        type=float,
        default=None,
        help="Phase center Declination in degrees (default: use zenith)",
    )

    parser.add_argument(
        "--sky-flux",
        type=float,
        default=1.0,
        help="Flux of the point source at phase center in Jy (default: 1.0)",
    )

    parser.add_argument(
        "--sky-model",
        help="Path to sky model CSV file. If not provided, a simple point source model is used.",
    )

    parser.add_argument(
        "--model-cutoff",
        type=float,
        default=None,
        help="Cutoff angle for sky model in degrees (default: no cutoff)",
    )

    parser.add_argument(
        "--model-flux-limit",
        type=float,
        default=None,
        help="minimum flux for sky model in Jy (default: no flux limit)",
    )

    parser.add_argument(
        "--model-count",
        type=float,
        default=None,
        help="maximum number of sources for sky model (default: no limit)",
    )

    parser.add_argument(
        "--backend",
        choices=["OSKAR", "RASCIL", "HYPERDRIVE"],
        default="OSKAR",
        help="Simulator backend to use (default: OSKAR)",
    )

    # --- Hyperdrive backend options ---
    parser.add_argument(
        "--hyperdrive-metafits",
        # don't commit me!
        default="/opt/mwa_hyperdrive_test_files/1090008640/1090008640.metafits",
        help=(
            "Path to an MWA metafits file (required for HYPERDRIVE backend). "
            "Example: /path/to/1090008640.metafits"
        ),
    )

    parser.add_argument(
        "--hyperdrive-bin",
        default="hyperdrive",
        help=(
            "Path to the hyperdrive binary (default: 'hyperdrive' from PATH). "
            "If you pass an absolute path, ensure its shared-library dependencies are available "
            "in the current environment."
        ),
    )

    # NOTE: Hyperdrive CPU/GPU selection reuses the existing --use-gpus flag.

    parser.add_argument(
        "--station-type",
        default="Isotropic beam",
        help=(
            "Station type for simulation (default: 'Isotropic beam'). "
            "Other options include: 'Gaussian beam', 'Aperture array', 'VLA (PBCOR)'.\n"
            "Note: For OSKAR, station/primary-beam effects are configured via the beam options below."
        ),
    )

    # --- Beam / station response options (OSKAR backend) ---
    parser.add_argument(
        "--enable-array-beam",
        action="store_true",
        help=(
            "Enable the aperture-array (station) array-factor contribution to the station beam "
            "(OSKAR: telescope.aperture_array/array_pattern/enable)."
        ),
    )

    parser.add_argument(
        "--enable-numerical-beam",
        action="store_true",
        help=(
            "Enable use of numerical element pattern data if available in the telescope model "
            "(OSKAR: telescope.aperture_array/element_pattern/enable_numerical)."
        ),
    )

    parser.add_argument(
        "--gauss-beam-fwhm-deg",
        type=float,
        default=0.0,
        help=(
            "Gaussian beam FWHM in degrees at the reference frequency. "
            "Only used when --station-type='Gaussian beam'."
        ),
    )

    parser.add_argument(
        "--gauss-ref-freq-hz",
        type=float,
        default=0.0,
        help=(
            "Reference frequency for --gauss-beam-fwhm-deg in Hz. "
            "Only used when --station-type='Gaussian beam'."
        ),
    )

    parser.add_argument(
        "--enable-power-pattern",
        action="store_true",
        help=(
            "Interpret --gauss-beam-fwhm-deg as a power-pattern FWHM rather than a field-pattern FWHM "
            "(Karabo will internally convert if required)."
        ),
    )

    parser.add_argument(
        "--use-gpus",
        action="store_true",
        help="Enable GPU acceleration (if available)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
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
    if args.backend == "OSKAR":
        backend = SimulatorBackend.OSKAR
    elif args.backend == "RASCIL":
        backend = SimulatorBackend.RASCIL
    elif args.backend == "HYPERDRIVE":
        backend = SimulatorBackend.HYPERDRIVE
    else:
        raise ValueError(f"Unknown backend: {args.backend}")

    if args.use_gpus and backend == SimulatorBackend.OSKAR:
        gpu_diagnostics()

    if backend == SimulatorBackend.HYPERDRIVE:
        # Hyperdrive is currently MWA-specific and requires a metafits file.
        if args.hyperdrive_metafits is None:
            print(
                "Error: --hyperdrive-metafits is required when --backend=HYPERDRIVE",
                file=sys.stderr,
            )
            sys.exit(1)
        if "MWA" not in args.telescope.upper():
            print(
                "Error: HYPERDRIVE backend currently supports only MWA telescopes",
                file=sys.stderr,
            )
            sys.exit(1)

    # Parse telescope version
    try:
        telescope_version = parse_telescope_version(
            args.telescope, args.telescope_version
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate start frequency from middle frequency
    total_bandwidth = args.num_channels * args.frequency_resolution
    start_frequency = args.mid_frequency - total_bandwidth / 2

    print(f"Telescope: {args.telescope}", end="")
    if telescope_version:
        print(f" (version: {telescope_version})")
    else:
        print()
    print(f"Backend: {backend}")

    # Create telescope
    print(f"Creating telescope name={args.telescope} ...")
    try:
        # Telescope model is primarily needed for OSKAR/RASCIL paths.
        # For the HYPERDRIVE simulation backend, we still construct the MWA telescope
        # using the OSKAR backend so we can reuse location info, etc.
        telescope_backend = backend
        if backend == SimulatorBackend.HYPERDRIVE:
            telescope_backend = SimulatorBackend.OSKAR

        telescope = Telescope.constructor(
            name=args.telescope, version=telescope_version, backend=telescope_backend
        )
    except Exception as e:
        print(f"Error creating telescope: {e}", file=sys.stderr)
        sys.exit(1)

    location = EarthLocation(
        lon=telescope.centre_longitude * u.deg,
        lat=telescope.centre_latitude * u.deg,
        height=telescope.centre_altitude * u.m,
    )

    # Parse midpoint time
    if args.midpoint_time is None:
        j2k_epoch = datetime.fromisoformat("1999-12-31T23:59:20+00:00")
        if args.phase_center_ra is None or args.phase_center_dec is None:
            print("No phase center or midpoint time provided", file=sys.stderr)
            sys.exit(1)
        else:
            source_coord = SkyCoord(ra=args.phase_center_ra * u.deg, dec=args.phase_center_dec * u.deg)

            # Calculate transit time nearest to J2000 epoch
            obs_time = Time(j2k_epoch, location=location)
            lst = obs_time.sidereal_time('apparent')

            # HA = LST - RA. Wrap at 12h to find nearest transit.
            ha = (lst - source_coord.ra).wrap_at(12 * u.hourangle)

            # Convert sidereal HA to solar time offset
            # 1 sidereal hour = 0.99726958 solar hours
            offset_solar_hours = -ha.to_value(u.hourangle) * 0.99726958

            transit_time = obs_time + offset_solar_hours * u.hour
            midpoint_time = transit_time.to_datetime(timezone.utc)
            args.midpoint_time = midpoint_time.isoformat()

            print(f"No midpoint time provided. Using transit time nearest J2000: {args.midpoint_time}", file=sys.stderr)
    else:
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

    obs_time = Time(midpoint_time)

    # default to zenith if phase center is not provided
    if args.phase_center_ra is None or args.phase_center_dec is None:
        zenith_azel = AltAz(0.0 * u.deg, 90.0 * u.deg, obstime=obs_time, location=location)
        zenith_radec = zenith_azel.transform_to(ICRS())
        args.phase_center_ra = zenith_radec.ra.deg
        args.phase_center_dec = zenith_radec.dec.deg

    print(f"Phase center: RA={args.phase_center_ra}°, Dec={args.phase_center_dec}°")

    # check if phase center is above the horizon
    source_coord = SkyCoord(ra=args.phase_center_ra * u.deg, dec=args.phase_center_dec * u.deg)
    altaz = source_coord.transform_to(AltAz(obstime=obs_time, location=location))
    elevation = altaz.alt.deg
    azimuth = altaz.az.deg
    print(f"Phase center elevation: {elevation}°, azimuth: {azimuth}°")
    if elevation < 0:
        print("WARNING: Phase center is below the horizon!")
        sys.exit(1)
    elif elevation < 10:
        print("WARNING: Phase center is very low on the horizon (< 10°).")
        sys.exit(1)
    else:
        print("Phase center is visible.")

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

    # Create sky model
    print("Creating sky model...")
    if args.sky_model:
        try:
            sky_model = SkyModel.read_from_file(args.sky_model)
        except Exception as e:
            print(f"Error reading sky model from {args.sky_model}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        sky_model = create_simple_sky_model(
            args.phase_center_ra,
            args.phase_center_dec,
            args.sky_flux,
            args.mid_frequency,
        )

    previous_count = len(sky_model.sources)

    if args.model_cutoff:
        sky_model = sky_model.filter_by_radius_euclidean_flat_approximation(0, args.model_cutoff, args.phase_center_ra, args.phase_center_dec)
        if len(sky_model.sources) != previous_count:
            print(f"Sky model: filtered {len(sky_model.sources)} of {previous_count} source(s) within {args.model_cutoff}° of phase center")
        previous_count = len(sky_model.sources)

    if args.model_flux_limit:
        sky_model = sky_model.filter_by_flux(args.model_flux_limit, np.inf)
        if len(sky_model.sources) != previous_count:
            print(f"Sky model: filtered {len(sky_model.sources)} of {previous_count} source(s) with flux greater than {args.model_flux_limit} Jy")
        previous_count = len(sky_model.sources)

    if args.model_count:
        sky_model = sky_model.limit_sources(args.model_count)
        if len(sky_model.sources) != previous_count:
            print(f"Sky model: limited to brightest {len(sky_model.sources)} of {previous_count} source(s)")
        previous_count = len(sky_model.sources)

    if previous_count != len(sky_model.sources):
        print(f"Sky model: {len(sky_model.sources)} source(s), showing up to 50:")
    # print sources

    print(tabulate(sky_model.sources[:50].values, headers=["ra", "dec", "i", "q", "u", "v", "ref_freq", "alpha", "rm", "maj", "min", "pa", "z_true", "z_obs", "id"], tablefmt="github"))

    # Create interferometer simulation
    print("Setting up interferometer simulation...")
    simulation = InterferometerSimulation(
        channel_bandwidth_hz=args.frequency_resolution,
        station_type=args.station_type,
        enable_array_beam=args.enable_array_beam,
        enable_numerical_beam=args.enable_numerical_beam,
        enable_power_pattern=args.enable_power_pattern,
        gauss_beam_fwhm_deg=args.gauss_beam_fwhm_deg,
        gauss_ref_freq_hz=args.gauss_ref_freq_hz,
        use_gpus=args.use_gpus,
        # Hyperdrive backend options (ignored unless backend=HYPERDRIVE)
        hyperdrive_metafits_path=args.hyperdrive_metafits,
        hyperdrive_bin=args.hyperdrive_bin,
        # Reuse existing --use-gpus flag: if enabled, allow hyperdrive to use GPU;
        # otherwise default to CPU.
        hyperdrive_use_cpu=(not args.use_gpus),
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
        if backend == SimulatorBackend.OSKAR:
            import json
            import os

            # Write sky model to OSM
            osm_path = "oskar_model.osm"
            with open(osm_path, "w") as f:
                # Write header
                f.write("#\n")
                f.write("#  RA,    Dec,   I,    Q,    U,    V,   freq0, spix,  RM,      maj,      min,      pa\n")
                f.write("# (deg), (deg), (Jy), (Jy), (Jy), (Jy), (Hz), (-), (rad/m^2), (arcsec), (arcsec), (deg)\n")
                f.write("#\n\n")

                # Write data
                # SkyModel sources structure:
                # [0] right ascension (deg)
                # [1] declination (deg)
                # [2] stokes I Flux (Jy)
                # [3] stokes Q Flux (Jy)
                # [4] stokes U Flux (Jy)
                # [5] stokes V Flux (Jy)
                # [6] reference_frequency (Hz)
                # [7] spectral index (N/A)
                # [8] rotation measure (rad / m^2)
                # [9] major axis FWHM (arcsec)
                # [10] minor axis FWHM (arcsec)
                # [11] position angle (deg)
                # [12] true redshift (not in OSM)
                # [13] observed redshift (not in OSM)
                # [14] source id (not in OSM)

                # We need columns 0-11 for the OSM format
                # The columns match exactly with SkyModel sources structure for the first 12 columns

                if sky_model.sources is not None:
                    sources_np = sky_model.sources.values
                    for row in sources_np:
                        # Format each value. Use general formatting but ensure spacing
                        # Adjust formatting to look nice like the example
                        line = (
                            f"{row[0]:.6f} {row[1]:.6f} "
                            f"{row[2]:.6g} {row[3]:.6g} {row[4]:.6g} {row[5]:.6g} "
                            f"{row[6]:.6e} {row[7]:.6g} {row[8]:.6g} "
                            f"{row[9]:.6g} {row[10]:.6g} {row[11]:.6g}\n"
                        )
                        f.write(line)
                    f.write("\n")

            print(f"Sky model written to {osm_path}")

            filename_key = "ms_filename" if visibility_format == "MS" else "oskar_vis_filename"
            # pylint: disable=protected-access
            interferometer_params = simulation._InterferometerSimulation__get_OSKAR_settings_tree(
                input_telpath=telescope.path,
                visibility_filename_key=filename_key,
                visibility_path=output_path,
            )
            observation_params = observation.get_OSKAR_settings_tree()
            params_total = {**interferometer_params, **observation_params}

            # Add sky model path to params
            if "sky" not in params_total:
                params_total["sky"] = {}
            params_total["sky"]["oskar_sky_model/file"] = os.path.realpath(osm_path)

            # Write to INI file
            ini_path = "oskar_sim_interferometer.ini"
            with open(ini_path, "w") as f:
                # Top-level keys in params_total correspond to sections
                for section, settings in params_total.items():
                    f.write(f"\n[{section}]\n")
                    for key, value in settings.items():
                        # Handle nested keys with slashes which OSKAR supports in Python dicts
                        # but typically represent subgroups in INI
                        f.write(f"{key}={value}\n")

            print(f"OSKAR settings written to {ini_path}")

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
        import traceback
        traceback.print_exc()
        print(f"\n✗ Error during simulation: {e}", file=sys.stderr)
        sys.exit(1)

def gpu_diagnostics():
    """Quick, noisy GPU/CUDA/OSKAR visibility checks to debug why OSKAR can't use GPUs."""
    import os
    import shutil
    import subprocess
    import ctypes
    import glob
    from textwrap import indent

    def run(cmd):
        try:
            p = subprocess.run(cmd, check=False, text=True, capture_output=True)
            out = (p.stdout or "").strip()
            err = (p.stderr or "").strip()
            return p.returncode, out, err
        except FileNotFoundError:
            return 127, "", f"not found: {cmd[0]}"
        except Exception as e:
            return 1, "", repr(e)

    def banner(title):
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)

    banner("GPU DIAGNOSTICS")

    # 1) Basic env + device nodes
    keys = [
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
        "NVIDIA_DRIVER_CAPABILITIES",
        "NVIDIA_REQUIRE_CUDA",
        "CUDA_DEVICE_ORDER",
        "LD_LIBRARY_PATH",
        "PATH",
    ]
    print("Environment:")
    for k in keys:
        v = os.environ.get(k)
        if v is not None:
            print(f"  {k}={v}")

    devs = sorted(glob.glob("/dev/nvidia*"))
    print("\nDevice nodes:")
    if devs:
        for d in devs:
            try:
                st = os.stat(d)
                print(f"  {d} (mode {oct(st.st_mode)})")
            except Exception:
                print(f"  {d} (stat failed)")
    else:
        print("  (none)  -> container/job probably has no GPU passthrough")

    # 2) nvidia-smi (most informative when available)
    banner("nvidia-smi")
    rc, out, err = run(["nvidia-smi", "-L"])
    print(f"rc={rc}")
    if out:
        print(out)
    if err:
        print(indent(err, "  "))

    rc2, out2, err2 = run(["nvidia-smi"])
    if out2:
        print("\nFull nvidia-smi:")
        print(out2)
    if err2:
        print(indent(err2, "  "))

    # 3) Can we dlopen driver/runtime libs?
    banner("CUDA library load checks")
    libs_to_try = [
        # driver API (comes from NVIDIA driver)
        "libcuda.so.1",
        "libcuda.so",
        # runtime API (comes from CUDA toolkit / CUDA runtime package)
        "libcudart.so.12",
        "libcudart.so.11.0",
        "libcudart.so",
    ]

    for lib in libs_to_try:
        try:
            ctypes.CDLL(lib)
            print(f"  OK: loaded {lib}")
        except OSError as e:
            print(f"  FAIL: {lib} -> {e}")

    # 4) OSKAR presence + (best-effort) version/build hints
    banner("OSKAR checks")
    try:
        import oskar  # type: ignore

        print("Python import: import oskar -> OK")
        # Not all builds expose a clean version API; try common patterns safely.
        ver = getattr(oskar, "__version__", None)
        if ver:
            print(f"oskar.__version__ = {ver}")
        else:
            print("oskar.__version__ not present")

        # Some builds expose a version() function; try if it exists.
        if hasattr(oskar, "version"):
            try:
                print(f"oskar.version() = {oskar.version()}")
            except Exception as e:
                print(f"oskar.version() exists but failed: {e}")

    except Exception as e:
        print(f"Python import: import oskar -> FAIL: {e}")

    # Try OSKAR CLI binaries (often reveal CUDA enablement in --version output)
    for exe in ["oskar_sim_interferometer", "oskar_settings_set", "oskar_settings_get"]:
        path = shutil.which(exe)
        if not path:
            continue
        print(f"\nFound {exe} at {path}")
        rc, out, err = run([exe, "--version"])
        print(f"  {exe} --version rc={rc}")
        if out:
            print(indent(out, "    "))
        if err:
            print(indent(err, "    "))

    # 5) Optional: can CuPy actually execute on GPU?
    banner("Optional: CuPy smoke test")
    try:
        import cupy as cp  # type: ignore

        ndev = cp.cuda.runtime.getDeviceCount()
        print(f"CuPy: device count = {ndev}")
        if ndev > 0:
            d = cp.cuda.Device(0)
            with d:
                name = cp.cuda.runtime.getDeviceProperties(0)["name"].decode("utf-8", "ignore")
                print(f"CuPy: device[0] = {name}")
                a = cp.arange(16, dtype=cp.float32)
                b = (a * 2).sum()
                print(f"CuPy: kernel OK, sum={float(b)}")
    except ModuleNotFoundError:
        print("CuPy not installed (fine) — skipping.")
    except Exception as e:
        print(f"CuPy present but failed to use GPU: {e}")

    banner("GPU DIAGNOSTICS DONE")

if __name__ == "__main__":
    main()
