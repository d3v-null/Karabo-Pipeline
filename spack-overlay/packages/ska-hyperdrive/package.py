import os
import shutil

import spack.llnl.util.filesystem as fs
from spack.package import *


class SkaHyperdrive(Package, CudaPackage):
    """Calibration software for the MWA, from Alec Thomson's fork, which adds
    SKA-Low (and other) beams through EveryBeam.

    Separate from the hyperdrive package (upstream MWATelescope/mwa_hyperdrive):
    this one tracks https://github.com/AlecThomson/mwa_hyperdrive.
    """

    homepage = "https://github.com/AlecThomson/mwa_hyperdrive"
    git = "https://github.com/AlecThomson/mwa_hyperdrive.git"

    maintainers("d3v-null")

    license("MPL-2.0")

    version("main", branch="main")
    # main at 2026-11-20: 0.11.0 + EveryBeam/SKA-Low beams.
    version("0.11.0.20261120", commit="0051b175e42b1fee8f31b3cbd997b55c52a78f85")

    # EveryBeam's installed headers include aocommon's, which it doesn't install.
    # Same commit as the fork vendors for EveryBeam 0.9.0 (crates/everybeam-sys/build.rs).
    resource(
        name="aocommon",
        git="https://gitlab.com/aroffringa/aocommon.git",
        commit="97bbc3e3b6dcd9b392271ec45d0c528a62e530ab",
        destination="",
        placement="aocommon",
        when="+everybeam",
    )

    variant("everybeam", default=True, description="Beam responses from EveryBeam (SKA-Low etc.)")
    variant("gpu-single", default=False, description="Single-precision GPU code (faster on desktop GPUs)")

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("rust@1.88:", type="build")
    depends_on("pkgconfig", type="build")
    depends_on("cmake", type="build")

    # cfitsio comes from the fitsio-src crate (cfitsio-static feature), so the
    # fitsio bindings always match the cfitsio they're built against.
    depends_on("hdf5~mpi")
    depends_on("everybeam@0.9:", when="+everybeam")
    depends_on("casacore", when="+everybeam")

    depends_on("cuda@11:", when="+cuda")

    def setup_build_environment(self, env):
        env.set("CARGO_HOME", join_path(self.stage.source_path, ".cargo"))
        env.unset("CARGO_BUILD_TARGET")
        env.unset("CARGO_TARGET_DIR")

        env.set("HDF5_DIR", self.spec["hdf5"].prefix)

        if self.spec.satisfies("+everybeam"):
            env.set("EVERYBEAM_DIR", self.spec["everybeam"].prefix)
            env.set("CASACORE_DIR", self.spec["casacore"].prefix)
            env.set("EVERYBEAM_CXXFLAGS", "-I" + join_path(self.stage.source_path, "aocommon", "include"))

        if self.spec.satisfies("+cuda"):
            archs = [a for a in self.spec.variants["cuda_arch"].value if a != "none"]
            if archs:
                env.set("HYPERDRIVE_CUDA_COMPUTE", ",".join(archs))
                env.set("HYPERBEAM_CUDA_COMPUTE", ",".join(archs))
            cuda = self.spec["cuda"].prefix
            env.set("CUDA_PATH", cuda)
            env.set("CUDA_LIB", cuda.lib64)

    def cargo_features(self):
        features = ["cfitsio-static"]
        for v in ["cuda", "everybeam", "gpu-single"]:
            if self.spec.satisfies(f"+{v}"):
                features.append(v)
        return features

    def install(self, spec, prefix):
        cargo = which("cargo")
        with fs.working_dir(self.stage.source_path):
            cargo("build", "--locked", "--release", "--features", ",".join(self.cargo_features()))
            os.makedirs(prefix.bin, exist_ok=True)
            shutil.copy2("target/release/hyperdrive", join_path(prefix.bin, "hyperdrive"))
