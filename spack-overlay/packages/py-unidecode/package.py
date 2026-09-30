from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyUnidecode(PythonPackage):
    """ASCII transliterations of Unicode text.

    Overlay copy: builtin Spack only knows 1.1.1, cli-ui needs >=1.3.6.
    """

    homepage = "https://github.com/avian2/unidecode"
    pypi = "Unidecode/Unidecode-1.3.8.tar.gz"

    license("GPL-2.0-or-later")

    version(
        "1.3.8",
        sha256="cfdb349d46ed3873ece4586b96aa75258726e2fa8ec21d6f00a591d98806c2f4",
    )
    version(
        "1.1.1",
        sha256="2b6aab710c2a1647e928e36d69c21e76b453cd455f4e2621000e54b2a9b8cce8",
    )

    depends_on("python@3.5:", type=("build", "run"), when="@1.3:")
    depends_on("python@2.7:2.8,3.4:", type=("build", "run"))
    depends_on("py-setuptools", type="build")

    import_modules = ["unidecode"]
