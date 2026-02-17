"""Hyperdrive visibility simulation backend.

This backend shells out to the `hyperdrive vis-simulate` CLI.

Notes / limitations:
- Hyperdrive currently requires an MWA metafits file to define the array.
- Only point sources are supported from `SkyModel` (gaussians/shapelets ignored).
- Output is written by hyperdrive (MS or UVFITS). We currently support MS.

The goal is to enable a drop-in simulation backend alongside OSKAR/RASCIL.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from karabo.simulation.observation import ObservationAbstract
from karabo.simulation.sky_model import SkyModel


@dataclass
class HyperdriveSimulateOptions:
    """Options for hyperdrive vis-simulate."""

    hyperdrive_bin: str = "hyperdrive"
    metafits_path: Optional[str] = None

    # Beam control. For matching OSKAR's typical synthetic workloads, default to no beam.
    no_beam: bool = True
    beam_type: Optional[str] = None  # e.g. "fee" or "none" (CLI uses --beam-type)
    beam_file: Optional[str] = None

    no_precession: bool = False

    # Hyperdrive defaults to GPU. In many containerized CI/bench environments CUDA
    # is not available, so default to CPU.
    use_cpu: bool = True

    # Logging
    verbosity: int = 0
    no_progress_bars: bool = True


def _obs_time_res_seconds(observation: ObservationAbstract) -> float:
    # Hyperdrive wants a scalar time resolution; for our Observation model this is:
    return float(observation.length.total_seconds()) / float(observation.number_of_time_steps)


def _obs_middle_freq_mhz(observation: ObservationAbstract) -> float:
    # Observation uses start_frequency_hz + increment, representing channel starts.
    # Hyperdrive's --middle-freq is the centroid frequency in MHz.
    n = observation.number_of_channels
    df = float(observation.frequency_increment_hz)
    f0 = float(observation.start_frequency_hz)
    # Channel centers: f0 + (k + 0.5) df
    # Middle of band = average of centers.
    middle_hz = f0 + (n / 2.0) * df
    return middle_hz / 1e6


def _obs_freq_res_khz(observation: ObservationAbstract) -> float:
    return float(observation.frequency_increment_hz) / 1e3


def write_hyperdrive_srclist_yaml(
    sky: SkyModel,
    out_path: str | Path,
    default_ref_freq_hz: float,
) -> None:
    """Write a minimal hyperdrive YAML source list.

    We only write point components, and encode fluxes as a power law with a single
    reference point.

    Hyperdrive format examples live in mwa_hyperdrive/examples/hyperdrive_srclist.yaml
    """

    if sky.sources is None:
        raise ValueError("SkyModel.sources is None")

    arr = np.asarray(sky.sources)
    # columns: ra, dec, I, Q, U, V, ref_freq, spectral_index, ...
    lines: list[str] = []

    # Build yaml by hand to avoid adding yaml dependency to Karabo.
    # Format:
    # src0:
    # - ra: ...
    #   dec: ...
    #   comp_type: point
    #   flux_type:
    #     power_law:
    #       si: -0.8
    #       fd:
    #         freq: 170000000.0
    #         i: 10.0

    for i, row in enumerate(arr):
        ra = float(row[0])
        dec = float(row[1])
        stokes_i = float(row[2])
        stokes_q = float(row[3]) if row.shape[0] > 3 else 0.0
        stokes_u = float(row[4]) if row.shape[0] > 4 else 0.0
        stokes_v = float(row[5]) if row.shape[0] > 5 else 0.0
        ref_freq = float(row[6]) if row.shape[0] > 6 and float(row[6]) != 0.0 else float(default_ref_freq_hz)
        spix = float(row[7]) if row.shape[0] > 7 else 0.0

        name = f"src{i}"
        lines.append(f"{name}:")
        lines.append(f"- ra: {ra}")
        lines.append(f"  dec: {dec}")
        lines.append("  comp_type: point")
        lines.append("  flux_type:")
        lines.append("    power_law:")
        lines.append(f"      si: {spix}")
        lines.append("      fd:")
        lines.append(f"        freq: {ref_freq}")
        lines.append(f"        i: {stokes_i}")
        # Only add Q/U/V if non-zero to keep output minimal.
        if stokes_q != 0.0:
            lines.append(f"        q: {stokes_q}")
        if stokes_u != 0.0:
            lines.append(f"        u: {stokes_u}")
        if stokes_v != 0.0:
            lines.append(f"        v: {stokes_v}")

    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_hyperdrive_vis_simulate(
    *,
    sky: SkyModel,
    observation: ObservationAbstract,
    output_ms_path: str | Path,
    options: HyperdriveSimulateOptions,
    workdir: Optional[str | Path] = None,
) -> None:
    if options.metafits_path is None:
        raise ValueError(
            "Hyperdrive backend requires a metafits file. "
            "Set InterferometerSimulation(hyperdrive_metafits_path=...)."
        )

    output_ms_path = Path(output_ms_path)

    # Create a temp srclist in the same directory so hyperdrive can find it even
    # if run from a different cwd.
    with tempfile.TemporaryDirectory(dir=str(workdir) if workdir else None) as td:
        td_path = Path(td)
        srclist_path = td_path / "karabo_hyperdrive_srclist.yaml"

        write_hyperdrive_srclist_yaml(
            sky=sky,
            out_path=srclist_path,
            default_ref_freq_hz=float(observation.start_frequency_hz),
        )

        cmd: list[str] = [options.hyperdrive_bin, "vis-simulate"]
        if options.no_progress_bars:
            cmd.append("--no-progress-bars")
        if options.verbosity > 0:
            cmd.append("-" + "v" * int(options.verbosity))

        # Beam.
        if options.no_beam:
            cmd.append("--no-beam")
        if options.beam_type is not None:
            cmd += ["--beam-type", options.beam_type]
        if options.beam_file is not None:
            cmd += ["--beam-file", options.beam_file]

        if options.no_precession:
            cmd.append("--no-precession")

        if options.use_cpu:
            cmd.append("--cpu")

        cmd += ["-m", options.metafits_path]

        # Sky model
        cmd += ["-s", str(srclist_path), "--source-list-type", "hyperdrive"]

        # Hyperdrive may "veto" sources below a threshold; for synthetic workloads
        # with a few sources this is counterproductive. Provide an explicit named
        # source allowlist to skip vetoing entirely.
        # Names must match the YAML top-level keys written by write_hyperdrive_srclist_yaml().
        n_sources = int(np.asarray(sky.sources).shape[0])
        for i in range(n_sources):
            cmd += ["--named-sources", f"src{i}"]

        # Observation params
        # Use --ra= / --dec= form so negative declinations are not parsed as flags.
        cmd += [f"--ra={float(observation.phase_centre_ra_deg)}"]
        cmd += [f"--dec={float(observation.phase_centre_dec_deg)}"]
        cmd += ["-t", str(int(observation.number_of_time_steps))]
        cmd += ["--time-res", str(_obs_time_res_seconds(observation))]
        cmd += ["-c", str(int(observation.number_of_channels))]
        cmd += ["-f", str(_obs_freq_res_khz(observation))]
        cmd += ["--middle-freq", str(_obs_middle_freq_mhz(observation))]

        # Output
        cmd += ["-o", str(output_ms_path)]

        # Run
        proc = subprocess.run(
            cmd,
            cwd=str(workdir) if workdir else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "hyperdrive vis-simulate failed with exit code "
                f"{proc.returncode}\nCommand: {json.dumps(cmd)}\nOutput:\n{proc.stdout}"
            )

        if not output_ms_path.exists():
            raise RuntimeError(
                f"hyperdrive reported success but output MS does not exist: {output_ms_path}\n"
                f"Command: {json.dumps(cmd)}\nOutput:\n{proc.stdout}"
            )
