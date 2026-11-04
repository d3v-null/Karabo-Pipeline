from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyBreizorro(PythonPackage):
    """Image masking tool; facetselfcal runs the `breizorro` command to make
    clean masks and refuses to start without it."""

    homepage = "https://github.com/ratt-ru/breizorro"
    pypi = "breizorro/breizorro-0.2.0.tar.gz"

    license("GPL-3.0-only")

    version("0.2.0", sha256="f5c86eaa52517e2cd2c77a216fcca3c52f813fcea269e6614c03635bc936707c")

    depends_on("python@3.9:3.12", type=("build", "run"))
    depends_on("py-poetry-core", type="build")
    depends_on("py-setuptools", type="build")

    depends_on("py-astropy", type="run")
    depends_on("py-click", type="run")
    depends_on("py-numpy", type="run")
    depends_on("py-omegaconf", type="run")
    depends_on("py-photutils", type="run")
    depends_on("py-regions@0.8:", type="run")
    depends_on("py-scikit-image", type="run")
    depends_on("py-scipy@1.13.1:", type="run")
    # provides scabha (clickify_parameters for the CLI)
    depends_on("py-stimela@2.0.2:", type="run")
    # bokeh is only used by --gui; not installed
