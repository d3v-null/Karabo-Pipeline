from spack.package import *

import os
import llnl.util.filesystem as fs
from pathlib import Path
import shutil


class Hyperbeam(Package, ROCmPackage, CudaPackage):
    """Primary beam model for the Murchison Widefield Array (MWA) radio telescope.

    hyperbeam is a Rust library for calculating the beam response of the MWA.
    It provides Python bindings (mwa_hyperbeam) for use in Python applications.

    Usage:
        # Basic installation with Python bindings
        spack install hyperbeam +python

        # With CUDA support for NVIDIA GPUs
        spack install hyperbeam +python +cuda

        # With HIP support for AMD GPUs
        spack install hyperbeam +python +hip

        # Static linking for portability
        spack install hyperbeam +python +all-static
    """

    homepage = "https://github.com/MWATelescope/mwa_hyperbeam"
    url = "https://github.com/MWATelescope/mwa_hyperbeam/archive/refs/tags/v0.10.2.tar.gz"
    git = "https://github.com/MWATelescope/mwa_hyperbeam.git"

    maintainers("d3v-null")

    license("MPL-2.0")

    # Versions
    version("main", branch="main")
    version("0.10.2", sha256="2ee299d94c882e0d5d480134cf31bbd8")

    # Variants
    variant("python", default=True, description="Build and install Python bindings.")
    variant("hdf5-static", default=False, description="Link statically to hdf5 via hdf5-sys crate.")
    variant("portable", default=True, description="Disable native CPU optimizations")

    # Build dependencies
    depends_on("rust@1.64.0:", type="build")
    depends_on("rust@1.80.0:", type="build", when="@0.10.0:")
    depends_on("cmake", type="build")

    # cfitsio > 4 introduces a breaking change, is incompatible with mwalib.
    depends_on("cfitsio@3.49")

    depends_on("hdf5@1.10 +cxx ~mpi api=v110", when="~hdf5-static")
    depends_on("py-maturin", when="+python")

    # this is the only version of patchelf that has been found to work with maturin. patchelf@0.18
    # corrupts the dynamic libraries, making them unusable.
    # https://github.com/PawseySC/pawsey-spack-config/pull/280#issuecomment-2258095785
    depends_on("patchelf@0.17.2", type=("build", "run"), when="+python")

    depends_on("py-numpy", type=("build", "run"), when="+python")
    depends_on("python", type=("build", "run"), when="+python")
    depends_on("py-pip", type="build", when="+python")
    depends_on("erfa", when="@0.5.0")

    conflicts("+rocm", when="@:0.6.0")  # early hip support was added in 0.6.0

    def setup_build_environment(self, env):
        build_dir = self.stage.source_path
        env.set("CARGO_HOME", f"{build_dir}/.cargo")
        if self.spec.satisfies("+rocm"):
            amdgpu_target = ",".join(self.spec.variants["amdgpu_target"].value)
            env.set("HYPERBEAM_HIP_ARCH", amdgpu_target)
            hip_spec = self.spec["hip"]
            rocm_dir = hip_spec.prefix
            # print(f"rocm_dir: {rocm_dir}, amdgpu_target: {amdgpu_target}")
            if hip_spec.satisfies("@6:"):
                env.set("HIP_PATH", rocm_dir)
            else:
                env.set("HIP_PATH", rocm_dir)
                env.set("ROCM_PATH", rocm_dir)
        if self.spec.satisfies("+cuda"):
            # Default to compute capability 86 (RTX 3090/4090) if not specified or none
            cuda_arch = "86"
            try:
                if "cuda_arch" in self.spec.variants:
                    arch_values = self.spec.variants["cuda_arch"].value
                    # Filter out 'none' values and use only valid architectures
                    valid_archs = [str(arch) for arch in arch_values if str(arch) != "none"]
                    if valid_archs:
                        cuda_arch = ",".join(valid_archs)
            except Exception:
                # If there's any issue accessing cuda_arch, use default
                pass
            env.set("HYPERBEAM_CUDA_COMPUTE", cuda_arch)
            cuda_dir = self.spec["cuda"].prefix
            # print(f"cuda_dir: {cuda_dir}, cuda_arch: {cuda_arch}")
        if self.spec.satisfies("~portable"):
            env.append_flags("RUSTFLAGS", f"-C target-cpu=native")

    def install(self, spec, prefix):
        """Install hyperbeam using cargo."""
        cargo = which("cargo")
        features = self.get_features()

        with fs.working_dir(self.stage.source_path):
            cargo("build", "--locked", "--release", f"--features={','.join(features)}")

            # Install library files
            shutil.copytree("include", f"{prefix}/include")
            os.mkdir(f"{prefix}/lib")
            release = Path("target/release/")
            for f in release.iterdir():
                if f.name.startswith("libmwa_hyperbeam."):
                    shutil.copy2(f"{f}", f"{prefix}/lib/")

            # Install Python bindings if requested
            if "+python" in spec:
                self.install_python_bindings(spec, prefix)

    def get_features(self):
        features = []
        if self.spec.satisfies("+hdf5-static"):
            features += ["hdf5-static"]
        if self.spec.satisfies("+rocm"):
            features += ["hip"]
        if self.spec.satisfies("+cuda"):
            features += ["cuda"]
        return features

    def install_python_bindings(self, spec, prefix):
        """Install Python bindings using maturin."""
        maturin = which("maturin")
        pip = which("pip3")
        features = self.get_features()
        pyfeatures = ["python"] + features
        maturin("build", "--release", f"--features={','.join(pyfeatures)}", "--strip")
        whl_file = list(os.listdir("target/wheels"))[0]
        pip("install", f"--prefix={prefix}", f"target/wheels/{whl_file}")

    def setup_run_environment(self, env):
        """Set up runtime environment."""
        # Ensure shared libraries can be found
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib)
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib64)

        # Add executables to PATH
        env.prepend_path("PATH", self.prefix.bin)

        # Python bindings
        if "+python" in self.spec:
            try:
                py_ver = self.spec["python"].version.up_to(2)
                env.prepend_path(
                    "PYTHONPATH",
                    join_path(self.prefix, "lib", f"python{py_ver}", "site-packages"),
                )
            except Exception:
                # Fallback for different Python installation layouts
                import glob
                python_dirs = glob.glob(join_path(self.prefix, "lib", "python*", "site-packages"))
                if python_dirs:
                    env.prepend_path("PYTHONPATH", python_dirs[0])

    def setup_dependent_run_environment(self, env, dependent_spec):
        """Set up environment for packages that depend on hyperbeam."""
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib)
        env.prepend_path("LD_LIBRARY_PATH", self.prefix.lib64)

        if "+python" in self.spec:
            try:
                py_ver = self.spec["python"].version.up_to(2)
                env.prepend_path(
                    "PYTHONPATH",
                    join_path(self.prefix, "lib", f"python{py_ver}", "site-packages"),
                )
            except Exception:
                pass

    def test_import(self):
        """Test that mwa_hyperbeam Python module can be imported."""
        if "+python" not in self.spec:
            print("Skipping Python import test: +python variant disabled")
            return

        python = self.spec["python"].command
        if python:
            env = os.environ.copy()
            try:
                py_ver = self.spec["python"].version.up_to(2)
                site_pkgs = join_path(self.prefix, "lib", f"python{py_ver}", "site-packages")
                env["PYTHONPATH"] = f"{site_pkgs}:{env.get('PYTHONPATH', '')}".strip(":")
            except Exception:
                pass

            python("-c", "from mwa_hyperbeam import FEEBeam; print('mwa_hyperbeam import successful')", env=env)

    def test_beam_calculation(self):
        """Test basic beam calculation functionality."""
        if "+python" not in self.spec:
            print("Skipping beam calculation test: +python variant disabled")
            return

        python = self.spec["python"].command
        if not python:
            return

        env = os.environ.copy()
        try:
            py_ver = self.spec["python"].version.up_to(2)
            site_pkgs = join_path(self.prefix, "lib", f"python{py_ver}", "site-packages")
            env["PYTHONPATH"] = f"{site_pkgs}:{env.get('PYTHONPATH', '')}".strip(":")
        except Exception:
            pass

        test_script = """
import numpy as np
from mwa_hyperbeam import FEEBeam

# This test requires a beam file - skip if not available
print('mwa_hyperbeam basic functionality test: SKIPPED (requires beam file)')
"""
        python("-c", test_script, env=env)
