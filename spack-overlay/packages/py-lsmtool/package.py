from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, maintainers, patch, variant, version, when


class PyLsmtool(PythonPackage):
    """LOFAR Sky model tool."""

    homepage = "https://lsmtool.readthedocs.io"
    git = "https://git.astron.nl/RD/LSMTool"
    pypi = "lsmtool/lsmtool-1.0.0.tar.gz"

    maintainers("mnijhuis-tos")
    license("GPLv3", checked_by="mnijhuis-tos")

    version(
        "1.8.0.20260630",
        commit="176ef008534bdd929e58c57b00c0a60e3445ad68",
        no_cache=True,
    )

    variant(
        "sofia",
        default=False,
        description="Enable SoFiA source finder support",
        when="@1.8.0:",
    )

    depends_on("python@3.10.12:", type=("build", "run"))
    depends_on("py-pybind11", type="build")
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-scikit-build-core@0.10:", type="build")
    depends_on("cmake@3.15:", type="build")
    depends_on("ninja@1.5:", type="build")

    depends_on("py-numpy", type="run")
    depends_on("py-scipy@0.11:", type="run")
    depends_on("py-matplotlib", type="run")
    depends_on("py-astropy@3.2:", type="run")
    depends_on("everybeam@0.6.1:", type="run")
    depends_on("py-casacore", type="run")
    depends_on("py-pyvo", type="run")
    depends_on("py-bdsf", type="run")
    depends_on("py-lofar-parameterset@1.1:", type="run")
    depends_on("py-pillow@11.2:", type="run")
    depends_on("py-shapely", type="run")
    depends_on("py-sofia2", type="run", when="+sofia")

    patch("rapthor-facet-robustness.patch", when="@1.8.0.20260630")
