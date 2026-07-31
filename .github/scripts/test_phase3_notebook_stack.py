#!/usr/bin/env python3
"""CI gate for SWF-8 image capabilities used by phase3_gpr_mwa_demo.py.

The Marimo demo (ska-src-ef-computing-broker) exercises CHIPS cube ingest,
power spectra, VAE/GPR kernels, emcee MCMC, and GIF export. Build-time
``import ml_gpr`` is not enough — healpy/pspec and the GPR symbol surface
must work too.

Supports both layouts:
  * ps_eor 0.34.x — monolithic ``ps_eor.ml_gpr`` module (GPy)
  * ps_eor 1.0+   — ``ps_eor.ml_gpr`` package (GPyTorch)
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import sys
import tempfile
import traceback
from pathlib import Path


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _pkg_ver(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "missing"


def _ensure_scipy_trapz_compat() -> None:
    """healpy 1.16 still imports scipy.integrate.trapz (removed in SciPy 1.14)."""
    import scipy.integrate as si

    if not hasattr(si, "trapz"):
        if not hasattr(si, "trapezoid"):
            _fail("scipy.integrate has neither trapz nor trapezoid")
        si.trapz = si.trapezoid  # type: ignore[attr-defined]
        _ok("scipy.integrate.trapz ← trapezoid (compat shim applied in-process)")
    else:
        _ok("scipy.integrate.trapz present")


def _require_import(mod: str):
    try:
        return importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001
        _fail(f"import {mod}: {type(exc).__name__}: {exc}")


def _find_attr(owners: list[tuple[str, object]], name: str):
    for label, obj in owners:
        if hasattr(obj, name):
            return getattr(obj, name), label
    return None


def main() -> None:
    print("=== phase3 notebook stack preflight ===")
    print(f"python {sys.version.split()[0]}")
    for pkg in (
        "ps_eor",
        "numpy",
        "scipy",
        "matplotlib",
        "astropy",
        "marimo",
        "torch",
        "gpytorch",
        "pyro-ppl",
        "emcee",
        "corner",
        "imageio",
        "healpy",
        "GPy",
        "h5py",
        "tables",
        "pyfftw",
        "scikit-learn",
        "pandas",
    ):
        print(f"  {pkg}={_pkg_ver(pkg)}")

    _ensure_scipy_trapz_compat()

    # --- imports the notebook does (or relies on) ---
    for mod in (
        "numpy",
        "scipy",
        "matplotlib",
        "matplotlib.pyplot",
        "astropy",
        "astropy.constants",
        "astropy.cosmology",
        "torch",
        "emcee",
        "corner",
        "imageio",
        "tqdm",
        "marimo",
        "healpy",
        "ps_eor",
        "ps_eor.datacube",
        "ps_eor.psutil",
        "ps_eor.pspec",
        "ps_eor.ml_gpr",
    ):
        _require_import(mod)
        _ok(f"import {mod}")

    from astropy.cosmology import WMAP7
    import astropy.constants as const
    import numpy as np
    from ps_eor import datacube, ml_gpr, pspec, psutil

    _ = float(WMAP7.H0.value)
    _ = float(const.c.value)
    _ok(f"astropy WMAP7 H0={WMAP7.H0}  c={const.c}")

    ml_is_pkg = hasattr(ml_gpr, "__path__")
    _ok(f"ps_eor.ml_gpr layout={'package' if ml_is_pkg else 'module'}")

    owners: list[tuple[str, object]] = [("ps_eor.ml_gpr", ml_gpr)]
    if ml_is_pkg:
        for sub in (
            "multidata",
            "vae",
            "kernels",
            "regressor",
            "samplers",
            "priors",
            "fitter",
            "config",
        ):
            owners.append((f"ps_eor.ml_gpr.{sub}", importlib.import_module(f"ps_eor.ml_gpr.{sub}")))

    # Notebook uses these names on 0.34.x; 1.0 renamed some (Uniform→UniformPrior,
    # MRBF→UVScaledKernel('rbf'), MWhiteHeteroscedastic→WhiteHeteroscedasticKernel).
    required = {
        "MultiData": ("MultiData",),
        "VAEFitter": ("VAEFitter",),
        "VAEKernTorch": ("VAEKernTorch",),
        "MultiGPRegressor": ("MultiGPRegressor",),
        "MCMCSampler": ("MCMCSampler",),
        "SamplerResult": ("SamplerResult",),
        "_prior_quantile_bands": ("_prior_quantile_bands",),
        "fg_kernel": ("MRBF", "UVScaledKernel"),
        "exp_kernel": ("MExponential", "UVScaledKernel"),
        "noise_kernel": ("MWhiteHeteroscedastic", "WhiteHeteroscedasticKernel"),
        "uniform_prior": ("Uniform", "UniformPrior"),
    }
    resolved = {}
    for key, names in required.items():
        hit = None
        for name in names:
            hit = _find_attr(owners, name)
            if hit is not None:
                break
        if hit is None:
            _fail(
                f"{key}: none of {names} found on "
                + ", ".join(label for label, _ in owners)
            )
        resolved[key] = hit
        obj, where = hit
        _ok(
            f"{key} → {name} via {where} "
            f"({getattr(obj, '__name__', type(obj).__name__)})"
        )

    # High-level 1.0 entrypoints (optional but expected on @1.0 images)
    if ml_is_pkg:
        for name in ("MLGPRForegroundFitter", "MLGPRConfigFile"):
            if not hasattr(ml_gpr, name):
                _fail(f"ps_eor 1.0 package missing top-level {name}")
            _ok(f"ml_gpr.{name}")

    # Exact names phase3_gpr_mwa_demo.py uses today (`ml_gpr.X`, not submodules).
    # On ps_eor 1.0 these live under submodules / were renamed — fail loudly so
    # we do not ship an image CI-green for GPR while the demo cannot import.
    notebook_flat = (
        "MultiData",
        "VAEFitter",
        "VAEKernTorch",
        "MRBF",
        "MExponential",
        "MWhiteHeteroscedastic",
        "Uniform",
        "MultiGPRegressor",
        "MCMCSampler",
    )
    missing_flat = [n for n in notebook_flat if not hasattr(ml_gpr, n)]
    if missing_flat:
        _fail(
            "phase3_gpr_mwa_demo.py flat API missing on ps_eor.ml_gpr: "
            + ", ".join(missing_flat)
            + ". Either re-export 0.34-compatible aliases from ml_gpr.__init__ "
            "or update the Marimo notebook for the ps_eor 1.0 package API "
            "(UVScaledKernel / UniformPrior / MultiGPRegressor(components=…))."
        )
    _ok("notebook flat ml_gpr.* API present")

    # --- functional: CHIPS-like CartDataCube + MultiData + PS builder ---
    pspec.psutil.set_cosmology(WMAP7)
    du, umin, umax = 10, 30, 100
    res = 1 / umax
    n_pix = umax // du
    freqs = np.linspace(167e6, 187e6, 16)
    uu, vv, _idx = psutil.get_ungrid_vis_idx((n_pix, n_pix), res, umin, umax)
    meta = datacube.ImageMetaData.from_res(res, (n_pix, n_pix))
    meta.wcs.wcs.cdelt[2] = psutil.robust_freq_width(freqs)
    rng = np.random.default_rng(0)
    shape = (len(freqs), len(uu))
    vis = (rng.normal(size=shape) + 1j * rng.normal(size=shape)).astype(np.complex64) * 0.1
    nse = (rng.normal(size=shape) + 1j * rng.normal(size=shape)).astype(np.complex64) * 0.05
    data = datacube.CartDataCube(vis, uu, vv, freqs, meta)
    data.weights = datacube.CartWeightCube(
        np.ones(shape, dtype=np.float32), uu, vv, freqs, meta
    )
    noise = datacube.CartDataCube(nse, uu, vv, freqs, meta)
    noise.weights = data.weights
    _ok(f"CartDataCube n_vis={len(uu)} n_freq={len(freqs)}")

    MultiData = resolved["MultiData"][0]
    m_data = MultiData(data, noise_cube=noise, uv_bins_du=10)
    if not hasattr(m_data, "uv_bins"):
        _fail("MultiData missing uv_bins")
    _ok(f"MultiData uv_bins={getattr(m_data.uv_bins, 'shape', m_data.uv_bins)}")

    ps_build = pspec.PowerSpectraBuilder()
    if not hasattr(pspec, "FourPanelPsResults"):
        _fail("pspec.FourPanelPsResults missing")
    _ok(f"PowerSpectraBuilder={type(ps_build).__name__} FourPanelPsResults OK")

    # Same PowerSpectraBuilder.get(...) call shape as phase3_gpr_mwa_demo.py
    if not hasattr(ps_build, "get"):
        _fail("PowerSpectraBuilder.get missing")
    f_mhz = freqs[[0, -1]] / 1e6
    ps_gen = ps_build.get(
        data,
        fmhz_range=[float(f_mhz[0]), float(f_mhz[1])],
        du=du,
        umin=umin,
        umax=umax,
        rmean_freqs=False,
        window_fct="blackmanharris",
        primary_beam="ant_4.4_1.0_gaussian",
        ft_method="lssa",
    )
    for attr in ("get_ps2d", "get_ps3d", "kmin", "k_per", "k_par", "z"):
        if not hasattr(ps_gen, attr):
            _fail(f"PS generator missing {attr}")
    ps2d = ps_gen.get_ps2d(data)
    _ = psutil.k_to_l(0.025, z=ps_gen.z)
    _ok(
        f"ps_build.get → z={ps_gen.z:.2f} get_ps2d={type(ps2d).__name__} "
        f"k_to_l OK"
    )

    # --- GPR object graph (construct only — full MCMC is too heavy for CI) ---
    import inspect

    VAEFitter = resolved["VAEFitter"][0]
    VAEKernTorch = resolved["VAEKernTorch"][0]
    MultiGPRegressor = resolved["MultiGPRegressor"][0]
    MCMCSampler = resolved["MCMCSampler"][0]
    if not hasattr(VAEFitter, "load"):
        _fail("VAEFitter.load missing")
    _ok("VAEFitter.load present")
    _ok(f"VAEKernTorch{inspect.signature(VAEKernTorch.__init__)}")

    UVScaledKernel = None
    for _label, obj in owners:
        if hasattr(obj, "UVScaledKernel"):
            UVScaledKernel = getattr(obj, "UVScaledKernel")
            break

    try:
        NoiseCls = resolved["noise_kernel"][0]
        if hasattr(ml_gpr, "MRBF"):
            # ps_eor 0.34.x (GPy) — matches phase3_gpr_mwa_demo.py call shape
            k_fg = ml_gpr.MRBF(lengthscale=10, variance=1, name="fg0")
            if hasattr(ml_gpr, "MExponential"):
                k_fg = k_fg + ml_gpr.MExponential(
                    lengthscale=0.1, variance=1, name="ex"
                )
            if hasattr(k_fg, "set_uv_bins"):
                k_fg.set_uv_bins(m_data.uv_bins)
            k_noise = NoiseCls(variance=1, name="noise")
            gp = MultiGPRegressor(m_data, k_fg, k_noise)
            api = "0.34"
        elif UVScaledKernel is not None:
            # ps_eor 1.0 — MultiGPRegressor(multi_data, components: dict)
            k_fg = UVScaledKernel("rbf", lengthscale=10, variance=1, name="fg0")
            mean_fmhz = float(np.mean(freqs) / 1e6)
            if hasattr(k_fg, "bind_data"):
                k_fg.bind_data(m_data.uv_bins, mean_fmhz)
            try:
                k_noise = NoiseCls(variance=1, name="noise")
            except TypeError:
                k_noise = NoiseCls(alpha=1.0, name="noise")
            gp_sig = inspect.signature(MultiGPRegressor.__init__)
            if "components" in gp_sig.parameters or any(
                p.annotation == dict or "dict" in str(p.annotation)
                for p in list(gp_sig.parameters.values())[1:]
            ):
                gp = MultiGPRegressor(m_data, {"fg": k_fg, "noise": k_noise})
            else:
                gp = MultiGPRegressor(m_data, k_fg, k_noise)
            api = "1.0"
        else:
            _fail("cannot construct foreground kernel (no MRBF / UVScaledKernel)")

        try:
            sampler = MCMCSampler(gp, 4, emcee_moves="kde")
        except TypeError:
            sampler = MCMCSampler(gp, n_walkers=4, emcee_moves="kde")
        _ok(
            f"MultiGPRegressor+MCMCSampler(kde) api={api} "
            f"ndim={getattr(sampler, 'ndim', '?')} "
            f"walkers={getattr(sampler, 'n_walkers', '?')}"
        )

        # Likelihood eval when the model has free parameters (priors set).
        ndim = int(getattr(sampler, "ndim", 0) or 0)
        if ndim > 0 and hasattr(sampler, "lnprob"):
            kern = getattr(sampler.gp, "kern", None)
            if kern is not None and hasattr(kern, "optimizer_array"):
                p0 = np.asarray(kern.optimizer_array, dtype=float).copy()
                lp = float(sampler.lnprob(p0))
                _ok(f"sampler.lnprob(p0)={lp}")
            else:
                _ok("sampler.lnprob present (skipped: no optimizer_array)")
        elif ndim == 0:
            _ok("sampler ndim=0 (no free params without priors — construct OK)")
        else:
            _ok("MCMCSampler constructed (lnprob not exercised)")

        prior_fn = resolved["_prior_quantile_bands"][0]
        flat = getattr(sampler, "flat_params", None)
        if flat is not None and ndim > 0:
            bands = prior_fn(flat, [0.16, 0.84])
            _ok(f"_prior_quantile_bands → shape={getattr(bands, 'shape', type(bands))}")
        elif hasattr(sampler, "pp") and hasattr(sampler.pp, "prior_transform") and ndim > 0:
            bands = sampler.pp.prior_transform(
                np.array([[0.16, 0.84]] * ndim)
            )
            _ok(f"pp.prior_transform → shape={getattr(bands, 'shape', type(bands))}")
        else:
            # Symbol presence already checked; empty flat_params on unbound priors.
            _ok("_prior_quantile_bands symbol OK (no free params to transform)")

        for meth in ("get_ps_stack", "generate_data_cubes", "plot_samples"):
            if not hasattr(resolved["SamplerResult"][0], meth):
                _fail(f"SamplerResult.{meth} missing")
        _ok("SamplerResult.get_ps_stack/generate_data_cubes/plot_samples present")

        if ml_is_pkg:
            cfg_cls = getattr(ml_gpr, "MLGPRConfigFile", None)
            fit_cls = getattr(ml_gpr, "MLGPRForegroundFitter", None)
            if cfg_cls is None or fit_cls is None:
                _fail("1.0 missing MLGPRConfigFile / MLGPRForegroundFitter")
            defaults = getattr(cfg_cls, "DEFAULT_SETTINGS", None) or getattr(
                cfg_cls, "get_defaults", lambda: None
            )()
            if defaults and Path(str(defaults)).is_file():
                cfg = cfg_cls.load_with_defaults(str(defaults))
                _ = fit_cls(cfg)
                _ok(f"MLGPRForegroundFitter(defaults={defaults})")
            else:
                _ok("MLGPRForegroundFitter class present (no DEFAULT_SETTINGS file)")
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        _fail("GPR object-graph smoke failed (see traceback)")

    # --- imageio GIF path (movie cell) ---
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import imageio.v2 as imageio

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        png = td_path / "frame.png"
        gif = td_path / "out.gif"
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        fig.savefig(png)
        plt.close(fig)
        frame = imageio.imread(png)
        imageio.mimsave(gif, [frame, frame], fps=2)
        if not gif.is_file() or gif.stat().st_size < 10:
            _fail("imageio.mimsave produced empty gif")
        _ok(f"imageio.mimsave → {gif.stat().st_size} bytes")

    print("=== phase3 notebook stack: ALL CHECKS PASSED ===")


if __name__ == "__main__":
    main()
