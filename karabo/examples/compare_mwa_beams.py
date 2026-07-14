#!/usr/bin/env python3
import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.colors import LogNorm
from scipy.interpolate import RegularGridInterpolator
from typing import Tuple

import everybeam
from astropy.coordinates import AltAz, EarthLocation, ITRS
from astropy.time import Time
import astropy.units as u
from casacore.tables import table
from mwa_hyperbeam import FEEBeam
from pyuvdata import UVBeam


def compute_hyperbeam(beam_path: str, freq_mhz: float, za_vals: np.ndarray, az_vals: np.ndarray, delays: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    beam = FEEBeam(beam_path)
    freqs = beam.get_fee_beam_freqs()
    freq_hz = float(freqs[np.argmin(np.abs(freqs - freq_mhz * 1e6))])
    AZ, ZA = np.meshgrid(np.radians(az_vals), np.radians(za_vals), indexing="xy")
    # Jones array flattened per point: [J_xx, J_xy, J_yx, J_yy]
    J = beam.calc_jones_array(AZ.ravel(), ZA.ravel(), freq_hz, delays, np.ones(16, float), False)
    J = J.reshape(ZA.size, 4)
    J_xx = J[:, 0].reshape(len(za_vals), len(az_vals))
    J_xy = J[:, 1].reshape(len(za_vals), len(az_vals))
    J_yx = J[:, 2].reshape(len(za_vals), len(az_vals))
    J_yy = J[:, 3].reshape(len(za_vals), len(az_vals))
    # Feed power for unpolarized sky: sum over sky pol components
    Pxx = np.abs(J_xx) ** 2 + np.abs(J_xy) ** 2
    Pyy = np.abs(J_yx) ** 2 + np.abs(J_yy) ** 2
    return Pxx, Pyy


def compute_pyuvbeam(beam_path: str, freq_mhz: float, za_vals: np.ndarray, az_vals: np.ndarray, delays: np.ndarray, *, az_shift_mode: int = -1, basis_mode: int = 0, rot_mode: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    # Compute power from efield with correct transformations
    Jxx, Jxy, Jyx, Jyy = compute_py_jones_grid(beam_path, freq_mhz, za_vals, az_vals, delays, az_shift_mode=az_shift_mode, basis_mode=basis_mode, rot_mode=rot_mode)
    # Power for unpolarized sky: sum over sky pol components
    Pxx = np.abs(Jxx)**2 + np.abs(Jxy)**2
    Pyy = np.abs(Jyx)**2 + np.abs(Jyy)**2
    return Pxx, Pyy


def read_pyuvbeam(beam_path: str, freq_mhz: float) -> UVBeam:
    beam = UVBeam()
    f0 = freq_mhz * 1e6
    beam.read_mwa_beam(beam_path, run_check=False, freq_range=(f0 - 0.64e6, f0 + 0.64e6))
    return beam


def compute_hb_jones_grid(beam_path: str, freq_mhz: float, za_vals: np.ndarray, az_vals: np.ndarray, delays: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    beam = FEEBeam(beam_path)
    freqs = beam.get_fee_beam_freqs()
    freq_hz = float(freqs[np.argmin(np.abs(freqs - freq_mhz * 1e6))])
    AZ, ZA = np.meshgrid(np.radians(az_vals), np.radians(za_vals), indexing="xy")
    J = beam.calc_jones_array(AZ.ravel(), ZA.ravel(), freq_hz, delays, np.ones(16, float), False)
    J = J.reshape(ZA.size, 4)
    Jxx = J[:, 0].reshape(len(za_vals), len(az_vals))
    Jxy = J[:, 1].reshape(len(za_vals), len(az_vals))
    Jyx = J[:, 2].reshape(len(za_vals), len(az_vals))
    Jyy = J[:, 3].reshape(len(za_vals), len(az_vals))
    return Jxx, Jxy, Jyx, Jyy


def pyuvbeam_efield(
    beam: UVBeam, vector_index: int, feed_index: int, frequency_index: int,
    za_index, az_index,
) -> np.ndarray:
    """Read PyUVData's e-field array across its pre- and post-3.x layouts."""
    if beam.data_array.ndim == 6:
        return beam.data_array[
            vector_index, 0, feed_index, frequency_index, za_index, az_index
        ]
    if beam.data_array.ndim == 5:
        return beam.data_array[
            vector_index, feed_index, frequency_index, za_index, az_index
        ]
    raise ValueError(f"Unsupported PyUVBeam data shape: {beam.data_array.shape}")


def compute_everybeam_jones_grid(
    ms_path: str,
    beam_path: str,
    freq_mhz: float,
    za_vals: np.ndarray,
    az_vals: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate EveryBeam's DP3-Predict MWA primitive over an AltAz grid."""
    with table(ms_path, ack=False) as ms:
        time_mjd_seconds = float(ms.getcell("TIME", 0))
    with table(os.path.join(ms_path, "ANTENNA"), ack=False) as antennas:
        array_position_m = antennas.getcell("POSITION", 0)

    telescope = everybeam.load_telescope(ms_path, coeff_path=beam_path)
    if not isinstance(telescope, everybeam.MWA):
        raise TypeError(f"Expected an MWA telescope, got {type(telescope).__name__}")

    AZ, ZA = np.meshgrid(np.radians(az_vals), np.radians(za_vals), indexing="xy")
    observation_time = Time(time_mjd_seconds / 86400.0, format="mjd", scale="utc")
    location = EarthLocation.from_geocentric(*array_position_m, unit="m")
    altaz = AltAz(
        az=AZ.ravel() * u.rad,
        alt=(np.pi / 2.0 - ZA.ravel()) * u.rad,
        obstime=observation_time,
        location=location,
    )
    itrf = altaz.transform_to(ITRS(obstime=observation_time)).cartesian
    directions_itrf = np.column_stack(
        [itrf.x.value, itrf.y.value, itrf.z.value]
    )
    directions_itrf /= np.linalg.norm(directions_itrf, axis=1)[:, None]

    frequency_hz = freq_mhz * 1e6
    jones = np.empty((directions_itrf.shape[0], 2, 2), dtype=complex)
    for index, direction_itrf in enumerate(directions_itrf):
        jones[index] = telescope.station_response(
            time_mjd_seconds, 0, frequency_hz, direction_itrf
        )

    shape = (len(za_vals), len(az_vals))
    return (
        jones[:, 0, 0].reshape(shape),
        jones[:, 0, 1].reshape(shape),
        jones[:, 1, 0].reshape(shape),
        jones[:, 1, 1].reshape(shape),
    )


def compute_py_jones_grid(beam_path: str, freq_mhz: float, za_vals: np.ndarray, az_vals: np.ndarray, delays: np.ndarray, *, az_shift_mode: int = 1, basis_mode: int = 0, rot_mode: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
	delays_2 = np.array([delays, delays])
	beam = UVBeam()
	f0 = freq_mhz * 1e6
	beam.read_mwa_beam(beam_path, run_check=False, freq_range=(f0 - 0.64e6, f0 + 0.64e6), delays=delays_2)
	# Expect efield
	assert beam.beam_type == "efield"
	freqs = beam.freq_array[0]
	fi = int(np.argmin(np.abs(freqs - f0)))
	az_src = np.rad2deg(beam.axis1_array) if beam.pixel_coordinate_system == "az_za" else beam.axis1_array
	za_src = np.rad2deg(beam.axis2_array) if beam.pixel_coordinate_system == "az_za" else beam.axis2_array
	az_step = (az_src[1] - az_src[0]) if len(az_src) > 1 else 1.0
	za_step = (za_src[1] - za_src[0]) if len(za_src) > 1 else 1.0
	# Apply az shift per diagnosed mode
	if az_shift_mode == 1:
		az_vals_py = (90.0 + az_vals) % 360.0
	elif az_shift_mode == -1:
		az_vals_py = (90.0 - az_vals) % 360.0
	else:
		az_vals_py = az_vals % 360.0
	az_idx = np.clip(np.round((az_vals_py - az_src.min()) / az_step).astype(int), 0, len(az_src) - 1)
	za_idx = np.clip(np.round((za_vals - za_src.min()) / za_step).astype(int), 0, len(za_src) - 1)
	# Prepare outputs
	Jxx = np.empty((len(za_vals), len(az_vals)), dtype=complex)
	Jxy = np.empty_like(Jxx)
	Jyx = np.empty_like(Jxx)
	Jyy = np.empty_like(Jxx)
	# basis 0 ~ theta, 1 ~ phi; data indices end with (za, az)
	for i, zi in enumerate(za_idx):
		# slice at this za over all az
		Ex_theta_row = pyuvbeam_efield(beam, 0, 0, fi, zi, slice(None))
		Ex_phi_row = pyuvbeam_efield(beam, 1, 0, fi, zi, slice(None))
		if beam.Nfeeds > 1:
			Ey_theta_row = pyuvbeam_efield(beam, 0, 1, fi, zi, slice(None))
			Ey_phi_row = pyuvbeam_efield(beam, 1, 1, fi, zi, slice(None))
		else:
			Ey_theta_row = np.zeros_like(Ex_theta_row)
			Ey_phi_row   = np.zeros_like(Ex_phi_row)
		sel = az_idx
		# Map to XY per diagnosed basis mode
		if basis_mode == 0:
			# X=+phi, Y=-theta
			Jxx[i, :] = Ex_phi_row[sel]
			Jxy[i, :] = -Ex_theta_row[sel]
			Jyx[i, :] = Ey_phi_row[sel]
			Jyy[i, :] = -Ey_theta_row[sel]
		else:
			# X=+theta, Y=+phi
			Jxx[i, :] = Ex_theta_row[sel]
			Jxy[i, :] = Ex_phi_row[sel]
			Jyx[i, :] = Ey_theta_row[sel]
			Jyy[i, :] = Ey_phi_row[sel]

	# Apply feed rotation per diagnosed mode
	if rot_mode == 0:
		Jxx_rot, Jxy_rot, Jyx_rot, Jyy_rot = Jxx, Jxy, Jyx, Jyy
	elif rot_mode == 1:
		# swap X<->Y: R=[[0,1],[1,0]]
		Jxx_rot = Jyx
		Jxy_rot = Jyy
		Jyx_rot = Jxx
		Jyy_rot = Jxy
	elif rot_mode == 2:
		# rotate X<-Y, Y<- -X: R=[[0,1],[-1,0]]
		Jxx_rot = Jyx
		Jxy_rot = Jyy
		Jyx_rot = -Jxx
		Jyy_rot = -Jxy
	else:
		# rotate X<- -Y, Y<-X: R=[[0,-1],[1,0]]
		Jxx_rot = -Jyx
		Jxy_rot = -Jyy
		Jyx_rot = Jxx
		Jyy_rot = Jxy
	return Jxx_rot, Jxy_rot, Jyx_rot, Jyy_rot


def sample_hyperbeam_jones(beam_path: str, freq_mhz: float, za_deg: float, az_deg: float, az_offset_deg: float = 0.0) -> np.ndarray:
    beam = FEEBeam(beam_path)
    freqs = beam.get_fee_beam_freqs()
    freq_hz = float(freqs[np.argmin(np.abs(freqs - freq_mhz * 1e6))])
    az_use = np.radians((az_deg + az_offset_deg) % 360.0)
    za_use = np.radians(za_deg)
    J = beam.calc_jones_array(np.array([az_use]), np.array([za_use]), freq_hz, np.zeros(16, np.uint32), np.ones(16, float), False)
    # J layout: [J_xx, J_xy, J_yx, J_yy]
    J = J.reshape(4)
    return np.array([[J[0], J[1]], [J[2], J[3]]], dtype=complex)


def _map_theta_phi_to_xy(theta_x: complex, phi_x: complex, theta_y: complex, phi_y: complex, basis_mode: int) -> np.ndarray:
    # basis_mode 0: X=+phi, Y=-theta (current)
    # basis_mode 1: X=+theta, Y=+phi (alternative)
    if basis_mode == 0:
        Jxx = phi_x
        Jxy = -theta_x
        Jyx = phi_y
        Jyy = -theta_y
    else:
        Jxx = theta_x
        Jxy = phi_x
        Jyx = theta_y
        Jyy = phi_y
    return np.array([[Jxx, Jxy], [Jyx, Jyy]], dtype=complex)


def _apply_feed_rotation(J: np.ndarray, rot_mode: int) -> np.ndarray:
    # rot_mode 0: identity
    # 1: swap X<->Y (R=[[0,1],[1,0]])
    # 2: rotate 90deg: X<-Y, Y<- -X (R=[[0,1],[-1,0]])
    # 3: rotate -90deg: X<- -Y, Y<- X (R=[[0,-1],[1,0]])
    if rot_mode == 0:
        return J
    elif rot_mode == 1:
        R = np.array([[0,1],[1,0]], dtype=int)
    elif rot_mode == 2:
        R = np.array([[0,1],[-1,0]], dtype=int)
    else:
        R = np.array([[0,-1],[1,0]], dtype=int)
    return R @ J @ R.T


def sample_pyuvbeam_jones(beam: UVBeam, freq_mhz: float, za_deg: float, az_deg: float, *, az_shift_mode: int = 1, basis_mode: int = 0, rot_mode: int = 0) -> np.ndarray:
    # Expect efield beam: data_array shape (2, Nspws, Nfeeds, Nfreqs, Naxis1, Naxis2)
    assert beam.beam_type == "efield"
    f0 = freq_mhz * 1e6
    freqs = beam.freq_array[0]
    fi = int(np.argmin(np.abs(freqs - f0)))
    # In az_za, axis1=az (rad), axis2=za (rad). data_array ends with (Naxes2, Naxes1) = (za, az)
    az_vals = np.rad2deg(beam.axis1_array) if beam.pixel_coordinate_system == "az_za" else beam.axis1_array
    za_vals = np.rad2deg(beam.axis2_array) if beam.pixel_coordinate_system == "az_za" else beam.axis2_array
    # map hyperbeam az to pyuvbeam az per shift mode: +1 => (90+az), -1 => (90-az), 0 => az
    if az_shift_mode == 1:
        az_eff = (90.0 + az_deg) % 360.0
    elif az_shift_mode == -1:
        az_eff = (90.0 - az_deg) % 360.0
    else:
        az_eff = az_deg % 360.0
    az_idx = int(np.clip(np.argmin(np.abs(az_vals - az_eff)), 0, len(az_vals) - 1))
    za_idx = int(np.clip(np.argmin(np.abs(za_vals - za_deg)), 0, len(za_vals) - 1))
    # basis 0 ~ theta (za), basis 1 ~ phi (az)
    # Map to sky XY: X ~ +phi, Y ~ -theta
    Ex_theta = pyuvbeam_efield(beam, 0, 0, fi, za_idx, az_idx)
    Ex_phi = pyuvbeam_efield(beam, 1, 0, fi, za_idx, az_idx)
    if beam.Nfeeds > 1:
        Ey_theta = pyuvbeam_efield(beam, 0, 1, fi, za_idx, az_idx)
        Ey_phi = pyuvbeam_efield(beam, 1, 1, fi, za_idx, az_idx)
    else:
        Ey_theta, Ey_phi = Ex_theta * 0, Ex_phi * 0
    J = _map_theta_phi_to_xy(Ex_theta, Ex_phi, Ey_theta, Ey_phi, basis_mode)
    J = _apply_feed_rotation(J, rot_mode)
    return J


def diagnose_py_mapping(beam_hb_path: str, beam_py: UVBeam, freq_mhz: float) -> tuple:
    # Try a grid of mappings and choose minimal complex L2 error over 5 points
    candidates = []
    # az shift modes: -1, 0, +1
    for az_mode in (-1, 0, 1):
        for basis_mode in (0, 1):
            for rot_mode in (0, 1, 2, 3):
                err = 0.0
                for (za_deg, az_deg) in [(0.0,0.0),(10.0,0.0),(10.0,90.0),(10.0,180.0),(10.0,270.0)]:
                    J_hb = sample_hyperbeam_jones(beam_hb_path, freq_mhz, za_deg, az_deg, az_offset_deg=0.0)
                    J_py = sample_pyuvbeam_jones(beam_py, freq_mhz, za_deg, az_deg, az_shift_mode=az_mode, basis_mode=basis_mode, rot_mode=rot_mode)
                    err += np.linalg.norm(J_hb - J_py)
                candidates.append((err, az_mode, basis_mode, rot_mode))
    candidates.sort(key=lambda x: x[0])
    return candidates[0]


def main() -> None:
    p = argparse.ArgumentParser(description="Compare MWA beams: hyperbeam vs pyuvbeam")
    p.add_argument("beam_path", help="Path to MWA HDF5 beam file")
    p.add_argument("--freq-mhz", type=float, required=True)
    p.add_argument("--pol", default="X", choices=["X", "Y"])
    p.add_argument("--za-step", type=float, default=1.0)
    p.add_argument("--az-step", type=float, default=1.0)
    p.add_argument("--norm", default="none", choices=["none", "zenith"], help="Normalization: none (raw), zenith (divide by power at zenith)")
    p.add_argument("--mode", default="power", choices=["power", "efield"], help="Compare in power or efield domain (Jones)")
    p.add_argument("--out", default="compare_mwa_beams.png")
    p.add_argument("--projection", type=str, default=None, help="Projection code: SIN, TAN, ARC, ZEA, STG")
    p.add_argument("--proj-size", type=float, default=90.0, help="Half-size of projected plane in deg (extent is ±proj-size)")
    p.add_argument("--pix", type=float, default=0.5, help="Pixel scale in deg for projection")
    p.add_argument(
        "--everybeam-ms",
        default=os.environ.get("EVERYBEAM_MWA_MS"),
        help="MWA Measurement Set for EveryBeam (or set EVERYBEAM_MWA_MS)",
    )
    p.add_argument("--no-plot", action="store_true", help="Skip plotting and only print summary/table")
    p.add_argument("--quiet", action="store_true", help="Suppress non-table prints for minimal output")
    p.add_argument("--delay-ewp", type=int, default=0, help="Delay E-W plane in beamformer units")
    args = p.parse_args()

    za_vals = np.arange(0.0, 90.0 + 1e-6, args.za_step)
    az_vals = np.arange(0.0, 360.0, args.az_step)

    # Diagnose best mapping first (using efield beam)
    beam_py = read_pyuvbeam(args.beam_path, args.freq_mhz)
    if beam_py.beam_type != "efield":
        if args.mode == "efield":
            print("Efield comparison requested but pyuvbeam is power; falling back to power mode.")
            args.mode = "power"
    best_err, best_az_mode, best_basis_mode, best_rot_mode = diagnose_py_mapping(args.beam_path, beam_py, args.freq_mhz)
    if not args.quiet:
        basis_desc = "X=+phi, Y=-theta" if best_basis_mode == 0 else "X=+theta, Y=+phi"
        if best_az_mode == -1:
            az_desc = "az_py = (90 - az_hb)"
        elif best_az_mode == 1:
            az_desc = "az_py = (90 + az_hb)"
        else:
            az_desc = "az_py = az_hb"
        rot_desc = {0: "no feed rotation", 1: "swap X↔Y", 2: "rotate X<-Y, Y<- -X", 3: "rotate X<- -Y, Y<-X"}.get(best_rot_mode, str(best_rot_mode))
        print(f"Mapping: {az_desc}; basis: {basis_desc}; feeds: {rot_desc}; err={best_err:.3e}")

    # Timed computations
    start = time.perf_counter()
    delays = np.array([0,0,0,0] * 4)
    if args.delay_ewp:
        delays = np.array([0,1*args.delay_ewp,2*args.delay_ewp,3*args.delay_ewp] * 4)
    Hxx, Hyy = compute_hyperbeam(args.beam_path, args.freq_mhz, za_vals, az_vals, delays)
    hb_time = time.perf_counter() - start
    start = time.perf_counter()
    Pxx, Pyy = compute_pyuvbeam(args.beam_path, args.freq_mhz, za_vals, az_vals, delays, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
    py_time = time.perf_counter() - start

    H = Hxx if args.pol.upper() == "X" else Hyy
    P = Pxx if args.pol.upper() == "X" else Pyy

    # Apply normalization if requested
    if args.norm == "zenith":
        Hz = H[0, 0] if np.isfinite(H[0, 0]) and H[0, 0] != 0 else 1.0
        Pz = P[0, 0] if np.isfinite(P[0, 0]) and P[0, 0] != 0 else 1.0
        H = H / Hz
        P = P / Pz

    # Report zenith power and timings
    if not args.quiet:
        print(f"Hyperbeam power at zenith: {H[0,0]:.6e}")
        print(f"PyUVBeam power at zenith: {P[0,0]:.6e}")
        npix = H.size
        print(f"Hyperbeam time: {hb_time:.3f} s  ({npix/hb_time:.1f} px/s)")
        print(f"PyUVBeam time: {py_time:.3f} s  ({npix/py_time:.1f} px/s)")

    # Differences
    valid = np.isfinite(H) & np.isfinite(P)
    diff_abs = np.nanmean(np.abs(H[valid] - P[valid]))
    diff_rel = np.nanmean(np.abs((H[valid] - P[valid]) / np.maximum(P[valid], 1e-20)))
    if not args.quiet:
        print(f"Mean abs diff: {diff_abs:.3e}")
        print(f"Mean rel diff: {diff_rel:.3e}")

    # Sample 5 points: zenith and 10° off-zenith in N/E/S/W
    def nearest_idx(vals: np.ndarray, target: float) -> int:
        return int(np.clip(np.argmin(np.abs(vals - target)), 0, len(vals) - 1))

    samples = [
        ("Zenith", 0.0, 0.0),
        ("North 10deg", 10.0, 0.0),
        ("East 10deg", 10.0, 90.0),
        ("South 10deg", 10.0, 180.0),
        ("West 10deg", 10.0, 270.0),
    ]

    rows = []
    for label, za_deg, az_deg in samples:
        zi = nearest_idx(za_vals, za_deg)
        ai = nearest_idx(az_vals, az_deg % 360.0)
        hv = float(H[zi, ai]) if np.isfinite(H[zi, ai]) else float("nan")
        pv = float(P[zi, ai]) if np.isfinite(P[zi, ai]) else float("nan")
        ratio = hv / pv if (np.isfinite(pv) and pv != 0.0) else float("nan")
        rows.append((label, za_deg, az_deg, hv, pv, ratio))

    # Build 4x4 offset grid from zenith in the tangent plane (E-W, N-S in degrees)
    # Use symmetric offsets around zenith
    offsets = [45.0, 15.0, -15.0, -45.0]
    grid_points = []  # (name, za_deg, az_deg, x_off, y_off)
    for y_off in offsets:  # N-S (positive north)
        for x_off in offsets:  # E-W (positive east)
            r = float(np.hypot(x_off, y_off))
            az_deg = float((np.degrees(np.arctan2(x_off, y_off)) % 360.0))
            grid_points.append((f"x={x_off:.0f},y={y_off:.0f}", r, az_deg, x_off, y_off))

    # Pretty table using tabulate
    try:
        from tabulate import tabulate  # type: ignore
        headers = ["Point", "za [deg]", "az [deg]", "Hyperbeam", "PyUVBeam"] #, "H/P"]
        table_rows = []
        for label, za_deg, az_deg, hv, pv, ratio in rows:
            table_rows.append([label, f"{za_deg:.1f}", f"{az_deg:.1f}", hv, pv]) #, ratio])
        print(tabulate(table_rows, headers=headers, tablefmt="github", floatfmt=".6e"))
    except Exception:
        # Fallback to simple markdown if tabulate is unavailable
        print("| Point | za [deg] | az [deg] | Hyperbeam | PyUVBeam | H/P |")
        print("|---|---:|---:|---:|---:|---:|")
        for label, za_deg, az_deg, hv, pv, ratio in rows:
            print(f"| {label} | {za_deg:.1f} | {az_deg:.1f} | {hv:.6e} | {pv:.6e} | {ratio:.6e} |")

    # Full Jones matrices (efield) comparison at the same 5 points with diagnosed mapping (already done above)
    # Build Jones table with mag/phase (deg), 1sf scientific notation for mag
    def fmt_mag_phase(x: complex) -> tuple:
        mag = np.abs(x)
        ph = np.degrees(np.angle(x))
        mag_s = f"{mag:.0e}" if np.isfinite(mag) else "nan"
        ph_s = f"{ph:.1f}" if np.isfinite(ph) else "nan"
        return mag_s, ph_s

    j_headers = [
        "Point", "za [deg]", "az [deg]",
        "HB |Jxx|", "HB ∠Jxx", "HB |Jxy|", "HB ∠Jxy",
        "HB |Jyy|", "HB ∠Jyy",
        "PY(m) |Jxx|", "PY(m) ∠Jxx", "PY(m) |Jxy|", "PY(m) ∠Jxy",
        "PY(m) |Jyy|", "PY(m) ∠Jyy",
    ]
    j_rows = []
    for label, za_deg, az_deg in [("Zenith",0.0,0.0),("North 10deg",10.0,0.0),("East 10deg",10.0,90.0),("South 10deg",10.0,180.0),("West 10deg",10.0,270.0)]:
        if args.mode == "efield":
            J_hb = sample_hyperbeam_jones(args.beam_path, args.freq_mhz, za_deg, az_deg, az_offset_deg=0.0)
            J_py = sample_pyuvbeam_jones(beam_py, args.freq_mhz, za_deg, az_deg, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
        else:
            # In power mode, compare autos as |Jxx|^2+|Jxy|^2 etc.
            J_hb = sample_hyperbeam_jones(args.beam_path, args.freq_mhz, za_deg, az_deg, az_offset_deg=0.0)
            J_py = sample_pyuvbeam_jones(beam_py, args.freq_mhz, za_deg, az_deg, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
        hxx_mag,hxx_ph = fmt_mag_phase(J_hb[0,0]); hxy_mag,hxy_ph = fmt_mag_phase(J_hb[0,1])
        hyy_mag,hyy_ph = fmt_mag_phase(J_hb[1,1])
        pxx_mag,pxx_ph = fmt_mag_phase(J_py[0,0]); pxy_mag,pxy_ph = fmt_mag_phase(J_py[0,1])
        pyy_mag,pyy_ph = fmt_mag_phase(J_py[1,1])
        j_rows.append([
            label, f"{za_deg:.1f}", f"{az_deg:.1f}",
            hxx_mag, hxx_ph, hxy_mag, hxy_ph,
            hyy_mag, hyy_ph,
            pxx_mag, pxx_ph, pxy_mag, pxy_ph,
            pyy_mag, pyy_ph,
        ])
    # Append 4x4 grid points
    for label, r_za, az_deg, _x, _y in grid_points:
        if r_za > 90.0:
            continue
        if args.mode == "efield":
            J_hb = sample_hyperbeam_jones(args.beam_path, args.freq_mhz, r_za, az_deg, az_offset_deg=0.0)
            J_py = sample_pyuvbeam_jones(beam_py, args.freq_mhz, r_za, az_deg, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
        else:
            J_hb = sample_hyperbeam_jones(args.beam_path, args.freq_mhz, r_za, az_deg, az_offset_deg=0.0)
            J_py = sample_pyuvbeam_jones(beam_py, args.freq_mhz, r_za, az_deg, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
        hxx_mag,hxx_ph = fmt_mag_phase(J_hb[0,0]); hxy_mag,hxy_ph = fmt_mag_phase(J_hb[0,1])
        hyy_mag,hyy_ph = fmt_mag_phase(J_hb[1,1])
        pxx_mag,pxx_ph = fmt_mag_phase(J_py[0,0]); pxy_mag,pxy_ph = fmt_mag_phase(J_py[0,1])
        pyy_mag,pyy_ph = fmt_mag_phase(J_py[1,1])
        j_rows.append([
            f"Grid {label}", f"{r_za:.1f}", f"{az_deg:.1f}",
            hxx_mag, hxx_ph, hxy_mag, hxy_ph,
            hyy_mag, hyy_ph,
            pxx_mag, pxx_ph, pxy_mag, pxy_ph,
            pyy_mag, pyy_ph,
        ])
    try:
        from tabulate import tabulate  # type: ignore
        print(tabulate(j_rows, headers=j_headers, tablefmt="github"))
    except Exception:
        print("| "+" | ".join(j_headers)+" |")
        print("|"+"---|"*len(j_headers))
        for r in j_rows:
            print("| "+" | ".join(str(x) for x in r)+" |")

    if not args.no_plot:
        if not args.everybeam_ms:
            p.error("--everybeam-ms or EVERYBEAM_MWA_MS is required for plotting")
        plt.style.use("dark_background")
        # Build Jones grids for 6 panels: Hyperbeam / PyUVBeam / EveryBeam.
        Jxx_hb, Jxy_hb, Jyx_hb, Jyy_hb = compute_hb_jones_grid(args.beam_path, args.freq_mhz, za_vals, az_vals, delays)
        # Use diagnosed mapping for the grid too
        Jxx_py, Jxy_py, Jyx_py, Jyy_py = compute_py_jones_grid(args.beam_path, args.freq_mhz, za_vals, az_vals, delays, az_shift_mode=best_az_mode, basis_mode=best_basis_mode, rot_mode=best_rot_mode)
        start = time.perf_counter()
        Jxx_eb, Jxy_eb, Jyx_eb, Jyy_eb = compute_everybeam_jones_grid(
            args.everybeam_ms,
            args.beam_path,
            args.freq_mhz,
            za_vals,
            az_vals,
        )
        eb_time = time.perf_counter() - start
        if not args.quiet:
            print(f"EveryBeam time: {eb_time:.3f} s")

        def mag(z):
            return np.abs(z)

        def phase(z):
            return np.degrees(np.angle(z))

        rows = [
            (mag(Jxx_hb), mag(Jxx_py), mag(Jxx_eb), "|Jxx|"),
            (phase(Jxx_hb), phase(Jxx_py), phase(Jxx_eb), "∠Jxx"),
            (mag(Jyy_hb), mag(Jyy_py), mag(Jyy_eb), "|Jyy|"),
            (phase(Jyy_hb), phase(Jyy_py), phase(Jyy_eb), "∠Jyy"),
            (mag(Jxy_hb), mag(Jxy_py), mag(Jxy_eb), "|Jxy|"),
            (phase(Jxy_hb), phase(Jxy_py), phase(Jxy_eb), "∠Jxy"),
        ]
        # Keep a pristine copy for projection; handle seam only for native plotting below
        rows_orig = rows
        extent_native = [az_vals.min(), az_vals.max(), za_vals.min(), za_vals.max()]
        fig, axs = plt.subplots(6, 3, figsize=(18, 20), constrained_layout=True)
        # Row-wise normalization (shared vmin/vmax per row)
        def row_norm(
            arr_hb: np.ndarray,
            arr_py: np.ndarray,
            arr_eb: np.ndarray,
            is_mag: bool,
        ):
            Z1, Z2, Z3 = np.copy(arr_hb), np.copy(arr_py), np.copy(arr_eb)
            if is_mag:
                # linear mags, log norm; set tiny floor for zeros
                tiny = 1e-12
                Z1 = np.where(np.isfinite(Z1), Z1, np.nan)
                Z2 = np.where(np.isfinite(Z2), Z2, np.nan)
                Z3 = np.where(np.isfinite(Z3), Z3, np.nan)
                positive_mins = [
                    np.nanmin(Z[Z > 0]) if np.any(Z > 0) else np.nan
                    for Z in (Z1, Z2, Z3)
                ]
                vmin = max(tiny, np.nanmin(positive_mins))
                vmax = np.nanmax([np.nanmax(Z1), np.nanmax(Z2), np.nanmax(Z3)])
                return Z1, Z2, Z3, vmin, vmax
            # Phases in degrees, centered to [-180, 180].
            return (
                (Z1 + 180.0) % 360.0 - 180.0,
                (Z2 + 180.0) % 360.0 - 180.0,
                (Z3 + 180.0) % 360.0 - 180.0,
                -180.0,
                180.0,
            )
        if args.projection is None:
            # Native plotting
            add_seam = az_vals[-1] < 360.0
            if add_seam:
                az_plot = np.append(az_vals, 360.0)
                rows_native = [
                    (
                        np.concatenate([hb, hb[:, :1]], axis=1),
                        np.concatenate([py, py[:, :1]], axis=1),
                        np.concatenate([eb, eb[:, :1]], axis=1),
                        title,
                    )
                    for hb, py, eb, title in rows_orig
                ]
            else:
                az_plot = az_vals
                rows_native = rows_orig
            extent_native = [az_plot.min(), az_plot.max(), za_vals.min(), za_vals.max()]
            for i, (hbZ_raw, pyZ_raw, ebZ_raw, title) in enumerate(rows_native):
                is_mag = ("|" in title)
                hbZ, pyZ, ebZ, vmin, vmax = row_norm(
                    hbZ_raw, pyZ_raw, ebZ_raw, is_mag
                )
                for j, (Z, lbl) in enumerate([
                    (hbZ, "Hyperbeam"),
                    (pyZ, "PyUVBeam"),
                    (ebZ, "EveryBeam"),
                ]):
                    ax = axs[i, j]
                    im = ax.imshow(
                        Z,
                        origin="upper",
                        extent=extent_native,
                        aspect="auto",
                        cmap="rainbow",
                        norm=LogNorm(vmin=vmin, vmax=vmax) if is_mag else None,
                        vmin=None if is_mag else vmin,
                        vmax=None if is_mag else vmax,
                    )
                    ax.set_xlabel("Azimuth [deg]")
                    ax.set_ylabel("Zenith Angle [deg]")
                    ax.set_title(f"{lbl} {title}")
                    fig.colorbar(im, ax=ax)
            # Overlay test points on native polar plots
            # 5 named points
            for (label, za_deg, az_deg) in [("Zenith",0.0,0.0),("North 10deg",10.0,0.0),("East 10deg",10.0,90.0),("South 10deg",10.0,180.0),("West 10deg",10.0,270.0)]:
                x = az_deg
                y = za_deg
                for r in range(6):
                    for c in range(3):
                        axs[r, c].plot(x, y, 'w+', markersize=8, markeredgewidth=1.5)
            # 4x4 grid points
            for _name, r_za, az_deg, _xoff, _yoff in grid_points:
                if r_za > 90.0:
                    continue
                x = az_deg
                y = r_za
                for r in range(6):
                    for c in range(3):
                        axs[r, c].plot(x, y, 'wo', markersize=3, markeredgewidth=0.0, alpha=0.8)
        else:
            # Projected plotting
            npix = int(2 * args.proj_size / max(args.pix, 1e-3))
            extent_proj = [-args.proj_size, args.proj_size, -args.proj_size, args.proj_size]
            x_cart = np.linspace(-args.proj_size, args.proj_size, npix)
            y_cart = np.linspace(-args.proj_size, args.proj_size, npix)
            xx, yy = np.meshgrid(x_cart, y_cart)
            r_deg = np.sqrt(xx**2 + yy**2)
            proj = (args.projection or "ARC").upper()
            if proj == "SIN":
                r_norm = r_deg / args.proj_size
                za_cart = np.where(r_norm <= 1.0, np.degrees(np.arcsin(r_norm)), np.nan)
            elif proj == "TAN":
                r_norm = r_deg / args.proj_size
                za_cart = np.degrees(np.arctan(r_norm))
            elif proj == "ZEA":
                r_norm = r_deg / args.proj_size
                za_cart = np.where(r_norm <= 2.0, 2.0 * np.degrees(np.arcsin(r_norm / 2.0)), np.nan)
            elif proj == "STG":
                r_norm = r_deg / args.proj_size
                za_cart = 2.0 * np.degrees(np.arctan(r_norm / 2.0))
            else:
                za_cart = r_deg
            az_cart = (np.degrees(np.arctan2(xx, yy)) % 360.0)

            def project_field(Zsrc: np.ndarray) -> np.ndarray:
                interp = RegularGridInterpolator((za_vals, az_vals), Zsrc, bounds_error=False, fill_value=np.nan, method="linear")
                points = np.column_stack([za_cart.ravel(), az_cart.ravel()])
                Zp = interp(points).reshape((npix, npix))
                Zp[za_cart > 90.0] = np.nan
                return Zp

            for i, (hbZ_raw, pyZ_raw, ebZ_raw, title) in enumerate(rows_orig):
                is_mag = ("|" in title)
                hbZp = project_field(hbZ_raw)
                pyZp = project_field(pyZ_raw)
                ebZp = project_field(ebZ_raw)
                hbZ, pyZ, ebZ, vmin, vmax = row_norm(hbZp, pyZp, ebZp, is_mag)
                for j, (Z, lbl) in enumerate([
                    (hbZ, "Hyperbeam"),
                    (pyZ, "PyUVBeam"),
                    (ebZ, "EveryBeam"),
                ]):
                    ax = axs[i, j]
                    im = ax.imshow(
                        Z,
                        origin="upper",
                        extent=extent_proj,
                        aspect="equal",
                        cmap="rainbow",
                        norm=LogNorm(vmin=vmin, vmax=vmax) if is_mag else None,
                        vmin=None if is_mag else vmin,
                        vmax=None if is_mag else vmax,
                    )
                    ax.set_xlabel("E-W offset [deg]")
                    ax.set_ylabel("N-S offset [deg]")
                    ax.set_title(f"{lbl} {title} — {proj}")
                    fig.colorbar(im, ax=ax)
            # Overlay test points in projection
            def project_points(points):
                pts = []
                for _name, r_za, az_deg, x_off, y_off in points:
                    if r_za > 90.0:
                        continue
                    # Inverse of projection mapping used above
                    # For small fields, use linear ARC mapping for marker placement
                    pts.append((x_off, y_off))
                return pts
            pts = project_points(grid_points + [("Z",0.0,0.0,0.0,0.0)])
            for (x, y) in pts:
                for r in range(6):
                    for c in range(3):
                        axs[r, c].plot(x, y, 'wo', markersize=3, markeredgewidth=0.0, alpha=0.8)
        fig.suptitle(f"MWA beams @ {args.freq_mhz:.2f} MHz — pol {args.pol}")
        fig.savefig(args.out, dpi=150)
        if not args.quiet:
            print(f"Saved {os.path.realpath(args.out)}")


if __name__ == "__main__":
    main()
