#!/usr/bin/env python3
"""Headless MWA Phase-3 CHIPS → LOFAR-style GPR plotter (from phase3_gpr_mwa_demo).

Takes a CHIPS grid (directory of *.dat, or .tar.gz, or Pawsey URL), runs the
same load + GPR MCMC pipeline as the Marimo demo, and writes a single combined
PNG (UV SEFD, 2D/1D PS, MCMC convergence, GPR components, excess uv). Use
``gif`` to stitch multiple combined PNGs into one long GIF via ffmpeg.

Credit: analysis by Satyapan Munshi (ANU) — MWA Project Meeting 2026.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# healpy 1.16 × SciPy 1.14 trapz shim (also via sitecustomize on swf8 image)
import scipy.integrate as _si

if not hasattr(_si, "trapz") and hasattr(_si, "trapezoid"):
    _si.trapz = _si.trapezoid  # type: ignore[attr-defined]

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

mpl.rcParams["image.origin"] = "lower"
mpl.rcParams["image.cmap"] = "Spectral_r"
mpl.rcParams["image.interpolation"] = "nearest"
mpl.rcParams["axes.grid"] = False
mpl.use("Agg")

from astropy import constants as const
from astropy.cosmology import WMAP7
from ps_eor import datacube, ml_gpr, pspec, psutil

pspec.psutil.set_cosmology(WMAP7)

DEFAULT_FITTER_DIR = Path(
    os.environ.get(
        "PHASE3_FITTER_DIR",
        "/opt/phase3_gpr/gpr_emulator",
    )
)
FREQ_RANGES = [(170.875, 186.235), (177.275, 192.635), (182.395, 197.755)]
Z_VALS = [7.0, 6.8, 6.5]
FULL_SHAPE = (601, 1200, 384)
COMPLEX64_SIZE = 8
_CHIPS_RE = re.compile(
    r"^(?P<kind>vis_tot|vis_diff|weights|noise_tot|noise_diff)"
    r"_(?P<pol>[a-z]{2})\.(?P<tag>.+)\.dat$"
)
_PRIOR_QS = (0.0015, 0.025, 0.16, 0.84, 0.975, 0.9985)
_OBSID_RE = re.compile(r"(?<!\d)(1[0-9]{9})(?!\d)")


# ---------------------------------------------------------------------------
# CHIPS I/O
# ---------------------------------------------------------------------------


def infer_obsid(*candidates: str | None) -> str | None:
    for c in candidates:
        if not c:
            continue
        m = _OBSID_RE.search(str(c))
        if m:
            return m.group(1)
    return None


def list_chips_sets(data_dir: Path) -> dict[str, dict]:
    groups: dict[tuple[str, str], dict[str, Path]] = {}
    for path in sorted(data_dir.glob("*.dat")):
        match = _CHIPS_RE.match(path.name)
        if match is None:
            continue
        key = (match.group("pol"), match.group("tag"))
        groups.setdefault(key, {})[match.group("kind")] = path
    options: dict[str, dict] = {}
    for (pol, tag), parts in groups.items():
        if not all(k in parts for k in ("vis_tot", "vis_diff", "weights")):
            continue
        options[f"{tag} [{pol}]"] = {
            "pol": pol,
            "tag": tag,
            "vis_tot": parts["vis_tot"],
            "vis_diff": parts["vis_diff"],
            "weights": parts["weights"],
        }
    return options


def infer_shape(vis: Path) -> tuple[int, int, int]:
    n = vis.stat().st_size // COMPLEX64_SIZE
    prod = FULL_SHAPE[0] * FULL_SHAPE[1] * FULL_SHAPE[2]
    if n == prod:
        return FULL_SHAPE
    for nf in (384, 768, 192):
        for nu in (1200, 600):
            if n % (nu * nf) == 0:
                return (n // (nu * nf), nu, nf)
    raise SystemExit(f"cannot infer cube shape for {vis} ({n} complex64 samples)")


def write_mwa_freqs(out: Path, nf: int) -> Path:
    f0 = 167.075e6
    df = 80e3
    freqs = f0 + np.arange(nf) * df
    path = out / "mwa_freqs.npy"
    np.save(path, freqs)
    return path


def download_or_extract(source: str, work: Path) -> Path:
    """Return directory containing vis_tot_*.dat."""
    work.mkdir(parents=True, exist_ok=True)
    src = source.strip()
    if src.startswith("http://") or src.startswith("https://"):
        archive = work / "grids.tar.gz"
        print(f"downloading {src} …", flush=True)
        subprocess.check_call(
            ["curl", "-L", "--fail", "--retry", "3", "-o", str(archive), src]
        )
        src_path = archive
    else:
        src_path = Path(src).expanduser().resolve()

    if src_path.is_dir():
        for cand in src_path.rglob("vis_tot_*.dat"):
            return cand.parent
        raise SystemExit(f"no vis_tot_*.dat under {src_path}")

    if src_path.suffixes[-2:] == [".tar", ".gz"] or src_path.suffix == ".tgz":
        extract = work / "extract"
        extract.mkdir(parents=True, exist_ok=True)
        print(f"extracting {src_path} …", flush=True)
        subprocess.check_call(["tar", "-xzf", str(src_path), "-C", str(extract)])
        for cand in extract.rglob("vis_tot_*.dat"):
            return cand.parent
        raise SystemExit(f"no vis_tot_*.dat inside {src_path}")

    raise SystemExit(f"unsupported source: {source}")


# ---------------------------------------------------------------------------
# Cube helpers (from phase3_gpr_mwa_demo)
# ---------------------------------------------------------------------------


def unfold_u(vis_half_uvshifted):
    Nv_half, Nu, Nf = vis_half_uvshifted.shape
    Nv = 2 * (Nv_half - 1)
    vis_half = np.fft.ifftshift(vis_half_uvshifted, axes=1)
    vis_full = np.empty((Nu, Nv, Nf), dtype=vis_half.dtype)
    vis_full[:, :Nv_half, :] = vis_half.transpose(1, 0, 2)
    v_mirror = (-np.arange(Nv)) % Nv
    k = np.arange(1, Nv_half - 1)
    vis_full[:, Nv - k, :] = np.conj(vis_half[k][:, v_mirror, :]).transpose(1, 0, 2)
    vis_full_shifted = np.fft.fftshift(vis_full, axes=(0, 1))
    return np.flip(vis_full_shifted, axis=1)


def bin_uv_weighted(vis, weights, factor=4):
    Nu, Nv, Nf = vis.shape
    assert Nu % factor == 0 and Nv % factor == 0
    Nu2, Nv2 = Nu // factor, Nv // factor
    vis_r = vis.reshape(Nu2, factor, Nv2, factor, Nf)
    w_r = weights.reshape(Nu2, factor, Nv2, factor, Nf)
    w_sum = w_r.sum(axis=(1, 3))
    vw_sum = (vis_r * w_r).sum(axis=(1, 3))
    vis_binned = np.zeros_like(vw_sum, dtype=vis.dtype)
    mask = w_sum > 0
    vis_binned[mask] = vw_sum[mask] / w_sum[mask]
    return vis_binned, w_sum


def load_chips_cube(vis_tot, vis_diff, weights, freqs, du=2, umin=0, umax=600, freq_ranges=None):
    res = 1 / umax
    n_pix = umax // du
    Nf = len(freqs)
    uu, vv, _ = psutil.get_ungrid_vis_idx((n_pix, n_pix), res, umin, umax)
    meta = datacube.ImageMetaData.from_res(res, (n_pix, n_pix))
    meta.wcs.wcs.cdelt[2] = psutil.robust_freq_width(freqs)
    data = datacube.CartDataCube(
        np.zeros((len(freqs), len(uu)), dtype=np.complex64), uu, vv, freqs, meta
    )
    data.weights = datacube.CartWeightCube(
        np.zeros((len(freqs), len(uu)), dtype=np.float32), uu, vv, freqs, meta
    )
    noise = datacube.CartDataCube(
        np.zeros((len(freqs), len(uu)), dtype=np.complex64), uu, vv, freqs, meta
    )
    noise.weights = datacube.CartWeightCube(
        np.zeros((len(freqs), len(uu)), dtype=np.float32), uu, vv, freqs, meta
    )
    vis_cube = 0.5 * vis_tot
    noise_cube = 0.5 * vis_diff
    factor = int(du / 0.5)
    vis_avg, weights_avg = bin_uv_weighted(unfold_u(vis_cube), unfold_u(weights), factor=factor)
    noise_avg, _ = bin_uv_weighted(unfold_u(noise_cube), unfold_u(weights), factor=factor)
    vis_avg = vis_avg.reshape(n_pix * n_pix, Nf).T
    noise_avg = noise_avg.reshape(n_pix * n_pix, Nf).T
    weights_avg = weights_avg.reshape(n_pix * n_pix, Nf).T
    lamb = const.c.value / freqs
    fov = (data.meta.shape[0] * data.meta.res) ** 2
    jy2k = ((1e-26 * lamb**2) / (2 * const.k_B.value)) / fov
    data.data = vis_avg * jy2k[:, None]
    data.weights.data = weights_avg
    noise.data = noise_avg * jy2k[:, None]
    noise.weights.data = weights_avg
    if freq_ranges is None:
        return data, noise
    flags_freq = []
    for band_i in range(3):
        flag_freq = np.zeros_like(data.freqs, dtype=bool)
        freq_min = freq_ranges[band_i][0] * 1e6
        freq_max = freq_ranges[band_i][1] * 1e6
        for freq_i in range(len(data.freqs)):
            if freq_min <= data.freqs[freq_i] <= freq_max:
                flag_freq[freq_i] = True
        flags_freq.append(flag_freq)
    data_z, noise_z = [], []
    for band_i in range(3):
        data_flag = data.copy()
        noise_flag = noise.copy()
        flag = flags_freq[band_i]
        data_flag.data = data.data[flag]
        data_flag.weights.data = data.weights.data[flag]
        data_flag.freqs = data.freqs[flag]
        data_flag.weights.freqs = data.weights.freqs[flag]
        noise_flag.data = noise.data[flag]
        noise_flag.weights.data = noise.weights.data[flag]
        noise_flag.freqs = noise.freqs[flag]
        noise_flag.weights.freqs = noise.weights.freqs[flag]
        data_z.append(data_flag)
        noise_z.append(noise_flag)
    return data_z, noise_z


def correct_decoherence(ps_obj, factor=2.15):
    ps_obj.data = ps_obj.data * factor
    ps_obj.err = ps_obj.err * factor
    return ps_obj


def prior_quantile_bands(sampler_or_result):
    from ps_eor.ml_gpr.samplers import _prior_quantile_bands as _pqb

    flat = getattr(sampler_or_result, "flat_params", None)
    if flat is None:
        raise AttributeError("sampler/result missing flat_params")
    return _pqb(flat, list(_PRIOR_QS))


def stitch_spatial_ps(
    ps_lo,
    ps_hi,
    *,
    split_hz: float | None = None,
    mode: str = "cut",
    match_scale: bool = False,
    blend_edge: float = 0.15,
):
    """Stack lower+upper SpatialPowerSpectra along frequency.

    Parameters
    ----------
    mode:
      ``cut`` — hard split at midpoint of overlap (default; good for residual).
      ``blend`` — in the overlap, cross-fade lo→hi after optional scale match
      (better for excess, whose absolute GPR amplitude jumps between bands).
    match_scale:
      Rescale the upper half so its median |P| in the overlap matches the
      lower half (applied before cut/blend). Needed for excess continuity.
    blend_edge:
      Unused (kept for API stability); blend uses a linear weight across the
      full overlap.
    """
    from ps_eor.pspec import SpatialPowerSpectra

    del blend_edge  # reserved
    f_lo = np.asarray(ps_lo.freqs, dtype=float)
    f_hi = np.asarray(ps_hi.freqs, dtype=float)
    overlap_lo = float(max(f_lo.min(), f_hi.min()))
    overlap_hi = float(min(f_lo.max(), f_hi.max()))
    has_overlap = overlap_hi > overlap_lo
    if not has_overlap:
        split = float(f_lo.max())
    else:
        split = float(split_hz) if split_hz is not None else 0.5 * (overlap_lo + overlap_hi)

    k_lo = np.asarray(ps_lo.k_per, dtype=float)
    k_hi = np.asarray(ps_hi.k_per, dtype=float)
    d_lo_all = np.asarray(ps_lo.data, dtype=float)
    e_lo_all = np.asarray(ps_lo.err, dtype=float)
    d_hi_all = np.asarray(ps_hi.data, dtype=float)
    e_hi_all = np.asarray(ps_hi.err, dtype=float)

    def _align_k(d_src, e_src, k_src):
        if k_lo.shape == k_src.shape and np.allclose(k_lo, k_src, rtol=1e-3, atol=0):
            return d_src, e_src
        d_out = np.empty((d_src.shape[0], k_lo.size), dtype=float)
        e_out = np.empty_like(d_out)
        for i in range(d_src.shape[0]):
            d_out[i] = np.interp(k_lo, k_src, d_src[i], left=np.nan, right=np.nan)
            e_out[i] = np.interp(k_lo, k_src, e_src[i], left=np.nan, right=np.nan)
        return d_out, e_out

    d_hi_all, e_hi_all = _align_k(d_hi_all, e_hi_all, k_hi)
    k_per = k_lo
    el = np.asarray(ps_lo.el)
    cl = bool(getattr(ps_lo, "cl", False))

    scale = 1.0
    if match_scale and has_overlap:
        ov_lo = (f_lo >= overlap_lo) & (f_lo <= overlap_hi)
        ov_hi = (f_hi >= overlap_lo) & (f_hi <= overlap_hi)
        med_lo = float(np.nanmedian(np.abs(d_lo_all[ov_lo])))
        med_hi = float(np.nanmedian(np.abs(d_hi_all[ov_hi])))
        if med_hi > 0 and np.isfinite(med_lo) and np.isfinite(med_hi):
            scale = med_lo / med_hi
            d_hi_all = d_hi_all * scale
            e_hi_all = e_hi_all * scale

    if mode == "cut" or not has_overlap:
        m_lo = f_lo < split
        m_hi = f_hi >= split
        if not np.any(m_lo) or not np.any(m_hi):
            raise ValueError(
                f"stitch produced empty half (split={split:.3e} Hz, "
                f"lo={f_lo.min():.3e}–{f_lo.max():.3e}, hi={f_hi.min():.3e}–{f_hi.max():.3e})"
            )
        freqs = np.concatenate([f_lo[m_lo], f_hi[m_hi]])
        data = np.concatenate([d_lo_all[m_lo], d_hi_all[m_hi]], axis=0)
        err = np.concatenate([e_lo_all[m_lo], e_hi_all[m_hi]], axis=0)
    elif mode == "blend":
        # Unique freq grid: all lo freqs below overlap, blended overlap, all hi above.
        below = f_lo < overlap_lo
        above = f_hi > overlap_hi
        # Overlap freq axis: union of both, sorted unique
        f_ov = np.unique(
            np.concatenate(
                [f_lo[(f_lo >= overlap_lo) & (f_lo <= overlap_hi)],
                 f_hi[(f_hi >= overlap_lo) & (f_hi <= overlap_hi)]]
            )
        )
        # Interpolate each band onto f_ov along frequency for every k bin
        def _interp_freq(freqs_src, data_src, freqs_dst):
            out = np.empty((freqs_dst.size, data_src.shape[1]), dtype=float)
            for j in range(data_src.shape[1]):
                out[:, j] = np.interp(freqs_dst, freqs_src, data_src[:, j], left=np.nan, right=np.nan)
            return out

        d_lo_ov = _interp_freq(f_lo, d_lo_all, f_ov)
        e_lo_ov = _interp_freq(f_lo, e_lo_all, f_ov)
        d_hi_ov = _interp_freq(f_hi, d_hi_all, f_ov)
        e_hi_ov = _interp_freq(f_hi, e_hi_all, f_ov)
        # Linear weight: 0 at overlap_lo (all lower), 1 at overlap_hi (all upper)
        w = (f_ov - overlap_lo) / (overlap_hi - overlap_lo)
        w = np.clip(w, 0.0, 1.0)[:, None]
        d_ov = (1.0 - w) * d_lo_ov + w * d_hi_ov
        e_ov = np.sqrt(((1.0 - w) * e_lo_ov) ** 2 + (w * e_hi_ov) ** 2)

        parts_f = [f_lo[below], f_ov, f_hi[above]]
        parts_d = [d_lo_all[below], d_ov, d_hi_all[above]]
        parts_e = [e_lo_all[below], e_ov, e_hi_all[above]]
        # drop empty
        freqs = np.concatenate([p for p in parts_f if p.size])
        data = np.concatenate([p for p in parts_d if p.size], axis=0)
        err = np.concatenate([p for p in parts_e if p.size], axis=0)
    else:
        raise ValueError(f"unknown stitch mode: {mode!r}")

    order = np.argsort(freqs)
    freqs, data, err = freqs[order], data[order], err[order]
    return SpatialPowerSpectra(data, err, freqs, el, k_per, cl=cl, n_eff=None), {
        "split_hz": split,
        "scale": scale,
        "mode": mode,
        "match_scale": match_scale,
        "overlap_hz": [overlap_lo, overlap_hi] if has_overlap else None,
    }


def plot_mcmc_convergence(sampler_result, ax_grid=None):
    chain = sampler_result.samples.samples
    log_prob = sampler_result.samples.log_prob
    ndim = sampler_result.get_n_params()
    names = list(sampler_result.get_parameter_names()) + ["likelihood"]
    ncols = 4
    nrows = int(np.ceil((ndim + 1) / ncols))
    if ax_grid is None:
        fig, axs = plt.subplots(
            ncols=ncols, nrows=nrows, figsize=(10, 0.7 + 1.1 * nrows), sharex=True
        )
        own_fig = True
    else:
        fig = ax_grid.flat[0].figure
        axs = ax_grid
        own_fig = False
    prior_quantiles = prior_quantile_bands(sampler_result)
    steps = np.arange(chain.shape[0])
    n_burn = int(getattr(sampler_result.samples, "n_burn", 50) or 50)
    for j, ax in enumerate(np.atleast_1d(axs).ravel()):
        if j > ndim:
            ax.axis("off")
            continue
        if j < ndim:
            data = chain[:, :, j]
            qs = prior_quantiles[j]
            ax.axhspan(qs[0], qs[-1], color=psutil.green, alpha=0.08)
            ax.axhspan(qs[1], qs[-2], color=psutil.green, alpha=0.08)
            ax.axhspan(qs[2], qs[-3], color=psutil.green, alpha=0.08)
        else:
            data = log_prob
        ax.plot(steps, data, c="tab:orange", alpha=0.45, lw=0.6)
        med = float(np.median(data[:, -min(20, data.shape[1]) :]))
        ax.text(
            0.04,
            0.95,
            f"{names[j]}: {med:.3g}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=5.5,
        )
        ax.tick_params(labelsize=6, length=2, pad=1)
        if n_burn > 0:
            ax.axvline(n_burn, c=psutil.black, ls="--", lw=0.6, alpha=0.7)
    if own_fig:
        fig.tight_layout(pad=0.1)
    return fig


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    data_dir: Path,
    *,
    out_png: Path,
    fitter_dir: Path,
    obsid: str | None,
    redshift_idx: int = 1,
    n_steps: int = 200,
    n_walkers: int = 100,
    seed: int = 0,
    freqs_npy: Path | None = None,
) -> dict:
    t0 = time.perf_counter()
    sets = list_chips_sets(data_dir)
    if not sets:
        raise SystemExit(f"no CHIPS sets under {data_dir}")
    selected = next(iter(sets.values()))
    tag = selected["tag"]
    obsid = obsid or infer_obsid(tag, data_dir.name, str(data_dir))
    title_id = obsid or tag

    shape = infer_shape(selected["vis_tot"])
    freqs_path: Path | None = None
    for cand in (
        Path(freqs_npy) if freqs_npy else None,
        data_dir.parent / "mwa_freqs.npy",
        data_dir / "mwa_freqs.npy",
    ):
        if cand is not None and cand.is_file():
            freqs_path = cand
            break
    if freqs_path is None:
        freqs_path = write_mwa_freqs(data_dir, shape[2])

    print(f"[{title_id}] loading cubes shape={shape} tag={tag}", flush=True)
    vis_tot = np.fromfile(selected["vis_tot"], dtype=np.complex64).reshape(shape)
    vis_diff = np.fromfile(selected["vis_diff"], dtype=np.complex64).reshape(shape)
    weights = np.fromfile(selected["weights"], dtype=np.float32).reshape(shape)
    mwa_freqs = np.load(freqs_path)

    du = 2
    factor = int(du / 0.5)
    umax_from_shape = int(shape[1] // factor * du)
    umax_load = 600 if umax_from_shape >= 600 else umax_from_shape
    data_z, noise_z = load_chips_cube(
        vis_tot, vis_diff, weights, mwa_freqs, du=du, umax=umax_load, freq_ranges=FREQ_RANGES
    )
    del vis_tot, vis_diff, weights

    ps_build = pspec.PowerSpectraBuilder()
    ps_gens, ps_gens_avoid, kbins = [], [], []
    umin, umax = 20, 250
    if umax > umax_load:
        umax = int(umax_load)
    if umin >= umax:
        umin = 0
    for zi in range(3):
        ps_gen = ps_build.get(
            data_z[zi],
            fmhz_range=[FREQ_RANGES[zi][0], FREQ_RANGES[zi][1]],
            du=2,
            umin=umin,
            umax=umax,
            rmean_freqs=False,
            window_fct="blackmanharris",
            primary_beam="ant_4.4_1.0_gaussian",
            ft_method="lssa",
        )
        umin_av = psutil.k_to_l(0.025, z=ps_gen.z) / (2 * np.pi)
        umax_av = psutil.k_to_l(0.045, z=ps_gen.z) / (2 * np.pi)
        ps_gen_avoid = ps_build.get(
            data_z[zi],
            fmhz_range=[FREQ_RANGES[zi][0], FREQ_RANGES[zi][1]],
            du=2,
            umin=umin_av,
            umax=umax_av,
            rmean_freqs=False,
            window_fct="blackmanharris",
            primary_beam="ant_4.4_1.0_gaussian",
            ft_method="lssa",
            filter_kpar_min=0.11,
        )
        ps_gens.append(ps_gen)
        ps_gens_avoid.append(ps_gen_avoid)
        kbins.append(
            np.linspace(
                ps_gens[zi].kmin,
                np.sqrt(ps_gens[zi].k_per.max() ** 2 + ps_gens[zi].k_par.max() ** 2),
                50,
            )
        )

    for zi in range(3):
        data_z[zi].filter_uvrange(umin, umax)
        noise_z[zi].filter_uvrange(umin, umax)

    sefds = [data_z[zi].make_diff_cube().estimate_uv_sefd() for zi in range(3)]
    ps2ds = []
    for zi in range(3):
        ps2d_noise = correct_decoherence(ps_gens[zi].get_ps2d(noise_z[zi]))
        cube_ps2d = correct_decoherence(ps_gens[zi].get_ps2d(data_z[zi]))
        cube_ps2d.data = cube_ps2d.data - ps2d_noise.data
        ps2ds.append(cube_ps2d)

    kbins_avoid, ps3ds, ps3ds_noise = [], [], []
    for zi in range(3):
        kbins_avoid.append(
            np.linspace(
                ps_gens_avoid[zi].kmin,
                np.sqrt(
                    ps_gens_avoid[zi].k_per.max() ** 2 + ps_gens_avoid[zi].k_par.max() ** 2
                ),
                50,
            )
        )
        ps3d_noise = correct_decoherence(
            ps_gens_avoid[zi].get_ps3d(kbins_avoid[zi], noise_z[zi])
        )
        cube_ps3d = correct_decoherence(
            ps_gens_avoid[zi].get_ps3d(kbins_avoid[zi], data_z[zi])
        )
        cube_ps3d.data = cube_ps3d.data - ps3d_noise.data
        cube_ps3d.err = np.sqrt(cube_ps3d.err**2 + ps3d_noise.err**2)
        ps3ds.append(cube_ps3d)
        ps3ds_noise.append(ps3d_noise)

    # ---- GPR (primary band + lower/upper halves for residual/excess ~30 MHz) ----
    from ps_eor.ml_gpr import config as gpr_config
    from ps_eor.ml_gpr import kernels as gpr_kernels
    from ps_eor.ml_gpr import multidata as gpr_multidata
    from ps_eor.ml_gpr import regressor as gpr_regressor
    from ps_eor.ml_gpr import samplers as gpr_samplers
    from ps_eor.ml_gpr import vae as gpr_vae
    from ps_eor.ml_gpr.vae import PreProcessorFlatten, VAEFitterPreProc

    iz = int(redshift_idx)
    # Lower / upper halves of the ~30 MHz Phase-3 window (z=7.0 / z=6.5).
    # Full-span residual/excess cannot live in one SpatialPS (per-band GPR), so
    # we fit both halves and plot them side-by-side.
    band_indices = sorted({0, iz, 2})
    comp_list = ["fg0", "fg1", "ex", "eor"]

    def _run_gpr_band(band_i: int, band_seed: int):
        fitter_path = (
            Path(fitter_dir) / f"vae_z{Z_VALS[band_i]}_n2000_9params_2latent_v0.0.pt"
        )
        if not fitter_path.is_file():
            raise SystemExit(f"missing VAE fitter: {fitter_path}")
        print(
            f"[{title_id}] GPR MCMC z={Z_VALS[band_i]} "
            f"({FREQ_RANGES[band_i][0]}–{FREQ_RANGES[band_i][1]} MHz) "
            f"steps={n_steps} walkers={n_walkers}",
            flush=True,
        )
        data_gpr = data_z[band_i].copy()
        noise_gpr = noise_z[band_i].copy()
        data_gpr.data = np.asarray(data_gpr.data, dtype=np.complex128)
        noise_gpr.data = np.asarray(noise_gpr.data, dtype=np.complex128)
        data_gpr.weights.data = np.asarray(data_gpr.weights.data, dtype=np.float64)
        noise_gpr.weights.data = np.asarray(noise_gpr.weights.data, dtype=np.float64)
        m_data = gpr_multidata.MultiData(data_gpr, noise_cube=noise_gpr, uv_bins_du=10)

        vae_fitter = gpr_vae.VAEFitter.load(str(fitter_path))
        if isinstance(vae_fitter, VAEFitterPreProc):
            pre_proc = vae_fitter.pre_proc
        else:
            pre_proc = PreProcessorFlatten(vae_fitter.k_mean)
        _vae_model = vae_fitter.model
        _vae_dtype = next(_vae_model.parameters()).dtype

        def _vae_decode(z, _model=_vae_model, _dtype=_vae_dtype):
            return _model.decode(z.to(dtype=_dtype))

        k_eor = gpr_kernels.VAEKernTorch(
            _vae_decode,
            k_mean=vae_fitter.k_mean,
            latent_dim=vae_fitter.n_dim,
            pre_proc=pre_proc,
            name="eor",
        )
        for i in range(int(vae_fitter.n_dim)):
            k_eor.set_free(f"x{i + 1}", gpr_config.make_prior("Uniform", -3, 3))
        k_eor.set_free(
            "variance", gpr_config.make_prior("Log10Uniform", -10, -9), log_scale=True
        )
        k_fg0 = gpr_config.build_kern_from_dict(
            "MRBF",
            "fg0",
            {
                "variance": {"prior": "Log10Uniform(-1, 0)", "log_scale": True},
                "lengthscale": {"prior": "Uniform(5, 30)"},
                "ls_alpha": {"prior": "Fixed(0)"},
                "var_alpha": {"prior": "Fixed(0)"},
            },
        )
        k_fg1 = gpr_config.build_kern_from_dict(
            "MRBF",
            "fg1",
            {
                "variance": {"prior": "Log10Uniform(-1, 0)", "log_scale": True},
                "lengthscale": {"prior": "Uniform(1, 5)"},
                "ls_alpha": {"prior": "Uniform(5, 15)"},
                "var_alpha": {"prior": "Fixed(0)"},
            },
        )
        k_ex = gpr_config.build_kern_from_dict(
            "MExponential",
            "ex",
            {
                "variance": {"prior": "Log10Uniform(-5, -2)", "log_scale": True},
                "lengthscale": {"prior": "Uniform(0.01, 1)"},
                "ls_alpha": {"prior": "Fixed(0)"},
                "var_alpha": {"prior": "Fixed(0)"},
            },
        )
        k_noise = gpr_kernels.WhiteHeteroscedasticKernel(name="noise")
        k_noise.set_free("alpha", gpr_config.make_prior("Uniform", 0.5, 2))
        gp = gpr_regressor.MultiGPRegressor(
            m_data,
            {"eor": k_eor, "fg0": k_fg0, "fg1": k_fg1, "ex": k_ex, "noise": k_noise},
        )
        sampler = gpr_samplers.MCMCSampler(gp, n_walkers, emcee_moves="kde")
        np.random.seed(band_seed)
        result = sampler.run(n_steps, live_update=False)
        result.samples.n_burn = min(50, max(0, n_steps // 4))

        ps_res = result.get_ps_stack(
            ps_gens[band_i],
            kbins[band_i],
            n_pick=5,
            kern_name="fg*",
            subtract_from=data_z[band_i],
        )
        comps = [ps_res]
        for comp in comp_list:
            comps.append(
                result.get_ps_stack(
                    ps_gens[band_i], kbins[band_i], n_pick=5, kern_name=comp
                )
            )
        ex_cubes = [*result.generate_data_cubes(1, kern_name="ex")]
        return result, comps, ex_cubes

    gpr_by_band: dict[int, tuple] = {}
    for bi, band_i in enumerate(band_indices):
        print(f"[{title_id}] building component stacks for z={Z_VALS[band_i]}…", flush=True)
        gpr_by_band[band_i] = _run_gpr_band(band_i, seed + bi)

    sampler_result, ps_comps, ex_cube = gpr_by_band[iz]
    ex_chan = 50 if ex_cube[0].data.shape[0] > 50 else ex_cube[0].data.shape[0] - 1
    # Residual / excess: stitch z=7.0 (lower) + z=6.5 (upper) with a hard cut
    # through the overlap midpoint (no blend / no amplitude rescaling — short
    # MCMC can look discontinuous on excess; full-length chains are fine).
    res_lo = gpr_by_band[0][1][0].get_ps()
    res_hi = gpr_by_band[2][1][0].get_ps()
    ex_lo = gpr_by_band[0][1][3].get_ps()  # "ex" is index 3 in comps
    ex_hi = gpr_by_band[2][1][3].get_ps()
    res_full, res_stitch = stitch_spatial_ps(res_lo, res_hi, mode="cut", match_scale=False)
    ex_full, ex_stitch = stitch_spatial_ps(ex_lo, ex_hi, mode="cut", match_scale=False)
    f_span = (
        float(res_full.freqs.min()) * 1e-6,
        float(res_full.freqs.max()) * 1e-6,
    )
    split_mhz = float(res_stitch["split_hz"]) * 1e-6
    ex_scale = float(ex_stitch.get("scale") or 1.0)

    # ---- Combined figure ----
    print(f"[{title_id}] rendering combined PNG…", flush=True)
    # Fixed canvas — do NOT let legends/colorbars grow height via bbox_inches=tight.
    fig = plt.figure(figsize=(22, 28), constrained_layout=False)
    fig.suptitle(
        f"MWA Phase-3 CHIPS → GPR  ·  obsid={title_id}  ·  tag={tag}  ·  "
        f"primary z={Z_VALS[iz]}  ·  residual/excess {f_span[0]:.1f}–{f_span[1]:.1f} MHz",
        fontsize=13,
        fontweight="bold",
        y=0.995,
    )
    gs = fig.add_gridspec(
        7,
        12,
        height_ratios=[1.0, 1.15, 0.95, 1.15, 1.15, 1.55, 1.05],
        hspace=0.55,
        wspace=0.40,
        left=0.055,
        right=0.97,
        top=0.96,
        bottom=0.035,
    )

    # Row 0: UV SEFD
    for zi in range(3):
        ax = fig.add_subplot(gs[0, zi * 4 : (zi + 1) * 4])
        sefds[zi].plot_uv(ax=ax, norm=LogNorm(vmin=1e3, vmax=5e3))
        ax.set_title(f"UV SEFD  z={Z_VALS[zi]:.1f}  [{title_id}]", fontsize=9)

    # Row 1: 2D PS
    for zi in range(3):
        ax = fig.add_subplot(gs[1, zi * 4 : (zi + 1) * 4])
        ps2ds[zi].plot(
            ax=ax,
            wedge_lines=[90],
            z=Z_VALS[zi],
            vmin=1e0,
            vmax=1e7,
            colorbar=(zi == 2),
        )
        if zi != 0:
            ax.set_ylabel("")
        ax.set_title(f"PS 2D  z={Z_VALS[zi]:.1f}  [{title_id}]", fontsize=9)
        ax.set_yscale("log")
        ax.set_xscale("log")

    # Row 2: 1D PS
    for zi in range(3):
        ax = fig.add_subplot(gs[2, zi * 4 : (zi + 1) * 4])
        ax.step(ps3ds[zi].k_bins[:-1], ps3ds[zi].data * 1e6, where="post", label="P(k)")
        ax.step(
            ps3ds_noise[zi].k_bins[:-1],
            2 * ps3ds_noise[zi].err * 1e6,
            where="mid",
            label="2σ noise",
        )
        ax.set_title(f"PS 1D  z={Z_VALS[zi]:.1f}  [{title_id}]", fontsize=9)
        ax.set_xlabel(r"$k\,[h\,\mathrm{cMpc}^{-1}]$")
        if zi == 0:
            ax.set_ylabel(r"$P(k)\,[\mathrm{mK}^2]$")
            ax.legend(fontsize=6, loc="best", frameon=False)
        ax.set_yscale("log")
        ax.set_xscale("log")

    # Row 3: MCMC convergence (compact)
    ndim = sampler_result.get_n_params()
    ncols_c = 4
    nrows_c = int(np.ceil((ndim + 1) / ncols_c))
    inner = gs[3, :].subgridspec(nrows_c, ncols_c, hspace=0.22, wspace=0.22)
    axs_c = np.array(
        [[fig.add_subplot(inner[r, c]) for c in range(ncols_c)] for r in range(nrows_c)]
    )
    plot_mcmc_convergence(sampler_result, ax_grid=axs_c)
    axs_c.flat[0].set_title(
        f"MCMC convergence z={Z_VALS[iz]} (n_burn={sampler_result.samples.n_burn})  [{title_id}]",
        fontsize=8,
        loc="left",
    )

    # Row 4: GPR components 2D (primary band)
    ncols_comp = len(comp_list) + 3
    width = 12 // ncols_comp
    for ci in range(ncols_comp):
        ax = fig.add_subplot(gs[4, ci * width : (ci + 1) * width])
        if ci == 0:
            ps_gens[iz].get_ps2d(data_z[iz]).plot(ax=ax, wedge_lines=[90], z=Z_VALS[iz])
            ax.set_title(f"Data [{title_id}]", fontsize=8)
        elif ci == 1:
            ps_comps[0].get_ps2d().plot(ax=ax, wedge_lines=[90], z=Z_VALS[iz])
            ax.set_title("Residual", fontsize=8)
        elif ci < ncols_comp - 1:
            comp = comp_list[ci - 2]
            comp_ps2d = ps_comps[ci - 1].get_ps2d()
            if "fg" in comp:
                comp_ps2d.plot(ax=ax, wedge_lines=[90], z=Z_VALS[iz], vmin=1e-1)
            else:
                comp_ps2d.plot(ax=ax, wedge_lines=[90], z=Z_VALS[iz])
            ax.set_title(comp, fontsize=8)
        else:
            ps_gens[iz].get_ps2d(noise_z[iz]).plot(ax=ax, wedge_lines=[90], z=Z_VALS[iz])
            ax.set_title("Noise", fontsize=8)
        if ci != 0:
            ax.set_ylabel("")
        ax.set_xscale("log")
        ax.set_yscale("log")

    # Row 5: residual + excess stitched across ~30 MHz (hard cut, no blend)
    ax_r = fig.add_subplot(gs[5, 0:6])
    ax_e = fig.add_subplot(gs[5, 6:12])
    res_full.plot(ax=ax_r, title=None, k_only=True)
    ax_r.set_title(
        f"Residual  {f_span[0]:.1f}–{f_span[1]:.1f} MHz  "
        f"(z7.0∪z6.5, cut@{split_mhz:.1f})  [{title_id}]",
        fontsize=9,
    )
    if np.isfinite(split_mhz):
        ax_r.axhline(split_mhz, color="k", ls=":", lw=0.8, alpha=0.5)
    ex_full.plot(ax=ax_e, title=None, k_only=True)
    ax_e.set_title(
        f"Excess  {f_span[0]:.1f}–{f_span[1]:.1f} MHz  "
        f"(z7.0∪z6.5, cut@{split_mhz:.1f})  [{title_id}]",
        fontsize=9,
    )
    if np.isfinite(split_mhz):
        ax_e.axhline(split_mhz, color="k", ls=":", lw=0.8, alpha=0.5)

    # Row 6: excess uv abs / angle (primary band) + compact 1D component curves
    ax_abs = fig.add_subplot(gs[6, 0:4])
    ax_ang = fig.add_subplot(gs[6, 4:8])
    ax_fp = fig.add_subplot(gs[6, 8:12])
    ex_abs = abs(ex_cube[0].data[ex_chan, :])
    im_abs = ax_abs.scatter(
        ex_cube[0].uu,
        ex_cube[0].vv,
        marker="s",
        s=4,
        c=ex_abs,
        norm=LogNorm(vmin=1e-4, vmax=1e-2),
        cmap="hot_r",
    )
    fig.colorbar(im_abs, ax=ax_abs, fraction=0.046, pad=0.02)
    ax_abs.set_xlim(-100, 100)
    ax_abs.set_ylim(-100, 100)
    ax_abs.set_title(
        f"Excess |V| @ chan {ex_chan}  z={Z_VALS[iz]}  [{title_id}]", fontsize=8
    )
    im_ang = ax_ang.scatter(
        ex_cube[0].uu,
        ex_cube[0].vv,
        marker="s",
        s=4,
        c=np.angle(ex_cube[0].data[ex_chan, :]),
        vmin=-np.pi,
        vmax=np.pi,
        cmap="Spectral_r",
    )
    fig.colorbar(im_ang, ax=ax_ang, fraction=0.046, pad=0.02)
    ax_ang.set_xlim(-100, 100)
    ax_ang.set_ylim(-100, 100)
    ax_ang.set_title(
        f"Excess arg(V) @ chan {ex_chan}  z={Z_VALS[iz]}  [{title_id}]", fontsize=8
    )

    labels = ["Residual", *comp_list]
    for li, ps_comp in enumerate(ps_comps):
        try:
            ps_comp.get_ps().plot_kper(
                ax=ax_fp, show68=False, show95=False, label=labels[li], alpha=0.9
            )
        except TypeError:
            ps_comp.get_ps().plot_kper(ax=ax_fp, show68=False, show95=False)
            if ax_fp.lines:
                ax_fp.lines[-1].set_label(labels[li])
        except Exception:
            continue
    ax_fp.set_title(f"GPR components P(k⊥) z={Z_VALS[iz]}  [{title_id}]", fontsize=8)
    handles, labs = ax_fp.get_legend_handles_labels()
    if handles:
        seen = {}
        for h, lab in zip(handles, labs):
            if lab and not lab.startswith("_") and lab not in seen:
                seen[lab] = h
        if seen:
            ax_fp.legend(
                seen.values(),
                seen.keys(),
                fontsize=5,
                loc="upper right",
                frameon=True,
                framealpha=0.85,
                borderpad=0.3,
                labelspacing=0.2,
                handlelength=1.2,
            )
    ax_fp.set_xscale("log")
    ax_fp.set_yscale("log")

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    elapsed = round(time.perf_counter() - t0, 1)
    meta = {
        "obsid": title_id,
        "tag": tag,
        "shape": list(shape),
        "redshift": Z_VALS[iz],
        "residual_excess_mhz": [f_span[0], f_span[1]],
        "residual_excess_split_mhz": split_mhz if np.isfinite(split_mhz) else None,
        "excess_stitch": {
            "mode": ex_stitch.get("mode"),
            "match_scale": ex_stitch.get("match_scale"),
            "scale": ex_scale,
            "overlap_mhz": (
                [x * 1e-6 for x in ex_stitch["overlap_hz"]]
                if ex_stitch.get("overlap_hz")
                else None
            ),
        },
        "n_steps": n_steps,
        "n_walkers": n_walkers,
        "png": str(out_png),
        "elapsed_s": elapsed,
    }
    try:
        from PIL import Image as _Image

        _im = _Image.open(out_png)
        meta["png_size_px"] = [_im.size[0], _im.size[1]]
    except Exception:
        pass
    meta_path = out_png.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"[{title_id}] wrote {out_png} ({elapsed}s)", flush=True)
    return meta


def stitch_gif(frames: list[Path], out_gif: Path, *, fps: float = 1.0, hold: float = 1.5) -> Path:
    """Stitch PNGs into a long GIF with ffmpeg (palettegen for quality)."""
    if not frames:
        raise SystemExit("no frames to stitch")
    out_gif = Path(out_gif)
    out_gif.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("ffmpeg not found on PATH")

    with tempfile.TemporaryDirectory(prefix="phase3-gif-") as tmp:
        tmp_path = Path(tmp)
        # Build concat demuxer list with duration per frame
        lst = tmp_path / "frames.txt"
        lines = []
        for fr in frames:
            fr = Path(fr).resolve()
            if not fr.is_file():
                raise SystemExit(f"missing frame: {fr}")
            lines.append(f"file '{fr}'")
            lines.append(f"duration {hold}")
        # last frame must be listed again without duration for concat demuxer
        lines.append(f"file '{Path(frames[-1]).resolve()}'")
        lst.write_text("\n".join(lines) + "\n")

        palette = tmp_path / "palette.png"
        # Scale to even dims; generate palette then apply
        vf_scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        subprocess.check_call(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-vf",
                f"{vf_scale},palettegen=stats_mode=full",
                str(palette),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-i",
                str(palette),
                "-lavfi",
                f"{vf_scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                "-loop",
                "0",
                str(out_gif),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"wrote {out_gif} ({len(frames)} frames)", flush=True)
    return out_gif


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    work = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="phase3-run-"))
    work.mkdir(parents=True, exist_ok=True)
    data_dir = download_or_extract(args.grid, work / "data")
    obsid = args.obsid or infer_obsid(args.grid, data_dir.name, str(data_dir))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = obsid or "phase3"
    out_png = out_dir / f"{stem}_combined.png"
    run_pipeline(
        data_dir,
        out_png=out_png,
        fitter_dir=Path(args.fitter_dir),
        obsid=obsid,
        redshift_idx=args.redshift_idx,
        n_steps=args.n_steps,
        n_walkers=args.n_walkers,
        seed=args.seed,
        freqs_npy=Path(args.freqs) if args.freqs else None,
    )
    return 0


def cmd_gif(args: argparse.Namespace) -> int:
    frames = [Path(p) for p in args.frames]
    stitch_gif(frames, Path(args.out), fps=args.fps, hold=args.hold)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    url_tmpl = args.url_template
    frames: list[Path] = []
    for obsid in args.obsids:
        url = url_tmpl.format(obsid=obsid)
        work = out_dir / f"work_{obsid}"
        work.mkdir(parents=True, exist_ok=True)
        # Prefer local archive if provided via --grids-dir
        source = url
        if args.grids_dir:
            local = Path(args.grids_dir) / f"grid_{obsid}.tar.gz"
            if local.is_file():
                source = str(local)
        data_dir = download_or_extract(source, work / "data")
        out_png = out_dir / f"{obsid}_combined.png"
        if out_png.is_file() and not args.force:
            print(f"[{obsid}] skip existing {out_png}", flush=True)
        else:
            run_pipeline(
                data_dir,
                out_png=out_png,
                fitter_dir=Path(args.fitter_dir),
                obsid=str(obsid),
                redshift_idx=args.redshift_idx,
                n_steps=args.n_steps,
                n_walkers=args.n_walkers,
                seed=args.seed,
            )
        frames.append(out_png)
    gif_path = out_dir / args.gif_name
    stitch_gif(frames, gif_path, hold=args.hold)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phase3-gpr-plot",
        description="CHIPS grid → combined Phase-3 GPR diagnostic PNG (+ ffmpeg GIF)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    z_choices = {f"z={z}": i for i, z in enumerate(Z_VALS)}

    def add_common(sp):
        sp.add_argument(
            "--fitter-dir",
            default=str(DEFAULT_FITTER_DIR),
            help="directory with vae_z*.pt",
        )
        sp.add_argument(
            "--redshift-idx",
            type=int,
            default=1,
            choices=[0, 1, 2],
            help="0=z7.0 1=z6.8 2=z6.5 (default 1)",
        )
        sp.add_argument("--n-steps", type=int, default=int(os.getenv("PHASE3_GPR_STEPS", "200")))
        sp.add_argument("--n-walkers", type=int, default=100)
        sp.add_argument("--seed", type=int, default=int(os.getenv("PHASE3_GPR_SEED", "0")))

    run_p = sub.add_parser("run", help="process one grid → combined PNG")
    run_p.add_argument("--grid", required=True, help="dir | .tar.gz | URL")
    run_p.add_argument("--out", required=True, help="output directory")
    run_p.add_argument("--obsid", default=None)
    run_p.add_argument("--freqs", default=None, help="optional mwa_freqs.npy")
    run_p.add_argument("--work-dir", default=None)
    add_common(run_p)
    run_p.set_defaults(func=cmd_run)

    gif_p = sub.add_parser("gif", help="stitch PNGs into a long GIF with ffmpeg")
    gif_p.add_argument("frames", nargs="+", help="PNG paths in order")
    gif_p.add_argument("--out", required=True)
    gif_p.add_argument("--fps", type=float, default=1.0)
    gif_p.add_argument("--hold", type=float, default=1.5, help="seconds per frame")
    gif_p.set_defaults(func=cmd_gif)

    batch_p = sub.add_parser("batch", help="download/run many obsids + stitch GIF")
    batch_p.add_argument("obsids", nargs="+", help="GPS obsids")
    batch_p.add_argument("--out", required=True)
    batch_p.add_argument(
        "--url-template",
        default=(
            "https://projects.pawsey.org.au/high1.grids/"
            "grid_{obsid}.ionosub_ssins_30l_src8k_300it_8s_80kHz_i1000.yy.tar.gz"
        ),
    )
    batch_p.add_argument("--grids-dir", default=None, help="local dir of grid_*.tar.gz")
    batch_p.add_argument("--gif-name", default="phase3_obsids_combined.gif")
    batch_p.add_argument("--hold", type=float, default=2.0)
    batch_p.add_argument("--force", action="store_true")
    add_common(batch_p)
    batch_p.set_defaults(func=cmd_batch)

    # silence unused
    _ = z_choices
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
