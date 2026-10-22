from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import (
    depends_on,
    filter_file,
    license,
    maintainers,
    variant,
    version,
    which,
)


class PyBdsf(PythonPackage):
    """Blob Detection and Source Finder"""

    homepage = "https://pybdsf.readthedocs.io"
    git = "https://github.com/lofar-astron/PyBDSF"
    pypi = "bdsf/bdsf-1.0.0.tar.gz"

    maintainers("mnijhuis-tos")
    license("GPLv3", checked_by="mnijhuis-tos")

    # Since bdsf determines its version from the .git tree (using
    # setuptools_scm), disable caching.
    # Otherwise, Spack omits the .git tree from cached sources.
    version(
        "1.13.0.20250915",
        commit="3d705ee77732592fc8ffe972582059a1a1dfbb28",
        no_cache=True,
    )

    version(
        "1.13.0.20251010",
        commit="f528a63ebb3e1b49dccf296dc339e62ef61a0a4e",
        no_cache=True,
    )

    version(
        "1.13.0.20260409",
        commit="5b0bc9cd7e0c76190c0bbe8b88665c63f741b6a0",
        no_cache=True,
    )

    version(
        "1.14.1",
        commit="1b6e0a04ba6327bc1ce3f576928fe58b81d8c1cc",
        tag="v1.14.1",
        no_cache=True,
    )

    version(
        "1.14.1.20260723",
        commit="754be462b9ca883917e8556c7bb65b4b031fd3a1",
        no_cache=True,
    )

    variant(
        "rap",
        default=False,
        description="Support reading 'rap' images using CasaCore.",
    )

    depends_on("python@3.8:", type="build")
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools@:70", when="^python@:3.11", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-scikit-build@0.13:", type="build")
    depends_on("cmake@3.18:", type="build")
    depends_on("ninja", type="build")
    depends_on("meson", type="build")

    depends_on("boost+python+numpy", type=("build", "run"))
    depends_on("py-astropy", type="run")
    depends_on("py-scipy", type="run")
    # BDSF uses f2py from numpy at build time.
    depends_on("py-numpy@1:", type=("build", "run"))
    depends_on("py-matplotlib", type="run")

    # The pybdsf executable needs ipython.
    depends_on("py-ipython", type="run")

    depends_on("py-casacore", type="run", when="+rap")

    def patch(self):
        # This fix ensures PyBDSF uses f2py from the $PATH (from numpy)
        # instead of /usr/bin/f2py3, which may not work.
        filter_file(
            "find_package(F2PY REQUIRED)",
            "set(F2PY_EXECUTABLE f2py)",
            "CMakeLists.txt",
            string=True,
        )

    def test_executable(self):
        """Test that the pybdsf executable runs."""
        # This executable is a short Python script which runs bdsf.pybdsf.main().
        # Running it is therefore a good smoke test.

        pybdsf = which(self.prefix.bin.pybdsf)
        # pybdsf is an interactive application. Using /dev/null as input
        # makes it exit immediately.
        with open("/dev/null", "r", encoding="utf-8") as dev_null:
            pybdsf(input=dev_null)

    def setup_build_environment(self, env):
        # Built from a shallow git commit without tags: give setuptools-scm the real
        # version, or pip sees 0.1.dev1 and may "upgrade" it over the spack install.
        if str(self.version)[0].isdigit():
            env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BDSF", str(self.version))
