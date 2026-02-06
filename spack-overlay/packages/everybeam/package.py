# https://gitlab.com/ska-telescope/sdp/ska-sdp-spack/-/raw/5c515ba11992398717151feed33fb74ddf314f2d/packages/everybeam/package.py
# removed all available versions except 0.8.0.20251125 for MWA support

from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import depends_on, join_path, variant, version, which


class Everybeam(CMakePackage):
    """The EveryBeam library is a library that provides the antenna response
    pattern for several instruments, such as LOFAR (and LOBES), SKA (OSKAR),
    MWA, JVLA, etc."""

    homepage = "https://git.astron.nl/RD/EveryBeam"
    git = "https://git.astron.nl/RD/EveryBeam.git"
    version("0.8.0.20251125", commit="2614beafba64f5f5d326b783c486c765a3729889", submodules=True)

    variant("python", default=True, description="Enable Python support")

    # The bundled ska-sdp-func library requires a C compiler.
    depends_on("c", type="build")
    depends_on("cxx", type="build")

    depends_on("hdf5+cxx")
    depends_on("casacore@3.7.1: +data")
    depends_on("boost+filesystem+system")
    depends_on("fftw")
    depends_on("gsl", when="@0.4.0:")
    depends_on("python", when="+python")
    depends_on("cmake")
    depends_on("cmake@3.8:", when="@0.3.2:0.5.3")
    depends_on("cmake@3.15:", when="@0.5.4:")
    depends_on("git")
    depends_on("wget")

    def cmake_args(self):
        args = [
            self.define_from_variant("BUILD_WITH_PYTHON", "python"),
            self.define("PORTABLE", True),  # let Spack determine arch build flags
        ]
        return args

    def setup_run_environment(self, env):
        env.set("EVERYBEAM_DATADIR", self.prefix.share.everybeam)

        spec = self.spec
        if "+python" in spec:
            python_version = self.spec.dependencies("python")[0].version.up_to(2)
            env.prepend_path(
                "PYTHONPATH",
                join_path(
                    self.prefix.lib, f"python{python_version}", "site-packages"
                ),
            )

    def test_python_import(self):
        """Ensure the python module can be imported."""
        if "+python" in self.spec:
            python = self.module.python
            python("-c", "import everybeam; print(everybeam.Options())")
