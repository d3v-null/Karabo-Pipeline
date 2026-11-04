from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyAstroquery(PythonPackage):
    """Functions and classes to access online astronomical data resources
    (needed by facetselfcal)."""

    homepage = "https://astroquery.readthedocs.io"
    pypi = "astroquery/astroquery-0.4.11.tar.gz"

    license("BSD-3-Clause")

    version("0.4.11", sha256="5537529bddc7fa07e773d5cd9baca593e3f5d93474edd1914f68e89506042b33")

    depends_on("python@3.9:", type=("build", "run"))
    # 0.4.11's setup.py runs the bundled astropy_helpers via ah_bootstrap, which imports
    # pkg_resources (gone from setuptools 81+). :69 reuses the 69.2.0 the image already
    # builds py-bdsf and others with.
    depends_on("py-setuptools@:69", type="build")
    depends_on("py-wheel", type="build")
    depends_on("py-numpy@1.20:", type=("build", "run"))
    depends_on("py-astropy@5:", type=("build", "run"))
    depends_on("py-requests@2.19:", type=("build", "run"))
    depends_on("py-beautifulsoup4@4.8:", type=("build", "run"))
    depends_on("py-html5lib@0.999:", type=("build", "run"))
    depends_on("py-keyring@15:", type=("build", "run"))
    depends_on("py-pyvo@1.5:", type=("build", "run"))
