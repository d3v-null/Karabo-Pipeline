# Packaging `ps_eor` for Spack (SWF-8)

Lessons from installing the MWA Phase-3 CHIPS → LOFAR-style GPR stack
(`ps_eor[ml-gpr]`) into a Python 3.11 Jupyter/Marimo image, then encoding
that into the Karabo Spack overlay.

## Names

| Role | Value |
|------|--------|
| PyPI / Spack | `ps_eor` / `py-ps-eor` |
| Marimo banner | often shows `ps-eor` (normalized) |
| Import | `import ps_eor` / `from ps_eor import ml_gpr` |
| Upstream | https://gitlab.com/flomertens/ps_eor |
| Proven pin (GPy) | `0.34.1` |
| Git pin (GPyTorch) | `gpytorch_transition` @ `955d4109e89bde0990ce50979f2cf45c6fcd290e` |

Spack:

```text
karabo.py-ps-eor@0.34.1+ml-gpr~torch          # legacy GPy backend
karabo.py-ps-eor@gpytorch_transition+ml-gpr~torch   # GPyTorch backend
```

The `gpytorch_transition` version tracks
https://gitlab.com/flomertens/ps_eor/-/tree/gpytorch_transition
(`pyproject` package version `1.0`). Its `ml-gpr` extra is **torch +
gpytorch + pyro-ppl** (not GPy). With `~torch`, install those via pip into
the view after `spack install`.

## Hard version constraints (0.34.1 / GPy)

GPy 1.13.2 (required by `ml-gpr` on 0.34.1) declares on PyPI:

- `numpy<2.0.0,>=1.7`
- `scipy<=1.12.0,>=1.3.0`

Additionally, `ps_eor.ml_gpr` still uses `scipy.integrate.trapz`, which SciPy
removed in 1.14. **Keep the env on NumPy 1.26.x and SciPy 1.12.x.**

Do **not** unify this environment with the Rapthor/numpy2 stack
(`rapthor-jupyter.Dockerfile`).

Working pin set used in the JupyterHub marimo image (pip):

```
numpy==1.26.4
scipy==1.12.0
ps_eor==0.34.1
GPy==1.13.2
healpy==1.16.6
astropy==6.1.7
astropy-healpix==1.0.3
reproject==0.14.1
pandas==2.2.3
scikit-learn==1.5.2
torch==2.6.0          # CPU wheel via pip
zarr==2.18.3
```

Spack concretizer notes:

- `py-numexpr@2.8:2.9` only allows `numpy@:1.25`; `py-numexpr@2.10.2:`
  wants NumPy 2 at build → stay on NumPy 1.24.x under Spack.
- `numpy@1.25` conflicts with `%gcc@11` in builtin → prefer `1.24.4`.
- Cap `tables@3.9.x`, `h5py@:3.13`, `astropy-healpix@:1.0.2`.
- Astropy `@:6` requires `cfitsio@:3` while healpy `@1.16` needs
  `cfitsio@4.1:` → pin Astropy 7.0.x in the Spack env.
- Keep `karabo.py-healpy` (scipy through 1.12) for `healpy@1.16.6`.
- Pin `py-dask ~dataframe ~distributed` so reproject does not pull pyarrow.
- Pin `py-pyerfa@2.0.1.1` (overlay relaxes its NumPy floor to 1.24); newer
  pyerfa wants NumPy 2 at build.
- Pip can still use `numpy==1.26.4` / `astropy==6.1.7` as in the JH image.
## Overlay packages

Under `spack-overlay/packages/`:

| Package | Why |
|---------|-----|
| `py-ps-eor` | Root recipe; `+ml-gpr`, optional `+torch` |
| `py-gpy` | Overlay: enforce numpy&lt;2 / scipy≤1.12 for 1.13.x |
| `py-fast-histogram` | Core dep (C extension) |
| `py-dynesty` | `ml-gpr` extra (missing from builtin) |
| `py-ultranest` | `ml-gpr` extra (Cython) |
| `py-libpipe` | `ml-gpr` extra |
| `py-asyncssh` | `libpipe` dep (missing from builtin) |

Builtin already has: `py-emcee`, `py-corner`, `py-torch`, `py-imageio`,
`py-tqdm`, `py-scikit-learn`, `py-healpy`, `py-reproject`, `py-tables`, …

Prefer `builtin.py-healpy` from `py-ps-eor`: the Karabo `py-healpy` overlay
pins SciPy to 1.10.x, which fights the 1.12 pin.

## Torch

`py-torch` via Spack is a long source build. For container images use:

```text
karabo.py-ps-eor@0.34.1+ml-gpr~torch
```

then `pip install torch==2.6.0` (CPU wheel) into the Spack view. Set `+torch`
only when you intentionally want a Spack-built torch.

## Build host deps

When GPy/ultranest/fast-histogram compile from source:

- `build-essential`, `gfortran`
- BLAS headers help pip builds; Spack usually brings its own OpenBLAS

## Marimo / JupyterHub note

With `MarimoProxyConfig.no_sandbox=True`, PEP 723 script dependencies are
**not** installed by uv. Anything a demo imports must already be on the image.
Do not list local helper modules (e.g. `common_lib`) as pip deps.

## Image

See `swf8-jupyter.Dockerfile` (SWF-8 counterpart to `rapthor-jupyter.Dockerfile`).

## Gridding an MS into a `CartDataCube`

`ps_eor` (including `gpytorch_transition`) does **not** read Measurement Sets.
The supported path is **image-plane → FFT → visibility cube**:

1. **WSClean** the MS into per-channel image + PSF FITS (Jy/PSF).
2. **`pstool gen_vis_cube`** (or
   `CartDataCube.load_from_fits_image_and_psf`) to build an HDF5 cube.

This matches the upstream README on `gpytorch_transition` and the older
PyPI docs for [`gen_vis_cube`](https://pypi.org/project/ps_eor/). WSClean’s
[`-channels-out`](https://wsclean.readthedocs.io/en/latest/making_image_cubes.html)
produces the frequency-ordered FITS cubes; ps_eor sorts on `CRVAL3` and uses
the PSF (or `WSCNORMF`) for Jy/PSF → K.

### Example: MS → FITS → HDF5

```bash
# 1) Per-channel dirty images + PSFs (adjust scale/size/weighting to the MS).
#    Output names: out-0000-image.fits, out-0000-psf.fits, …
NCHAN=$(…)   # or use -channels-out N and -channel-range
wsclean \
  -name out \
  -size 1024 1024 \
  -scale 0.5amin \
  -weight natural \
  -make-psf \
  -no-update-model-required \
  -channels-out "${NCHAN}" \
  -pol I \
  /path/to/data.ms

# 2) File lists sorted by frequency (pstool also sorts on CRVAL3).
ls out-????-image.fits > img.list
ls out-????-psf.fits   > psf.list

# 3) Visibility cube for GPR / power spectra (umin/umax in λ;
#    --theta_fov in degrees; times as astropy Quantity strings).
pstool gen_vis_cube img.list psf.list \
  -o visibilities.h5 \
  --umin 50 --umax 250 --theta_fov 4 \
  --int_time 10s --total_time 10h
```

Python equivalent on `gpytorch_transition`:

```python
from pathlib import Path
import numpy as np
from ps_eor import datacube, psutil

image_files = psutil.sort_by_fits_key(
    [str(p) for p in Path(".").glob("out-????-image.fits")], "CRVAL3"
)
psf_files = psutil.sort_by_fits_key(
    [str(p) for p in Path(".").glob("out-????-psf.fits")], "CRVAL3"
)
cube = datacube.CartDataCube.load_from_fits_image_and_psf(
    image_files,
    psf_files,
    umin=50,
    umax=250,
    theta_fov=np.radians(4),
    int_time=10,
    total_time=10 * 3600,
)
cube.save("visibilities.h5")
```

Notes:

- Prefer **dirty** (or lightly cleaned) images with a matching PSF for EoR
  cubes; heavy cleaning can bias the noise/PSF normalization.
- Even/odd or time-split MSs → two cubes → `pstool even_odd_to_sum_diff` for
  signal / noise-proxy pairs used by ML-GPR.
- The Phase-3 demo’s CHIPS `*.dat` path is a **different** ingest (already
  gridded UV cubes). For arbitrary SKA-Low / LOFAR MSs, use WSClean →
  `gen_vis_cube` above — do not feed raw MS paths into `ml_gpr`.
