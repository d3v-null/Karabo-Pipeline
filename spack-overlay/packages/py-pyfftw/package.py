from spack.package import *
from spack_repo.builtin.build_systems.python import PythonPackage

class PyPyfftw(PythonPackage):
    """A pythonic wrapper around FFTW, the FFT library, presenting a unified
    interface for all the supported transforms."""

    homepage = "https://github.com/pyFFTW/pyFFTW"
    pypi = "pyFFTW/pyFFTW-0.13.1.tar.gz"

    version("0.13.1", sha256="09155e90a0c6d0c1f2d1f3668180a7de95fb9f83fef5137a112fb05978e87320")

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    # pyFFTW 0.13.1 is incompatible with Cython 3.0+, constrain to 0.29.x
    depends_on("py-cython@:0.29", type="build")
    depends_on("py-numpy", type=("build", "run"))
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





