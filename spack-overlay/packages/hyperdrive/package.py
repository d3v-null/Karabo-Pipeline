from spack.package import *
import os
import spack.llnl.util.filesystem as fs
import shutil


class Hyperdrive(Package, ROCmPackage, CudaPackage):
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
    # version("0.7.0", tag="v0.7.0")
    version("0.7.0.bmetrics", commit="b4338cc3f4f0dadbe4baae88cff4a48278eec970")

    # Variants
    variant("cuda", default=False, description="Enable CUDA support for GPU acceleration")
    variant("hip", default=False, description="Enable HIP support for AMD GPU acceleration")
    variant("bmetrics", default=False, description="Enable bmetrics subcommand")

    # Build dependencies
    depends_on("rust@1.64:", type="build")
    depends_on("pkgconfig", type="build")

    # Fontconfig and its dependencies for yeslogic-fontconfig-sys
    depends_on("fontconfig")
    depends_on("freetype")
    depends_on("libxml2")
    depends_on("util-linux-uuid", type="build")

    # Core dependencies
    # cfitsio > 4 has breaking API changes, use cfitsio-reentrant for 3.x
    depends_on("cfitsio-reentrant+shared", type=("build", "link", "run"))
    depends_on("hdf5", type=("build", "link", "run"))
    # hdf5~mpi is likely preferred if mpi is not supported/needed, matching hyperbeam
    depends_on("hdf5~mpi", type=("build", "link", "run"))

    # GPU dependencies
    depends_on("cuda@11.0:", when="+cuda", type=("build", "link", "run"))
    depends_on("hip@4.0:", when="+hip", type=("build", "link", "run"))

    # aoflagger is needed for bmetrics in v0.7.0-devel
    # Note: when="@0.7.0-devel" doesn't match due to Spack version parsing quirks
    depends_on("aoflagger@3.4.0:~gui~ipo", type=("build", "link", "run"), when="+bmetrics")

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
        build_dir = self.stage.source_path
        env.set("CARGO_HOME", f"{build_dir}/.cargo")

        # Set CFITSIO paths
        env.set("CFITSIO_LIB", self.spec["cfitsio-reentrant"].prefix.lib)
        env.set("CFITSIO_INC", self.spec["cfitsio-reentrant"].prefix.include)

        # Set HDF5 paths
        env.set("HDF5_DIR", self.spec["hdf5"].prefix)
        env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec["hdf5"].prefix, "lib", "pkgconfig"))

        # Set aoflagger paths (needed for v0.7.0-devel)
        if "aoflagger" in self.spec:
            aoflagger_spec = self.spec["aoflagger"]
            inc = join_path(aoflagger_spec.prefix, "include")
            lib = join_path(aoflagger_spec.prefix, "lib")

            # Set include paths for C/C++ compilers (cc crate uses these)
            env.prepend_path("C_INCLUDE_PATH", inc)
            env.prepend_path("CPLUS_INCLUDE_PATH", inc)
            env.prepend_path("CPATH", inc)

            # Also set CXXFLAGS for direct compiler invocations
            # Use append_flags to ensure we don't overwrite existing flags
            env.append_flags("CXXFLAGS", f"-I{inc}")
            env.append_flags("CFLAGS", f"-I{inc}")

            env.prepend_path("LIBRARY_PATH", lib)
            env.prepend_path("LD_LIBRARY_PATH", lib)

            env.prepend_path("PKG_CONFIG_PATH", join_path(aoflagger_spec.prefix, "lib", "pkgconfig"))
            env.prepend_path("PKG_CONFIG_PATH", join_path(aoflagger_spec.prefix, "lib64", "pkgconfig"))

        # Ensure fontconfig and dependencies are in PKG_CONFIG_PATH
        for dep in ["fontconfig", "freetype", "libxml2", "util-linux-uuid"]:
            if dep in self.spec:
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "lib", "pkgconfig"))
                # Some packages might put .pc files in lib64 or share
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "lib64", "pkgconfig"))
                env.prepend_path("PKG_CONFIG_PATH", join_path(self.spec[dep].prefix, "share", "pkgconfig"))

        # HIP support
        if self.spec.satisfies("+hip"):
            hip_spec = self.spec["hip"]
            hip_dir = hip_spec.prefix
            env.set("HIP_PATH", hip_dir)
            # Set HIP architecture if available (ROCmPackage provides amdgpu_target)
            if "amdgpu_target" in self.spec.variants:
                amdgpu_target = ",".join(self.spec.variants["amdgpu_target"].value)
                env.set("HYPERDRIVE_HIP_ARCH", amdgpu_target)
                env.set("HYPERBEAM_HIP_ARCH", amdgpu_target)  # Also set for hyperbeam dependency
            # ROCm 6+ uses different paths
            if hip_spec.satisfies("@6:"):
                env.set("HIP_PATH", hip_dir)
            else:
                env.set("ROCM_PATH", hip_dir)

        # CUDA support
        if self.spec.satisfies("+cuda"):
            # Default to compute capability 86 (RTX 3090/4090) if not specified or none
            cuda_arch = "86"
            try:
                if "cuda_arch" in self.spec.variants:
                    arch_values = self.spec.variants["cuda_arch"].value
                    # Filter out 'none' values and ensure each arch is a two-digit string
                    valid_archs = []
                    for arch in arch_values:
                        arch_str = str(arch).strip()
                        if arch_str != "none" and arch_str.isdigit():
                            # Ensure it's exactly 2 digits (pad with 0 if needed, though unlikely)
                            if len(arch_str) == 2:
                                valid_archs.append(arch_str)
                            elif len(arch_str) == 1:
                                valid_archs.append(f"0{arch_str}")
                    if valid_archs:
                        cuda_arch = ",".join(valid_archs)
            except Exception as e:
                # If there's any issue accessing cuda_arch, use default
                pass
            env.set("HYPERDRIVE_CUDA_COMPUTE", cuda_arch)
            env.set("HYPERBEAM_CUDA_COMPUTE", cuda_arch)  # Also set for hyperbeam dependency
            cuda_dir = self.spec["cuda"].prefix
            env.set("CUDA_LIB", cuda_dir + "/lib")
            env.set("CUDA_LIB64", cuda_dir + "/lib64")

        # Fix for ARM64 proc-macro compilation issue
        env.unset("CARGO_BUILD_TARGET")
        env.unset("CARGO_TARGET_DIR")
        env.unset("CARGO_BUILD_TARGET_DIR")

        # Use release profile for optimization
        env.set("CARGO_PROFILE_RELEASE_OPT_LEVEL", "3")
        env.set("CARGO_PROFILE_RELEASE_LTO", "thin")

    def get_features(self):
        """Get list of Cargo features based on active variants."""
        features = []
        if self.spec.satisfies("+hip"):
            features.append("hip")
        if self.spec.satisfies("+cuda"):
            features.append("cuda")
        if self.spec.satisfies("+bmetrics"):
            features.append("bmetrics")
        return features

    def install(self, spec, prefix):
        """Install hyperdrive using cargo."""
        import os
        import subprocess
        import llnl.util.tty as tty

        with fs.working_dir(self.stage.source_path):
            # Find aoflagger prefix -- it may not be a direct Spack dep of
            # hyperdrive (depends_on when= matching is fragile for -devel
            # versions), but it IS installed because dp3 depends on it.
            aoflagger_inc = None
            aoflagger_lib = None

            # 1. Try the Spack spec first (if depends_on resolved)
            if "aoflagger" in spec:
                aoflagger_inc = join_path(spec["aoflagger"].prefix, "include")
                aoflagger_lib = join_path(spec["aoflagger"].prefix, "lib")
                tty.info(f"aoflagger from spec: inc={aoflagger_inc}")

            # 2. Fallback: ask spack for an installed aoflagger
            if aoflagger_inc is None:
                try:
                    result = subprocess.run(
                        ["spack", "location", "-i", "aoflagger"],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        af_prefix = result.stdout.strip()
                        aoflagger_inc = os.path.join(af_prefix, "include")
                        aoflagger_lib = os.path.join(af_prefix, "lib")
                        tty.info(f"aoflagger from spack location: inc={aoflagger_inc}")
                except Exception as e:
                    tty.warn(f"spack location failed: {e}")

            # 3. Write .cargo/config.toml [env] section so that the cc crate
            #    (used by aoflagger_sys build.rs) picks up the include path.
            if aoflagger_inc and os.path.isdir(aoflagger_inc):
                tty.info(f"Injecting aoflagger paths into .cargo/config.toml")
                cargo_dir = os.path.join(self.stage.source_path, ".cargo")
                os.makedirs(cargo_dir, exist_ok=True)
                cfg = os.path.join(cargo_dir, "config.toml")

                existing = ""
                if os.path.exists(cfg):
                    with open(cfg, "r") as fh:
                        existing = fh.read()

                with open(cfg, "w") as fh:
                    fh.write(existing)
                    fh.write("\n# -- injected by spack hyperdrive package --\n")
                    fh.write("[net]\n")
                    fh.write("git-fetch-with-cli = true\n\n")
                    fh.write("[env]\n")
                    fh.write(f'CXXFLAGS = {{ value = "-I{aoflagger_inc}", force = true }}\n')
                    fh.write(f'CFLAGS = {{ value = "-I{aoflagger_inc}", force = true }}\n')
                    fh.write(f'C_INCLUDE_PATH = {{ value = "{aoflagger_inc}", force = true }}\n')
                    fh.write(f'CPLUS_INCLUDE_PATH = {{ value = "{aoflagger_inc}", force = true }}\n')
                    if aoflagger_lib:
                        fh.write(f'LIBRARY_PATH = {{ value = "{aoflagger_lib}", force = true }}\n')

                tty.info(f"Wrote cargo env config to {cfg}")
            else:
                tty.warn("aoflagger include dir not found - build may fail")
                # Still write [net] section for git-fetch-with-cli
                cargo_dir = os.path.join(self.stage.source_path, ".cargo")
                os.makedirs(cargo_dir, exist_ok=True)
                cfg = os.path.join(cargo_dir, "config.toml")
                existing = ""
                if os.path.exists(cfg):
                    with open(cfg, "r") as fh:
                        existing = fh.read()
                if "[net]" not in existing:
                    with open(cfg, "a") as fh:
                        fh.write("\n[net]\ngit-fetch-with-cli = true\n")

            # Build
            cargo_exe = which("cargo").path
            features = self.get_features()
            build_args = [cargo_exe, "build", "--locked", "--release"]
            if features:
                build_args.extend(["--features", ",".join(features)])

            tty.info(f"Running: {' '.join(build_args)}")
            subprocess.check_call(build_args)

            # Install
            install_dir = prefix.bin
            os.makedirs(install_dir, exist_ok=True)
            shutil.copy2(
                "target/release/hyperdrive",
                join_path(install_dir, "hyperdrive"),
            )
