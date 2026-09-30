from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyUritools(PythonPackage):
    """uritools: RFC 3986 compliant URI parsing, classification and
    composition."""

    homepage = "https://github.com/tkem/uritools"
    pypi = "uritools/uritools-5.0.0.tar.gz"

    license("MIT")

    version(
        "5.0.0",
        sha256="68180cad154062bd5b5d9ffcdd464f8de6934414b25462ae807b00b8df9345de",
    )

    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-setuptools@46.4.0:", type="build")
    depends_on("py-wheel", type="build")

    import_modules = ["uritools"]
