# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Spack packaging notes for ps_eor (SWF-8 / MWA Phase-3 GPR stack).

PyPI / import
  - Distribution name: ``ps_eor`` (Marimo / pip sometimes show ``ps-eor``).
  - Imports: ``ps_eor``, and with extra ``ml-gpr`` also ``ps_eor.ml_gpr``.
  - Upstream: https://gitlab.com/flomertens/ps_eor

Versions
  - ``0.34.1``: PyPI sdist; ML-GPR backend is **GPy** (numpy<2, scipy<=1.12).
    Legacy — superseded by 1.0 below, kept for compatibility rollback.
  - ``1.0``: git tag (upstream merged the ``gpytorch_transition`` branch into
    ``master`` and tagged it 1.0 — same commit either way).
    https://gitlab.com/flomertens/ps_eor/-/tags/1.0
    ML-GPR backend is **GPyTorch** (+ torch, pyro-ppl). Default for new work;
    do not mix with the GPy stack in one env.

Hard constraints (0.34.1 / GPy path — legacy)
  - GPy 1.13.2 requires ``numpy<2`` and ``scipy<=1.12`` (declared on PyPI).
  - ``ps_eor.ml_gpr`` still calls ``scipy.integrate.trapz``, removed in SciPy
    >=1.14 — keep SciPy at 1.12.x for the ml-gpr path.
  - healpy / reproject / tables must track the numpy *major* (1.x here).
  - ``py-torch`` via Spack is a multi-hour source build. The SWF-8 image uses
    ``+ml-gpr~torch`` and installs a CPU torch wheel with pip into the view.
  - Do not unify this env with Rapthor's numpy 2.x / scipy 1.14+ stack.

MS → CartDataCube (1.0 / GPyTorch)
  - ps_eor does **not** ingest Measurement Sets directly. Image with WSClean
    (per-channel ``*-image.fits`` + ``*-psf.fits``), then::
      pstool gen_vis_cube IMG_LIST PSF_LIST out.h5 --umin … --umax … …
    or ``CartDataCube.load_from_fits_image_and_psf(...)``.
  - See ``docs/ps_eor-spack-packaging.md`` § "Gridding an MS".

Variants
  - ``+ml-gpr``: MCMC / GPR stack (GPy on 0.34.1; torch/gpytorch/pyro on
    1.0 — install those three via pip when ``~torch``).
  - ``+torch`` (implies ``+ml-gpr``): also depends on ``py-torch`` from Spack.
"""

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyPsEor(PythonPackage):
    """Power spectra and EoR analysis tools (ps_eor), including optional GPR (ml_gpr)."""

    homepage = "https://gitlab.com/flomertens/ps_eor"
    pypi = "ps_eor/ps_eor-0.34.1.tar.gz"
    git = "https://gitlab.com/flomertens/ps_eor.git"

    license("GPL-3.0-or-later")

    version("0.34.1", sha256="bcc07bce4042f825031cf31a42b901b45807469b9e9832e58463aa2f2c065fb4")
    # Tagged release (== upstream gpytorch_transition branch, since merged to
    # master). Pin both tag and commit so the ref can't move under us even if
    # the tag is ever re-pointed upstream.
    # https://gitlab.com/flomertens/ps_eor/-/tags/1.0
    version(
        "1.0",
        tag="1.0",
        commit="fa2b765f42531aaf01361cbeb8ca13a0a120a556",
    )

    variant("ml-gpr", default=True, description="Enable ps_eor[ml-gpr] GPR / MCMC stack")
    variant(
        "torch",
        default=False,
        description="Pull py-torch via Spack (heavy source build). "
        "Prefer pip wheels in container images.",
    )

    depends_on("python@3.10:3.12", type=("build", "run"))
    # 0.34.1's PyPI sdist actually uses poetry (build-backend =
    # "poetry.core.masonry.api" in its pyproject.toml), not setuptools —
    # pip's --no-build-isolation install fails with
    # "BackendUnavailable: Cannot import 'poetry.core.masonry.api'"
    # without this (same issue py-libpipe had).
    depends_on("py-poetry-core", type="build", when="@0.34.1")
    depends_on("py-wheel", type="build")
    # 1.0 uses hatchling (pyproject build-backend).
    depends_on("py-hatchling@1.27:", type="build", when="@1.0")

    # ---- shared core deps ----
    depends_on("py-matplotlib@3.8:", type=("build", "run"))
    depends_on("py-healpy@1.16:", type=("build", "run"))
    depends_on("py-h5py@3.10:", type=("build", "run"))
    depends_on("py-joblib@1.3:", type=("build", "run"))
    depends_on("py-fast-histogram@0.11:", type=("build", "run"))
    depends_on("py-reproject@0.14:", type=("build", "run"))
    depends_on("py-tables@3.9:", type=("build", "run"))
    depends_on("py-pyfftw@0.13:", type=("build", "run"))
    depends_on("py-click@8:", type=("build", "run"))
    depends_on("py-scikit-learn@1.3:", type=("build", "run"))

    # ---- 0.34.1 (GPy): keep the tight NumPy / SciPy pin ----
    with when("@0.34.1"):
        # Upper caps keep the graph on NumPy 1.x (GPy 1.13 / ml_gpr). Newer
        # h5py/tables/numexpr/astropy-healpix releases require NumPy 2.
        # Prefer 1.24.x under gcc 11: Spack marks numpy@1.25 as conflicting with
        # %gcc@11. 1.26+ needs a numexpr overlay (builtin 2.8–2.9 caps at 1.25).
        depends_on("py-numpy@1.20:1.24", type=("build", "run"))
        depends_on("py-scipy@1.10:1.12", type=("build", "run"))
        # Astropy @:6 requires cfitsio@:3, but healpy@1.16 needs cfitsio@4.1: —
        # use Astropy 7.x so the two can share cfitsio 4.
        depends_on("py-astropy@7.0:7.1", type=("build", "run"))
        depends_on("py-astropy-healpix@1.0:1.0.2", type=("build", "run"))
        depends_on("py-numexpr@2.8:2.9", type=("build", "run"))
        depends_on("py-healpy@1.16", type=("build", "run"))
        depends_on("py-h5py@3.10:3.13", type=("build", "run"))
        depends_on("py-tables@3.9:3.9", type=("build", "run"))
        depends_on("py-reproject@0.14:0.14", type=("build", "run"))
        depends_on("py-scikit-learn@1.3:1.5", type=("build", "run"))

    # ---- 1.0: NumPy 2 / modern SciPy OK; no GPy ----
    with when("@1.0"):
        depends_on("py-numpy@1.20:", type=("build", "run"))
        depends_on("py-scipy@1.10:", type=("build", "run"))
        depends_on("py-astropy@6.0:", type=("build", "run"))

    conflicts("~ml-gpr", when="+torch")

    # GPy stack — only on 0.34.1
    with when("@0.34.1 +ml-gpr"):
        depends_on("py-gpy@1.10:1.13.2", type=("build", "run"))
        conflicts("py-gpy@1.12.0")
        depends_on("py-emcee@3.1:", type=("build", "run"))
        depends_on("py-corner@2.2:", type=("build", "run"))
        depends_on("py-dynesty@2:", type=("build", "run"))
        depends_on("py-ultranest@3:", type=("build", "run"))
        depends_on("py-libpipe@0.1.5:", type=("build", "run"))
        depends_on("py-pandas@2.0:2.2", type=("build", "run"))

    # GPyTorch stack — torch/gpytorch/pyro are heavy; Spack only for +torch.
    # With ~torch (image default), install wheels:
    #   pip install 'torch>=2' 'gpytorch>=1.11' 'pyro-ppl>=1.9'
    with when("@1.0 +ml-gpr"):
        depends_on("py-emcee@3.1:", type=("build", "run"))
        depends_on("py-corner@2.2:", type=("build", "run"))
        depends_on("py-dynesty@2:", type=("build", "run"))
        depends_on("py-libpipe@0.1.5:", type=("build", "run"))
        depends_on("py-pandas@2.0:", type=("build", "run"))

    with when("+torch"):
        depends_on("py-torch@2:", type=("build", "run"))

    import_modules = ["ps_eor"]

    def test_import(self):
        python = self.spec["python"].command
        python("-c", "import ps_eor; print('ps_eor', getattr(ps_eor, '__version__', '?'))")
        if self.spec.satisfies("+ml-gpr"):
            python(
                "-c",
                "from ps_eor import ml_gpr; print('ml_gpr OK')",
            )
