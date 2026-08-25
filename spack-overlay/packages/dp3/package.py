# https://gitlab.com/ska-telescope/sdp/ska-sdp-spack/-/raw/5c515ba11992398717151feed33fb74ddf314f2d/packages/dp3/package.py
# remove all versions except 6.5.1.20260109 for MWA support
# +cuda enables DP3 BUILD_WITH_CUDA (HAVE_CUDA_SOLVER). Off by default via CudaPackage.
from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage

from spack.package import depends_on, join_path, patch, variant, version, which
import os


class Dp3(CMakePackage, CudaPackage):
    """LOFAR preprocessing software, including averaging,
    flagging, various kinds of calibration and more."""

    homepage = "https://dp3.readthedocs.io"
    git = "https://git.astron.nl/RD/DP3.git"

    version(
        "6.5.1.20260109",
        commit="f4b51762b9971e4d5f51b5576a1cbf165c7e52bf",
        submodules=True,
        no_cache=True,
    )

    version(
        "6.6",
        commit="4a8f165a0f5683771cc3c84d041ffe98c14d5ceb",
        submodules=True,
        no_cache=True,
    )

    # IterativeDiagonalSolverCuda was not updated when SolverBase
    # dropped SolveResult/stat_stream from ApplyConstraints/Solve and
    # renamed NSolutions() -> NSubSolutions() (76d6920 / 5168437).
    # Without this, +cuda builds fail compiling CudaSolvers.
    patch(
        "cuda-solverbase-api.patch",
        sha256="bd3411d07dbfe919e81fc3cca29519e891ccbff52660d447705fdb54e6d9c13f",
        when="@6.6+cuda",
    )

    variant("python", default=True, description="Enable Python support")
    variant("idg", default=False, description="Enable IDG support")
    # DP3 6.6 defaults USE_FAST_PREDICT=OFF; +fastpredict compiles the
    # accelerated predict library and enables predict.usefastpredict.
    variant(
        "fastpredict",
        default=True,
        description="Enable FastPredict (USE_FAST_PREDICT / predict.usefastpredict)",
    )
    # CudaPackage provides +cuda / cuda_arch. BUILD_WITH_CUDA enables
    # IterativeDiagonalSolverCuda; runtime still needs ddecal.usegpu=true, and
    # that path only covers diagonal+directioniterative (not scalarphase).

    depends_on("c", type="build", when="@:6.4.1")
    depends_on("cxx", type="build")

    depends_on("aoflagger@3.4.0:", when="@latest,master")
    depends_on("aoflagger@3.4.0:", when="@6")
    depends_on("aoflagger@3.2.0", when="@5.3:5.4")
    depends_on("aoflagger@3.1.0", when="@5.0:5.2")
    depends_on("casacore@3.7.1:", when="@6.4:,latest")
    depends_on("everybeam@0.7.4:", when="@latest,master")
    depends_on("everybeam@0.7.4:0.9", when="@6.5.1.20260109:")
    depends_on("everybeam@0.7.4:0.7", when="@6.3:6.5.1.0")
    depends_on("everybeam@0.6", when="@6.1:6.2")
    depends_on("everybeam@0.5.3", when="@6.0")
    depends_on("everybeam@0.4.0", when="@5.4")
    depends_on("everybeam@0.3.0", when="@5.3")
    depends_on("everybeam@0.3.0", when="@5.2")
    depends_on("everybeam@0.1.3", when="@5.1")
    depends_on("everybeam@0.1.1", when="@5.0")
    depends_on("idg@1.2.0:", when="+idg")
    depends_on("idg@1.2.0:+cuda", when="+idg+cuda")
    depends_on("lofarstman", type="run")
    depends_on("openblas threads=pthreads")
    depends_on("boost+date_time+test+program_options")
    depends_on("hdf5~mpi")
    depends_on("gsl")
    depends_on("git")
    depends_on("python", when="+python")

    # xtensor 0.26+ moved headers (xtensor/xtensor.hpp ->
    # xtensor/containers/xtensor.hpp). DP3 6.6 already uses the new paths;
    # the FastPredict submodule still uses the old ones.
    _FASTPREDICT_XTENSOR_INCLUDES = (
        ("#include <xtensor/xtensor_forward.hpp>", "#include <xtensor/core/xtensor_forward.hpp>"),
        ("#include <xtensor/xtensor.hpp>", "#include <xtensor/containers/xtensor.hpp>"),
        ("#include <xtensor/xarray.hpp>", "#include <xtensor/containers/xarray.hpp>"),
        ("#include <xtensor/xadapt.hpp>", "#include <xtensor/containers/xadapt.hpp>"),
        ("#include <xtensor/xview.hpp>", "#include <xtensor/views/xview.hpp>"),
        ("#include <xtensor/xindex_view.hpp>", "#include <xtensor/views/xindex_view.hpp>"),
        ("#include <xtensor/xcomplex.hpp>", "#include <xtensor/misc/xcomplex.hpp>"),
        ("#include <xtensor/xmath.hpp>", "#include <xtensor/core/xmath.hpp>"),
        ("#include <xtensor/xlayout.hpp>", "#include <xtensor/core/xlayout.hpp>"),
        ("#include <xtensor/xshape.hpp>", "#include <xtensor/core/xshape.hpp>"),
        ("#include <xtensor/xbuilder.hpp>", "#include <xtensor/generators/xbuilder.hpp>"),
        ("#include <xtensor/xrandom.hpp>", "#include <xtensor/generators/xrandom.hpp>"),
        ("#include <xtensor/xio.hpp>", "#include <xtensor/io/xio.hpp>"),
        ("#include <xtensor/xcsv.hpp>", "#include <xtensor/io/xcsv.hpp>"),
    )

    def patch(self):
        if "+fastpredict" not in self.spec:
            return
        predict = join_path(self.stage.source_path, "external", "predict")
        if not os.path.isdir(predict):
            return
        for dirpath, _, filenames in os.walk(predict):
            for name in filenames:
                if not name.endswith((".h", ".hpp", ".cpp", ".cc")):
                    continue
                path = os.path.join(dirpath, name)
                with open(path) as fh:
                    text = fh.read()
                new = text
                for old, repl in self._FASTPREDICT_XTENSOR_INCLUDES:
                    new = new.replace(old, repl)
                if new != text:
                    with open(path, "w") as fh:
                        fh.write(new)

        # 6.6 FastPredict.cc includes aocommon threading headers that are not
        # in the pinned aocommon, and uses ThreadPool without including it.
        fast_predict = join_path(self.stage.source_path, "steps", "FastPredict.cc")
        if os.path.isfile(fast_predict):
            with open(fast_predict) as fh:
                text = fh.read()
            new = text
            for inc in (
                "#include <aocommon/barrier.h>\n",
                "#include <aocommon/recursivefor.h>\n",
                "#include <aocommon/staticfor.h>\n",
            ):
                new = new.replace(inc, "")
            if "#include <aocommon/threadpool.h>" not in new:
                new = new.replace(
                    "#include <aocommon/logger.h>\n",
                    "#include <aocommon/logger.h>\n#include <aocommon/threadpool.h>\n",
                )
            if new != text:
                with open(fast_predict, "w") as fh:
                    fh.write(new)

    def _cuda_stub_dir(self):
        if "+cuda" not in self.spec:
            return None
        cuda_prefix = self.spec["cuda"].prefix
        for stub in (
            os.path.join(cuda_prefix, "lib64", "stubs"),
            os.path.join(cuda_prefix, "lib", "stubs"),
        ):
            if os.path.isdir(stub):
                return stub
        return None

    def cmake_args(self):
        args = [
            self.define("PORTABLE", True),  # let Spack determine arch build flags
            self.define_from_variant("USE_FAST_PREDICT", "fastpredict"),
        ]

        if "+cuda" in self.spec:
            args.append(self.define("BUILD_WITH_CUDA", True))
            arches = list(self.spec.variants["cuda_arch"].value)
            if arches:
                args.append(self.define("CMAKE_CUDA_ARCHITECTURES", ";".join(arches)))

        stub = self._cuda_stub_dir()
        if stub:
            # Link against driver stubs so CUDA builds succeed without a GPU/driver.
            flags = f"-L{stub} -Wl,-rpath-link,{stub}"
            args.append(self.define("CMAKE_EXE_LINKER_FLAGS", flags))
            args.append(self.define("CMAKE_SHARED_LINKER_FLAGS", flags))
            args.append(self.define("CMAKE_MODULE_LINKER_FLAGS", flags))

        return args

    def setup_build_environment(self, env):
        print(self.spec.version)
        if (
            self.spec.satisfies("@latest")
            or self.spec.satisfies("@master")
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
        showsourcedb = which(self.prefix.bin.showsourcedb)
        dp3("--version")
        # --version and --help give exit code 1 for msoverview and showsourcedb
        msoverview("help=exit")
        showsourcedb("help=exit")

    def test_python_import(self):
        """Ensure the python module can be imported."""
        if "+python" in self.spec:
            python = self.module.python
            python("-c", "import dp3")
