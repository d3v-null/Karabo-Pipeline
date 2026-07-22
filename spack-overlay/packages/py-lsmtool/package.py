from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, maintainers, patch, variant, version, when


class PyLsmtool(PythonPackage):
    """LOFAR Sky model tool.

    Overlay copy: shadows the ska-sdp-spack package, so it must carry every
    version pinned by py-rapthor's dependency table (older Rapthor releases
    require older LSMTool commits), plus the facet-robustness patch for
    1.8.0.20260630.
    """

    homepage = "https://lsmtool.readthedocs.io"
    git = "https://git.astron.nl/RD/LSMTool"
    pypi = "lsmtool/lsmtool-1.0.0.tar.gz"

    maintainers("mnijhuis-tos")
    license("GPLv3", checked_by="mnijhuis-tos")

    # Since LSMTool extracts its version from the .git tree, disable
    # caching. Spack omits the .git tree from cached sources.
    version(
        "1.8.0.20260630",
        commit="176ef008534bdd929e58c57b00c0a60e3445ad68",
        no_cache=True,
    )
    version(
        "1.8.0.20260605",
        commit="c099308552fa481f5699d4592d462aadc7c92458",
        no_cache=True,
    )
    version(
        "1.8.0.20260522",
        commit="612927b6e7ad49101ca706e50f5945797b046cd8",
        no_cache=True,
    )
    version(
        "1.8.0.20260407",
        commit="8b6c5a849f163818f6c6d35b525172f08df44a23",
        no_cache=True,
    )
    version(
        "1.8.0.20251128",
        commit="5f590f37a0acbed08c2e4bc0a7ff7ac85c62bd8f",
        no_cache=True,
    )
    version(
        "1.6.2.20251104",
        commit="f9866e8b309673664e70f778475030b07a1a22f8",
        no_cache=True,
    )
    version("1.6.2", tag="v1.6.2", no_cache=True)
    version(
        "1.6.post1",
        sha256="84736672881107d1b607074d14a598b63509d5d66d1c9b4e436f9ae1a57c33a3",
    )
    version(
        "1.6",
        sha256="d06e2ae67fb31d136b5160d0847183061a8da1da6e12c9b7ba128d07810454f2",
    )

    variant(
        "sofia",
        default=False,
        description="Enable SoFiA source finder support",
        when="@1.8.0:",
    )

    depends_on("python@3:", type=("build", "run"))
    depends_on("py-pybind11", type="build")
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-scikit-build-core", type="build")
    depends_on("cmake@3.15:", type="build")
    depends_on("ninja@1.5:", type="build")

    depends_on("py-numpy", type="run", when="@1.6.2:")
    depends_on("py-numpy@1", type="run", when="@:1.6.1")
    depends_on("py-scipy@0.11:", type="run")
    depends_on("py-matplotlib", type="run")
    depends_on("py-astropy@3.2:", type="run")
    depends_on("everybeam@0.6.1:", type="run")
    depends_on("py-casacore", type="run")
    depends_on("py-pyvo", type="run")

    with when("@1.8.0:"):
        depends_on("python@3.10.12:", type=("build", "run"))
        depends_on("py-scikit-build-core@0.10:", type="build")
        depends_on("py-bdsf", type="run")
        depends_on("py-lofar-parameterset@1.1:", type="run")
        depends_on("py-pillow@11.2:", type="run")
        depends_on("py-shapely", type="run")
        depends_on("py-sofia2", type="run", when="+sofia")

    patch("rapthor-facet-robustness.patch", when="@1.8.0.20260630")
