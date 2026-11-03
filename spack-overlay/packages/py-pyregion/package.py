from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyPyregion(PythonPackage):
    """Python parser for ds9 region files (needed by facetselfcal)."""

    homepage = "https://github.com/astropy/pyregion"
    pypi = "pyregion/pyregion-2.3.0.tar.gz"

    license("MIT")

    version("2.3.0", sha256="e8498711421173239689de523bb465245f5551a18a181cb4956d87f9c7464925")

    depends_on("c", type="build")
    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm@6.2:", type="build")
    depends_on("py-cython@3:3", type="build")
    depends_on("py-extension-helpers@1:1", type="build")
    # build-system requires numpy>=2,<3; runtime needs >=1.23
    depends_on("py-numpy@2:2", type=("build", "run"))
    depends_on("py-astropy@5:", type=("build", "run"))
    depends_on("py-pyparsing@2:", type=("build", "run"))
