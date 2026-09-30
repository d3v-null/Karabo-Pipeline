from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyAstroKittens(PythonPackage):
    """Kittens: utility library (config, parsing, logging helpers) used by
    Tigger and MeqTrees."""

    homepage = "https://github.com/ska-sa/kittens"
    pypi = "astro-kittens/astro-kittens-1.4.6.tar.gz"

    license("GPL-2.0-or-later")

    version(
        "1.4.6",
        sha256="7dd70eff93dc2a24156d04371b99b3542048d4555172f1eb6d9c9ffe76b48bac",
    )

    depends_on("python@3:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-configparser", type=("build", "run"))
    depends_on("py-astropy", type=("build", "run"))

    import_modules = ["Kittens"]
