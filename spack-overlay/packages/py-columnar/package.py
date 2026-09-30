from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyColumnar(PythonPackage):
    """A tool for printing data in a columnar format."""

    homepage = "https://github.com/MaxTaggart/columnar"
    pypi = "Columnar/Columnar-1.4.1.tar.gz"

    license("MIT")

    version(
        "1.4.1",
        sha256="c3cb57273333b2ff9cfaafc86f09307419330c97faa88dcfe23df05e6fbb9c72",
    )

    depends_on("python@3:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-toolz", type=("build", "run"))
    depends_on("py-wcwidth", type=("build", "run"))

    import_modules = ["columnar"]
