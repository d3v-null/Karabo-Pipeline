import os

from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import depends_on, join_path, variant, version, which


# Karabo overlay of ska-sdp-spack's recipe: +cuda builds against Spack's CUDA
# (driver stubs, no GPU needed) and ~mpi ignores MPI outside Spack.
class Wsclean(CMakePackage):
    """WSClean (w-stacking clean) is a fast generic widefield imager. It
    implements several gridding algorithms and offers fully-automated
    multi-scale multi-frequency deconvolution."""

    homepage = "https://wsclean.readthedocs.io/"
    git = "https://gitlab.com/aroffringa/wsclean.git"

    version("3.0", tag="v3.0", submodules=True)
    version("3.0.1", tag="v3.0.1", submodules=True)
    version("3.1", tag="v3.1", submodules=True)
    version("3.2", tag="v3.2", submodules=True)
    version("3.3", tag="v3.3", submodules=True)
    version("3.4", tag="v3.4", submodules=True)
    version("3.5", tag="v3.5", submodules=True)
    version(  # master branch at 2025-01-27
        "3.5.20250127",
        commit="d7d89fddf472ffac05a2fa1820ec7d0027da38ee",
        submodules=True,
    )
    version("3.6", tag="v3.6", submodules=True)
    version(  # master branch at 2025-06-30
        "3.6.20250630",
        commit="012778d4b9ca9a5e46815f7aae95f3f469539f99",
        submodules=True,
    )
    version(  # master branch at 2026-01-09
        "3.6.20260109",
        commit="f3071fa68c052ec452c0c6ad0ec66a16e980daad",
        submodules=True,
    )
    version(  # master branch at 2026-03-18
        "3.7.20260318",
        commit="2b1a430ca1666677f9bb6f4e997134a75465e852",
        submodules=True,
    )
    version(  # master branch at 2026-04-20
        "3.7.20260420",
        commit="3d4bc86bd501444e15f1019ce9cc3248171937e3",
        submodules=True,
    )
    version(  # master branch at 2026-04-24
        "3.7.20260424",
        commit="c5314d942913d1502e2518b675c5605f234cdb75",
        submodules=True,
        preferred=True,
    )
    version(  # master branch at 2026-08-04
        "3.7.20260804",
        commit="5706883aac7ae6859045c72c584efb6d6880a590",
        submodules=True,
    )
    version(  # master branch at 2026-09-29
        "3.7.20260929",
        commit="d395485f72e91958cf8e029ec10000d8087637bf",
        submodules=True,
    )
    version(
        "master",
        branch="master",
        submodules=True,
        no_cache=True,
    )

    variant("python", default=False, description="Enable Python support")
    variant("cuda", default=False, description="Enable CUDA support")
    # The 'mpi' flag forces using an MPI implementation from Spack, by adding
    # a dependency on it. When the flag is off, WSClean will still build
    # wsclean-mp if there's an MPI implementation outside the Spack tree.
    variant("mpi", default=True, description="Use MPI from Spack")

    depends_on("c", type="build", when="@:3.6.0")
    depends_on("cxx", type="build")

    # Linking WSClean against HDF5 fails if HDF5 was built with MPI support.
    depends_on("hdf5+cxx+threadsafe~mpi")
    depends_on("fftw")
    depends_on("casacore+data", when="@:3.5")
    depends_on("casacore@3.6:+data", when="@3.6:")
    depends_on("everybeam@0.2.0", when="@3.0")
    depends_on("everybeam@0.3.0", when="@3.0.1")
    depends_on("everybeam@0.3.0", when="@3.1")
    depends_on("everybeam@0.4.0", when="@3.2")
    depends_on("everybeam@0.5.1", when="@3.3")
    depends_on("everybeam@0.5.3", when="@3.4")
    depends_on("everybeam@0.7.4:0.7", when="@3.5:3.6.20250630")
    depends_on("everybeam@0.7.4:0.8", when="@3.6.20260109:3.7.20260804")
    depends_on("everybeam@0.9.0", when="@3.7.20260929")
    depends_on("everybeam@0.9:", when="@master")
    depends_on("idg@1.0.0", when="@3.1")
    depends_on("idg@1.1.0", when="@3.2")
    depends_on("idg@1.1.0", when="@3.3")
    depends_on("idg@1.2.0:", when="@3.4:")
    depends_on("idg+cuda", when="+cuda")
    depends_on("cuda", when="+cuda")
    depends_on("idg+python", when="+python")
    depends_on("boost+date_time+program_options")
    depends_on("openblas threads=pthreads")
    depends_on("gsl")
    depends_on("git")
    depends_on("python")
    depends_on("mpi", when="+mpi")
    depends_on("py-pybind11", when="@3.6.20260109:")

    def cmake_args(self):
        args = [
            self.define(
                "BLA_VENDOR", "OpenBLAS"
            ),  # Avoid using the system BLAS/LAPACK
            self.define("PORTABLE", True),  # let Spack determine arch build flags
        ]
        if self.spec.satisfies("+cuda"):
            for sub in ("lib64", "lib"):
                stub = join_path(self.spec["cuda"].prefix, sub, "stubs")
                if os.path.isdir(stub):
                    flags = f"-L{stub} -Wl,-rpath-link,{stub}"
                    args.append(self.define("CMAKE_EXE_LINKER_FLAGS", flags))
                    args.append(self.define("CMAKE_SHARED_LINKER_FLAGS", flags))
                    break
        if self.spec.satisfies("~mpi"):
            # Without this, CMake picks up a stale system MPI.
            args.append(self.define("CMAKE_DISABLE_FIND_PACKAGE_MPI", True))
        return args

    def setup_build_environment(self, env):
        env.set("OPENBLAS_NUM_THREADS", "1")

    def setup_run_environment(self, env):
        env.set("OPENBLAS_NUM_THREADS", "1")

    def test_executables(self):
        """Ensure the executables run."""
        chgcentre = which(self.prefix.bin.chgcentre)
        wsclean = which(self.prefix.bin.wsclean)
        chgcentre()
        wsclean("--version")
        # ~mpi disables MPI discovery, so wsclean-mp is not built.
        if self.spec.satisfies("+mpi"):
            which(getattr(self.prefix.bin, "wsclean-mp"))("--version")
