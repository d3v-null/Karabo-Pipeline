from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyAstroTiggerLsm(PythonPackage):
    """Python libraries and command-line tools for manipulating
    Tigger-format local sky models (LSMs)."""

    homepage = "https://github.com/ratt-ru/tigger-lsm"
    pypi = "astro-tigger-lsm/astro-tigger-lsm-1.7.3.tar.gz"

    license("GPL-2.0-or-later")

    version(
        "1.7.3",
        sha256="f1d2ec28fe21c7f0e46de6656f75f339e29b6a3567f8e73219a9e4f6d9244200",
    )

    depends_on("python@3.6:", type=("build", "run"))
    depends_on("py-setuptools", type="build")

    depends_on("py-astro-kittens", type=("build", "run"))
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))
    depends_on("py-astlib@:0.11.10", type=("build", "run"))
    depends_on("py-astropy", type=("build", "run"))
    depends_on("py-future", type=("build", "run"))
    depends_on("py-casacore", type=("build", "run"))

    import_modules = ["Tigger", "Tigger.Models"]
