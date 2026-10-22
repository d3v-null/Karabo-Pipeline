from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import depends_on, join_path, patch, variant, version, which


class Everybeam(CMakePackage):
    """The EveryBeam library is a library that provides the antenna response
    pattern for several instruments, such as LOFAR (and LOBES), SKA (OSKAR),
    MWA, JVLA, etc."""

    homepage = "https://git.astron.nl/RD/EveryBeam"
    git = "https://git.astron.nl/RD/EveryBeam.git"

    version("0.1.1", tag="v0.1.1", submodules=True)
    version("0.1.2", tag="v0.1.2", submodules=True)
    version("0.1.3", tag="v0.1.3", submodules=True)
    version("0.2.0", tag="v0.2.0", submodules=True)
    version("0.3.0", tag="v0.3.0", submodules=True)
    version("0.3.1", tag="v0.3.1", submodules=True)
    version("0.4.0", tag="v0.4.0", submodules=True)
    version("0.5.1", tag="v0.5.1", submodules=True)
    version("0.5.2", tag="v0.5.2", submodules=True)
    version("0.5.3", tag="v0.5.3", submodules=True)
    version("0.5.4", tag="v0.5.4", submodules=True)
    version("0.5.5", tag="v0.5.5", submodules=True)
    version("0.6.0", tag="v0.6.0", submodules=True)
    version("0.6.1", tag="v0.6.1", submodules=True)
    version("0.7.0", tag="v0.7.0", submodules=True)
    version("0.7.1", tag="v0.7.1", submodules=True)
    version("0.7.2", tag="v0.7.2", submodules=True)
    version("0.7.3", tag="v0.7.3", submodules=True)
    version(
        "0.7.4",
        tag="v0.7.4",
        commit="1ee7cb5fd59d22015408dc0fcd50ccdfe36390be",
        submodules=True,
    )
    version("0.8.0", tag="v0.8.0", submodules=True)
    version(
        "0.8.0.20260213",
        commit="87ba7abcb291330936bed596631d537a6d643aaf",
        submodules=True,
        deprecated=True,  # Use 0.8.2 instead, which is functionally equivalent.
    )
    version(
        "0.8.2",
        tag="v0.8.2",
        commit="09e43d7f44e44e5b9a16822fa4387fc790e477d9",
        submodules=True,
    )
    version(
        "0.8.3",
        tag="v0.8.3",
        commit="bc4116ee9609c7a1c81c7f6e3d8f08f2a38ad949",
        submodules=True,
    )
    version(
        "0.8.3.20260810",
        commit="32fe4d17f4a070f434ef1075edb983d251a627c2",
        submodules=True,
    )
    version(
        "0.8.4",
        commit="99c542508c8f3c802b9297720db001728b0d328b",
        submodules=True,
    )
    version(
        "0.8.5.20260909",
        commit="c6a7406883bb923193fd2b80f85183f27db079d6",
        submodules=True,
    )
    version(
        "0.9.0",
        tag="v0.9.0",
        commit="61c3dfee36a38cfd1214288bb265b563cb8a1092",
        submodules=True,
    )
    version("master", branch="master", submodules=True, no_cache=True)

    variant("python", default=True, description="Enable Python support")

    # Karabo overlay of ska-sdp-spack's recipe; only the patches below differ.
    # Dp3 predict calls one MWA point response from all threads: share the tile
    # beam across time steps, cache modes per frequency, and evaluate the beam
    # outside the casacore lock (else ~1.5 cores busy, races on lazy init).
    patch("mwa-beam-thread-scaling.patch", when="@0.9.0")
    # Python dependency checkers (pip check) need dist-info for the extension.
    patch("install-python-metadata.patch", when="@0.9.0 +python")

    # The bundled ska-sdp-func library requires a C compiler.
    depends_on("c", type="build")
    depends_on("cxx", type="build")

    depends_on("hdf5+cxx")
    depends_on("casacore+data")
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

    test_requires_compiler = True

    def test_load_invalid_name(self):
        """Test an application that uses the Load() function."""
        source = join_path(
            self.test_suite.current_test_data_dir, "test_invalid_name.cpp"
        )
        # include/ contains dummy aocommon headers, which are required for
        # compiling the test. Normally, these headers are available via the
        # application that uses EveryBeam (DP3 or WSClean).
        include = join_path(self.test_suite.current_test_data_dir, "include")
        exe = "test_invalid_name"
        cxx = which(self.compiler.cxx)
        # Use the same compiler flags as used for building EveryBeam.
        # Otherwise checkavx.h may report an incompatibility error.
        flags = self.spec.target.optimization_flags(
            self.compiler.name, str(self.compiler.version)
        ).split(" ")
        cxx(
            source,
            "-o",
            exe,
            *flags,
            f"-I{include}",
            f"-I{self.prefix.include}",
            f"-L{self.prefix.lib}",
            f"-L{self.prefix.lib64}",
            f"-Wl,-rpath,{self.prefix.lib}",
            f"-Wl,-rpath,{self.prefix.lib64}",
            f"-I{self.spec['boost'].prefix.include}",
            f"-I{self.spec['casacore'].prefix.include}",
            f"-L{self.spec['casacore'].prefix.lib}",
            f"-L{self.spec['casacore'].prefix.lib64}",
            f"-Wl,-rpath,{self.spec['casacore'].prefix.lib}",
            f"-Wl,-rpath,{self.spec['casacore'].prefix.lib64}",
            "-lcasa_casa",
            "-lcasa_ms",
            "-lcasa_tables",
            "-leverybeam",
        )
        which(exe)()

    def test_python_import(self):
        """Ensure the python module can be imported."""
        if "+python" in self.spec:
            python = self.module.python
            python("-c", "import everybeam; print(everybeam.Options())")
