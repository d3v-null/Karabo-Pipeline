from spack.package import *
from spack_repo.builtin.build_systems.python import PythonPackage

class PyPyfftw(PythonPackage):
    """A pythonic wrapper around FFTW, the FFT library, presenting a unified
    interface for all the supported transforms."""

    homepage = "https://github.com/pyFFTW/pyFFTW"
    pypi = "pyFFTW/pyFFTW-0.14.0.tar.gz"

    # 0.14.0 is the numpy2-targeted release: its pyproject.toml (checked
    # directly against the v0.14.0 git tag) declares
    # build-system.requires = ["Cython>=3", "numpy>=2.0.0"], with a runtime
    # dependency of numpy>=1.20 (unbounded upper — wheels built against
    # numpy 2.x headers stay ABI-compatible with numpy 1.x at runtime).
    version("0.14.0", sha256="a55f94d3da9b5c04de1bc96932a93f922910f3984557931356173a515277b65b")
    # Legacy: predates numpy2. Its own PyPI metadata caps numpy<2.0, and it
    # only builds against Cython<3.0 — kept for the numpy1/GPy rollback path.
    version("0.13.1", sha256="09155e90a0c6d0c1f2d1f3668180a7de95fb9f83fef5137a112fb05978e87320")

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-cython@:0.29", type="build", when="@0.13.1")
    depends_on("py-numpy@:1", type=("build", "run"), when="@0.13.1")
    depends_on("py-cython@3:", type="build", when="@0.14.0:")
    depends_on("py-numpy@2.0:2", type=("build", "run"), when="@0.14.0:")
    # Require float and double precision. Long double is optional and will be
    # used if available. OpenMP is also optional - setup.py will automatically
    # detect and use whatever FFTW libraries are available.
    depends_on("fftw@3.3: precision=float,double", type=("build", "link", "run"))

    def setup_build_environment(self, env):
        fftw_spec = self.spec["fftw"]

        # Set standard include and library paths for pyFFTW's setup.py
        env.set("PYFFTW_INCLUDE", fftw_spec.prefix.include)
        env.set("PYFFTW_LIB_DIR", fftw_spec.prefix.lib)

        # These environment variables guide setup.py's library detection
        env.set("include_dirs", fftw_spec.prefix.include)
        env.set("library_dirs", fftw_spec.prefix.lib)





