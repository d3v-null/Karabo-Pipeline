from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyZarr(PythonPackage):
    """Zarr: chunked, compressed, N-dimensional arrays for Python.

    Overlay copy: the builtin (2.18.7) and ska-sdp-spack recipes require
    Python >=3.11; 2.18.3 is the last zarr 2.x that supports Python 3.10
    together with numpy 2, as needed by dask-ms.
    """

    homepage = "https://github.com/zarr-developers/zarr-python"
    pypi = "zarr/zarr-2.18.3.tar.gz"

    license("MIT")

    version(
        "2.18.3",
        sha256="2580d8cb6dd84621771a10d31c4d777dca8a27706a1a89b29f42d2d37e2df5ce",
    )

    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-setuptools@64:", type="build")
    depends_on("py-setuptools-scm@1.5.5:+toml", type="build")

    depends_on("py-asciitree", type=("build", "run"))
    depends_on("py-fasteners", type=("build", "run"))
    depends_on("py-numcodecs@0.10:0.13,0.14.2:0.15", type=("build", "run"))
    depends_on("py-numpy@1.24:", type=("build", "run"))

    import_modules = ["zarr"]
