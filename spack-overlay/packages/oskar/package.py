from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage

from spack.package import (
    conflicts,
    depends_on,
    license,
    maintainers,
    variant,
    version,
)


# Karabo overlay of ska-sdp-spack's recipe; adds the openmp variant.
class Oskar(CMakePackage, CudaPackage):
    """
    OSKAR: A GPU-accelerated simulator for the Square Kilometre Array

    OSKAR has been designed primarily to produce simulated data from
    telescopes that use aperture arrays, as envisaged for the SKA.

    This spack package currently does not support OpenCL builds.
    """

    homepage = "https://github.com/OxfordSKA/OSKAR"
    git = "https://github.com/OxfordSKA/OSKAR.git"
    url = "https://github.com/OxfordSKA/OSKAR/archive/refs/tags/2.11.1.tar.gz"

    maintainers("maneesh.sutar", "vmorello")

    license("BSD 3-Clause")

    version("master", branch="master")
    # Fixes segfault due to incorrect memory alignment issues when building
    # for target >= x86_64_v3
    version(
        "2.12.0.20260212",
        commit="29707fe07ba425b426876df3872e256ffb1d4b6c",
    )

    variant("qt", default=False, description="Build GUI with Qt5")
    variant("hdf5", default=False, description="Enable HDF5 file support")
    # Karabo images build ~openmp (OSKAR otherwise picks up OpenMP silently).
    variant("openmp", default=True, description="Enable OpenMP support")

    # See cuda_arch_values in CudaPackage class
    # for list of supported cuda architectures
    conflicts("cuda_arch=none", when="+cuda", msg="CUDA architecture is required")

    depends_on("cmake@3.18:", type="build")
    depends_on("cuda@7.0:12", when="+cuda")
    depends_on("casacore@2.0:")
    depends_on("qt@5:", when="+qt")
    depends_on("hdf5@1.10:", when="+hdf5")
    depends_on("qt@5:", when="+qt")

    depends_on("c", type="build")
    depends_on("cxx", type="build")

    def cmake_args(self):
        spec = self.spec
        args = []

        args.append(self.define_from_variant("FIND_CUDA", "cuda"))
        if spec.satisfies("~openmp"):
            args.append(self.define("CMAKE_DISABLE_FIND_PACKAGE_OpenMP", True))

        # CUDA architecture handling
        if spec.satisfies("+cuda"):
            archs = spec.variants["cuda_arch"].value
            arch_with_decimals = self.compute_capabilities(archs)
            args.append(self.define("CUDA_ARCH", arch_with_decimals))

        if spec.satisfies("+casacore"):
            args.append(
                self.define("CASACORE_INC_DIR", spec["casacore"].prefix.include)
            )
            args.append(
                self.define("CASACORE_LIB_DIR", spec["casacore"].prefix.lib)
            )

        return args
