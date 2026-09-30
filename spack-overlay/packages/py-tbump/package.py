from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyTbump(PythonPackage):
    """tbump: bump software releases (required at run time by QuartiCal)."""

    homepage = "https://github.com/your-tools/tbump"
    pypi = "tbump/tbump-6.11.0.tar.gz"

    license("BSD-3-Clause")

    version(
        "6.11.0",
        sha256="385e710eedf0a8a6ff959cf1e9f3cfd17c873617132fc0ec5f629af0c355c870",
    )

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-poetry-core@1.0.0:", type="build")

    depends_on("py-docopt@0.6.2:0.6", type=("build", "run"))
    depends_on("py-cli-ui@0.10.3:", type=("build", "run"))
    depends_on("py-schema@0.7.1:0.7", type=("build", "run"))
    depends_on("py-tomlkit@0.11", type=("build", "run"))

    import_modules = ["tbump"]
