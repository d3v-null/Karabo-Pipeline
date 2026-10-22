import os

from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import (
    InstallError,
    depends_on,
    filter_file,
    join_path,
    variant,
    version,
    which,
)


# Karabo overlay of ska-sdp-spack's recipe: pins cudawrappers (see patch()).
class Idg(CMakePackage):
    """Image Domain Gridding (IDG) is a fast method for convolutional
    resampling (gridding/degridding) of radio astronomical data (visibilities).
    Direction dependent effects (DDEs) or A-tems can be applied in the gridding
    process."""

    homepage = "https://idg.readthedocs.io"
    git = "https://git.astron.nl/RD/idg.git"

    version("0.8.1", tag="0.8.1", submodules=True)
    version("1.0.0", tag="1.0.0", submodules=True)
    version("1.1.0", tag="1.1.0", submodules=True)
    version("1.2.0", tag="1.2.0", submodules=True)
    version(
        "1.3.0",
        # The 1.3.0 tag is broken since it doesn't contain the correct version.
        # Use the next commit, which (only) sets the version to 1.3.0.
        commit="faf26bc081e2017f33a3c96d8b7d76804b405a21",
        submodules=True,
        no_cache=True,
    )
    version("master", branch="master", submodules=True)

    variant("cuda", default=False, description="Enable CUDA support")
    variant("python", default=False, description="Enable Python support")
    variant("report", default=False, description="Enable performance reporting")

    depends_on("c", type="build", when="@:1.2.0")
    depends_on("cxx", type="build")

    depends_on("boost")
    depends_on("fftw")
    depends_on("openblas")
    depends_on("cuda", when="+cuda")
    depends_on("python", when="+python")
    depends_on("git")
    depends_on("pkg-config")
    depends_on("py-numpy", when="+python")

    def patch(self):
        # idg-lib FetchContents cudawrappers at floating `main`, which now
        # requires CUDA >= 12.4 (CUdevResourceDesc). Pin the 1.0.0 release.
        cmake = join_path("idg-lib", "CMakeLists.txt")
        if not os.path.isfile(cmake):
            return
        with open(cmake) as fh:
            text = fh.read()
        if "nlesc-recruit/cudawrappers" not in text or "GIT_TAG 1.0.0)" in text:
            return
        if "GIT_TAG main)" not in text:
            raise InstallError("idg: unexpected cudawrappers GIT_TAG; update the pin")
        filter_file(r"GIT_TAG main\)", "GIT_TAG 1.0.0)", cmake)

    def cmake_args(self):
        args = [
            # let Spack determine arch build flags
            self.define("PORTABLE", True),
            self.define("BUILD_LIB_CPU", True),
            self.define_from_variant("BUILD_LIB_CUDA", "cuda"),
            self.define_from_variant("BUILD_WITH_PYTHON", "python"),
            self.define_from_variant("PERFORMANCE_REPORT", "report"),
        ]
        return args

    def setup_run_environment(self, env):
        env.prepend_path("PATH", join_path(self.prefix.bin, "examples", "cxx"))
        if "+python" in self.spec:
            env.prepend_path(
                "PATH", join_path(self.prefix.bin, "examples", "python")
            )
            python_version = self.spec.dependencies("python")[0].version.up_to(2)
            env.prepend_path(
                "PYTHONPATH",
                join_path(
                    self.prefix.lib, f"python{python_version}", "site-packages"
                ),
            )

    def test_executables(self):
        """Ensure that the example executables run."""
        which(getattr(self.prefix.bin.examples.cxx, "idg-plan.x"))()

        os.environ["NR_STATIONS"] = "2"  # Speeds up the examples
        which(getattr(self.prefix.bin.examples.cxx, "cpu-optimized.x"))()
        which(getattr(self.prefix.bin.examples.cxx, "cpu-reference.x"))()

    def test_python_import(self):
        """Ensure that the python module can be imported."""
        if "+python" in self.spec:
            python = self.module.python
            python("-c", "import idg")
