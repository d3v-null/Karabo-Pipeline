from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


# Karabo overlay of builtin's recipe: install the pure-python wheel instead of
# the sdist, whose build regenerates the ANTLR grammar and so needs java.
class PyOmegaconf(PythonPackage):
    """A hierarchical configuration system, with support for merging
    configurations from multiple sources."""

    homepage = "https://github.com/omry/omegaconf"
    url = "https://files.pythonhosted.org/packages/py3/o/omegaconf/omegaconf-2.3.0-py3-none-any.whl"

    license("BSD-3-Clause")

    version("2.3.0", sha256="7b4df175cdb08ba400f45cae3bdcae7ba8365db4d165fc65fd04b050ab63b46b")

    depends_on("python@3.6:", type=("build", "run"))
    depends_on("py-antlr4-python3-runtime@4.9", type=("build", "run"))
    depends_on("py-pyyaml@5.1:", type=("build", "run"))
