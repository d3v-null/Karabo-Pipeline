from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, variant, version


class PyCodexAfricanus(PythonPackage):
    """codex-africanus: radio astronomy building blocks (numba/dask)."""

    homepage = "https://github.com/ratt-ru/codex-africanus"
    pypi = "codex-africanus/codex_africanus-0.4.3.tar.gz"

    license("BSD-3-Clause")

    version(
        "0.4.3",
        sha256="5b05e5df7f66c3af78828d0c871481b113b957f7656c7bb2308e0164f9e146c8",
    )

    variant("dask", default=True, description="dask array support")
    variant("scipy", default=True, description="scipy-based functionality")
    variant("astropy", default=True, description="astropy-based functionality")
    variant("casacore", default=True, description="python-casacore support")

    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-hatchling", type="build")

    depends_on("py-appdirs@1.4.4:", type=("build", "run"))
    depends_on("py-decorator@5.1.1:", type=("build", "run"))
    depends_on("py-numpy@2.0:", type=("build", "run"))
    depends_on("py-numba@0.60:", type=("build", "run"))

    depends_on("py-dask@2024.0:+array", type=("build", "run"), when="+dask")
    depends_on("py-scipy@1.14.1:", type=("build", "run"), when="+scipy")
    # Upstream pins astropy>=6.1.4 in the 'astropy' extra; the image ships
    # astropy 6.1.0, which provides everything africanus uses.
    depends_on("py-astropy@6.1.0:", type=("build", "run"), when="+astropy")
    depends_on("py-casacore@3.6.1:", type=("build", "run"), when="+casacore")

    patch("astropy-6.1.0.patch", when="@0.4.3")

    import_modules = ["africanus"]
