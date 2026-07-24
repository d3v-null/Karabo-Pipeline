from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyPythonDateutil(PythonPackage):
    """Extensions to the standard Python datetime module."""

    homepage = "https://dateutil.readthedocs.io/"
    pypi = "python-dateutil/python-dateutil-2.8.2.tar.gz"

    license("Apache-2.0")

    version(
        "2.8.2",
        sha256="0123cacc1627ae19ddf3c27a5de5bd67ee4586fbdd6440d9748f8abb483d3e86",
    )

    patch("static-version.patch", when="@2.8.2")

    depends_on("py-setuptools@24.3:", type="build")
    depends_on("py-six@1.5:", type=("build", "run"))
