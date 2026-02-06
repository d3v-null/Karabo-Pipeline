# https://gitlab.com/ska-telescope/sdp/ska-sdp-spack/-/raw/5c515ba11992398717151feed33fb74ddf314f2d/packages/dp3/package.py
# remove all versions except 6.5.1.20260109 for MWA support
from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import depends_on, join_path, variant, version, which
import os


class Dp3(CMakePackage):
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

    variant("python", default=True, description="Enable Python support")
    variant("idg", default=False, description="Enable IDG support")

    depends_on("c", type="build", when="@:6.4.1")
    depends_on("cxx", type="build")

    depends_on("aoflagger@3.4.0:", when="@latest,master")
    depends_on("aoflagger@3.4.0", when="@6")
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
    depends_on("idg@1.2.0:1.2", when="+idg")
    depends_on("lofarstman", type="run")
    depends_on("openblas threads=pthreads")
    depends_on("boost+date_time+test+program_options")
    depends_on("hdf5~mpi")
    depends_on("gsl")
    depends_on("git")
    depends_on("python", when="+python")

    def cmake_args(self):
        args = [
            self.define("PORTABLE", True)  # let Spack determine arch build flags
        ]

        if "idg" in self.spec and "+cuda" in self.spec["idg"]:
            cuda_prefix = self.spec["idg"]["cuda"].prefix
            stubs_dirs = [os.path.join(cuda_prefix, "lib64", "stubs"), os.path.join(cuda_prefix, "lib", "stubs")]
            for stub in stubs_dirs:
                if os.path.isdir(stub):
                    args.append(self.define("CMAKE_EXE_LINKER_FLAGS", f"-L{stub} -Wl,-rpath-link,{stub}"))
                    args.append(self.define("CMAKE_SHARED_LINKER_FLAGS", f"-L{stub} -Wl,-rpath-link,{stub}"))
                    args.append(self.define("CMAKE_MODULE_LINKER_FLAGS", f"-L{stub} -Wl,-rpath-link,{stub}"))
                    break

        return args

    def setup_build_environment(self, env):
        print(self.spec.version)
        if (
            self.spec.satisfies("@latest")
            or self.spec.satisfies("@master")
            or int(str(self.spec.version.joined)) >= 52
        ):
            env.set("OPENBLAS_NUM_THREADS", "1")

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
