from spack.package import *
import os


class Hyperdrive(Package):
    """Calibration software for the Murchison Widefield Array (MWA) radio telescope.

    hyperdrive is a Rust library and command-line tool for calibrating MWA data.
    """

    homepage = "https://mwatelescope.github.io/mwa_hyperdrive/"
    url = "https://github.com/MWATelescope/mwa_hyperdrive/archive/refs/tags/v0.3.0.tar.gz"
    git = "https://github.com/MWATelescope/mwa_hyperdrive.git"

    maintainers("d3v-null")

    license("MPL-2.0")

    # Versions
    version("main", branch="main")
    version("0.6.1", tag="v0.6.1")

    # Variants
    variant("cuda", default=False, description="Enable CUDA support for GPU acceleration")
    variant("hip", default=False, description="Enable HIP support for AMD GPU acceleration")

    # Build dependencies
    depends_on("rust@1.64:", type="build")
    depends_on("pkgconfig", type="build")

    # Fontconfig and its dependencies for yeslogic-fontconfig-sys
    depends_on("fontconfig")
    depends_on("freetype")
    depends_on("libxml2")
    depends_on("util-linux-uuid", type="build")

    # Core dependencies
    depends_on("cfitsio", type=("build", "link", "run"))
    depends_on("hdf5", type=("build", "link", "run"))
    # hdf5~mpi is likely preferred if mpi is not supported/needed, matching hyperbeam
    depends_on("hdf5~mpi", type=("build", "link", "run"))

    # GPU dependencies
    depends_on("cuda@11.0:", when="+cuda", type=("build", "link", "run"))
    depends_on("hip@4.0:", when="+hip", type=("build", "link", "run"))

    # Conflicts
    conflicts("+cuda", when="+hip", msg="CUDA and HIP cannot be enabled simultaneously")

    def setup_run_environment(self, env):
        """Set up runtime environment."""
        # Ensure shared libraries can be found
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib)
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib64)

        # Add executables to PATH
        env.prepend_path("PATH", self.prefix.bin)

    def setup_build_environment(self, env):
        """Set up build environment for Rust compilation."""
        # Set CFITSIO paths
        env.set("CFITSIO_LIB", self.spec["cfitsio"].prefix.lib)
        env.set("CFITSIO_INC", self.spec["cfitsio"].prefix.include)

        # Set HDF5 paths
        env.set("HDF5_DIR", self.spec["hdf5"].prefix)
        env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec["hdf5"].prefix, "lib", "pkgconfig"))

        # Ensure fontconfig and dependencies are in PKG_CONFIG_PATH
        for dep in ["fontconfig", "freetype", "libxml2", "util-linux-uuid"]:
            if dep in self.spec:
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "lib", "pkgconfig"))
                # Some packages might put .pc files in lib64 or share
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "lib64", "pkgconfig"))
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "share", "pkgconfig"))

        # CUDA support
        if "+cuda" in self.spec:
            env.set("CUDA_LIB", self.spec["cuda"].prefix.lib)
            env.set("CUDA_LIB64", self.spec["cuda"].prefix.lib64)
            # Set compute capability (can be overridden by user)
            if not os.environ.get("HYPERDRIVE_CUDA_COMPUTE"):
                env.set("HYPERDRIVE_CUDA_COMPUTE", "75")  # Default to RTX 2070/3060 Ti

        # HIP support
        if "+hip" in self.spec:
            env.set("HIP_PATH", self.spec["hip"].prefix)

        # Fix for ARM64 proc-macro compilation issue
        env.unset("CARGO_BUILD_TARGET")
        env.unset("CARGO_TARGET_DIR")
        env.unset("CARGO_BUILD_TARGET_DIR")

        # Use release profile for optimization
        env.set("CARGO_PROFILE_RELEASE_OPT_LEVEL", "3")
        env.set("CARGO_PROFILE_RELEASE_LTO", "thin")

    def install(self, spec, prefix):
        """Install hyperdrive using cargo."""
        cargo = which("cargo")

        # Build Rust features list
        features = []

        if "+cuda" in spec:
            features.append("cuda")

        if "+hip" in spec:
            features.append("hip")

        # Install the Rust binary
        install_args = ["install", "--path", ".", "--locked", "--root", prefix]

        if features:
            install_args.extend(["--features", ",".join(features)])

        # Ensure we're building for the native target
        cargo(*install_args)

