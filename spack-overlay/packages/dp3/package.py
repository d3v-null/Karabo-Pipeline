import os

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage

from spack.package import depends_on, join_path, patch, variant, version, which


# Karabo overlay of ska-sdp-spack's recipe: adds +cuda (CudaPackage) and patches.
class Dp3(CMakePackage, CudaPackage):
    """LOFAR preprocessing software, including averaging,
    flagging, various kinds of calibration and more."""

    homepage = "https://dp3.readthedocs.io"
    git = "https://git.astron.nl/RD/DP3.git"

    version("5.0", tag="v5.0", submodules=True)
    version("5.1", tag="v5.1", submodules=True)
    version("5.2", tag="v5.2", submodules=True)
    version("5.3", tag="v5.3", submodules=True)
    # 5.4 is not an actual DP3 version, however at this commit the DP3_VERSION
    # was set to 5.4.0.
    version(
        "5.4", commit="548828e2fde1a5fc504042b6af384c398b484f79", submodules=True
    )
    version("6.0", tag="v6.0", submodules=True)
    version("6.1", tag="v6.1", submodules=True)
    version("6.2.1", tag="v6.2.1", submodules=True)
    version("6.3", tag="v6.3", submodules=True)
    version("6.4", tag="v6.4", submodules=True)
    version("6.4.1", tag="v6.4.1", submodules=True)
    version("6.5", tag="v6.5", submodules=True)
    version("6.5.1", tag="v6.5.1", submodules=True)
    version(
        "6.5.1.20260109",
        commit="f4b51762b9971e4d5f51b5576a1cbf165c7e52bf",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0",
        tag="v6.6",
        commit="4a8f165a0f5683771cc3c84d041ffe98c14d5ceb",
        submodules=True,
        preferred=True,
    )
    version(
        "6.6.0.20260630",
        commit="1aca2a4762463668e238bff8ccf2d4dd03a1c27d",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260722",
        commit="48ca8dbb396b2f316039bae2b011fcefc8b97ea9",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260731",
        commit="6c8846046df18a767e0e9cfdd2883677b01bcf7b",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260807",
        commit="9743ec54bc5a01455d2a7b7646bace71a55e43a5",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260813",
        commit="d87491b0378be26ef3c5a8ab79d6ceb331123bf1",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260915",
        commit="6097e642b830be3c81a979ca16f13a6626b8cae2",
        submodules=True,
        no_cache=True,
    )
    version(
        "6.6.0.20260923",
        commit="03728e5301bcbf6be1b6b3ee1c7d6b0f2cc2c776",
        submodules=True,
        no_cache=True,
    )
    version("master", branch="master", submodules=True, no_cache=True)

    variant("python", default=True, description="Enable Python support")
    variant("idg", default=False, description="Enable IDG support")
    variant("fast_predict", default=True, description="Enable FastPredict")
    # +cuda builds IterativeDiagonalSolverCuda (ddecal.usegpu=true; diagonal and
    # directioniterative solvers only).

    # Source-parallel predict allocated a full model cube per thread for every
    # time step (~200 MB each for MWA) and summed them one thread at a time
    # under a single mutex. Pool the buffers and reduce in parallel over
    # baselines.
    patch("onepredict-parallel-reduction.patch", when="@6.6.0.20260923")

    # IterativeDiagonalSolverCuda was not updated when SolverBase dropped
    # SolveResult/stat_stream and renamed NSolutions() -> NSubSolutions().
    patch("cuda-solverbase-api.patch", when="@6.6.0.20260923+cuda")
    # cudawrappers caches BUILD_SHARED_LIBS=ON, so FastPredict's TrigDx is
    # built shared and never installed: DP3 then fails with libtrigdx.so not found.
    patch("cuda-static-trigdx.patch", when="@6.6.0.20260923+cuda+fast_predict")
    # usegpu=true built the MC2x2FDiag CUDA solver, but the kernels only handle
    # full 2x2 visibilities: half-sized buffers, out-of-bounds reads, garbage
    # solutions. Use the MC2x2F instantiation (the one DP3's unit tests cover).
    patch("cuda-solver-full-visibilities.patch", when="@6.6.0.20260923+cuda")

    depends_on("c", type="build", when="@:6.4.1")
    depends_on("cxx", type="build")

    depends_on("aoflagger@3.4.0:", when="@master")
    depends_on("aoflagger@3.4.0:3.6.0", when="@6")
    depends_on("aoflagger@3.2.0", when="@5.3:5.4")
    depends_on("aoflagger@3.1.0", when="@5.0:5.2")
    depends_on("casacore@3.7.1:", when="@6.4:")
    depends_on("everybeam@0.9", when="@master")
    depends_on("everybeam@0.9.0", when="@6.6.0.20260923")
    depends_on("everybeam@0.8.3:0.8", when="@6.6.0.20260722:6.6.0.20260915")
    depends_on("everybeam@0.7.4:0.8.2", when="@6.5.1.20260109:6.6.0.20260630")
    depends_on("everybeam@0.7.4:0.7", when="@6.3:6.5.1.0")
    depends_on("everybeam@0.6", when="@6.1:6.2")
    depends_on("everybeam@0.5.3", when="@6.0")
    depends_on("everybeam@0.4.0", when="@5.4")
    depends_on("everybeam@0.3.0", when="@5.3")
    depends_on("everybeam@0.3.0", when="@5.2")
    depends_on("everybeam@0.1.3", when="@5.1")
    depends_on("everybeam@0.1.1", when="@5.0")
    depends_on("idg@1.2.0:1.3", when="+idg")
    depends_on("idg+cuda", when="+idg+cuda")
    depends_on("lofarstman", type="run")
    depends_on("openblas threads=pthreads")
    depends_on("boost+date_time+test+program_options")
    depends_on("hdf5~mpi")
    depends_on("gsl")
    depends_on("git")
    depends_on("python", when="+python")

    def cmake_args(self):
        args = [
            self.define(
                "BLA_VENDOR", "OpenBLAS"
            ),  # Avoid using the system BLAS/LAPACK
            self.define("PORTABLE", True),  # let Spack determine arch build flags
            self.define_from_variant("USE_FAST_PREDICT", "fast_predict"),
        ]
        if self.spec.satisfies("+cuda"):
            args.append(self.define("BUILD_WITH_CUDA", True))
            arches = self.spec.variants["cuda_arch"].value
            if arches and "none" not in arches:
                args.append(self.define("CMAKE_CUDA_ARCHITECTURES", ";".join(arches)))
        stub = self._cuda_stub_dir()
        if stub:
            # Link against the driver stubs so +cuda builds without a GPU/driver.
            flags = f"-L{stub} -Wl,-rpath-link,{stub}"
            for kind in ("EXE", "SHARED", "MODULE"):
                args.append(self.define(f"CMAKE_{kind}_LINKER_FLAGS", flags))
        return args

    def _cuda_stub_dir(self):
        if not self.spec.satisfies("+cuda"):
            return None
        for sub in ("lib64", "lib"):
            stub = join_path(self.spec["cuda"].prefix, sub, "stubs")
            if os.path.isdir(stub):
                return stub
        return None

    def setup_build_environment(self, env):
        print(self.spec.version)
        if (
            self.spec.satisfies("@master")
            or int(str(self.spec.version.joined)) >= 52
        ):
            env.set("OPENBLAS_NUM_THREADS", "1")
        stub = self._cuda_stub_dir()
        if stub:
            env.prepend_path("LIBRARY_PATH", stub)
            env.prepend_path("LD_LIBRARY_PATH", stub)

    def setup_run_environment(self, env):
        env.set("OPENBLAS_NUM_THREADS", "1")
        spec = self.spec
        if "+python" in spec:
            python_version = self.spec.dependencies("python")[0].version.up_to(2)
            env.prepend_path(
                "PYTHONPATH",
                join_path(
                    self.prefix.lib, f"python{python_version}", "site-packages"
                ),
            )

    def test_executables(self):
        """Ensure the executables run."""
        dp3 = which(self.prefix.bin.DP3)
        msoverview = which(self.prefix.bin.msoverview)
        dp3("--version")
        # --version and --help give exit code 1 for msoverview
        msoverview("help=exit")

    def test_python_import(self):
        """Ensure the python module can be imported."""
        if "+python" in self.spec:
            python = self.module.python
            python("-c", "import dp3")
