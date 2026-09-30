from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyCliUi(PythonPackage):
    """cli-ui: build nice user interfaces in the terminal."""

    homepage = "https://github.com/your-tools/python-cli-ui"
    pypi = "cli-ui/cli_ui-0.19.0.tar.gz"

    license("BSD-3-Clause")

    version(
        "0.19.0",
        sha256="59cdab0c6a2a6703c61b31cb75a1943076888907f015fffe15c5a8eb41a933aa",
    )

    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-poetry-core@1.0.0:", type="build")

    depends_on("py-colorama@0.4.1:0.4", type=("build", "run"))
    depends_on("py-tabulate@0.9", type=("build", "run"))
    depends_on("py-unidecode@1.3.6:1", type=("build", "run"))

    import_modules = ["cli_ui"]
