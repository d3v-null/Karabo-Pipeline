from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyAstlib(PythonPackage):
    """astLib: python astronomy modules (coordinates, WCS via bundled
    WCSTools, plotting, SED handling)."""

    homepage = "https://astlib.readthedocs.io"
    pypi = "astLib/astLib-0.11.10.tar.gz"

    license("LGPL-2.0-or-later")

    version(
        "0.11.10",
        sha256="c7a7edf73202e35a07d363cd60fa1ee77faef9f605f29b69e91b1654138ba72e",
    )

    depends_on("c", type="build")
    depends_on("python@3.6:", type=("build", "run"))
    # setup.py imports pkg_resources and setuptools._distutils
    depends_on("py-setuptools", type="build")
    depends_on("py-wheel", type="build")

    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))
    depends_on("py-astropy", type=("build", "run"))
    depends_on("py-matplotlib", type=("build", "run"))

    import_modules = ["astLib", "PyWCSTools"]
