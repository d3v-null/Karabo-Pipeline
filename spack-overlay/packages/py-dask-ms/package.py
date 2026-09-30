from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, variant, version


class PyDaskMs(PythonPackage):
    """dask-ms: xarray Datasets backed by CASA Measurement Sets, zarr and
    parquet, built on dask."""

    homepage = "https://github.com/ratt-ru/dask-ms"
    pypi = "dask-ms/dask_ms-0.2.27.tar.gz"

    license("BSD-3-Clause")

    version(
        "0.2.27",
        sha256="94477187d949246e0c8c8042714a030adfef105e83df22930fd8a4a7b97bcd13",
    )

    variant("xarray", default=True, description="xarray Dataset support")
    variant("zarr", default=True, description="zarr storage backend")
    variant("s3", default=True, description="S3 (s3fs) storage support")

    depends_on("python@3.10:3.13", type=("build", "run"))
    depends_on("py-hatchling", type="build")

    depends_on("py-appdirs@1.4.4:", type=("build", "run"))
    depends_on("py-cacheout@0.16.0:", type=("build", "run"))
    depends_on("py-dask@2023.1.1:2024.10+array", type=("build", "run"))
    depends_on("py-donfig@0.8.0:", type=("build", "run"))
    depends_on("py-fsspec@2022.7.0:", type=("build", "run"))
    depends_on("py-numpy@2.0.0:", type=("build", "run"))
    depends_on("py-casacore@3.7.0:", type=("build", "run"))

    depends_on("py-xarray@2023.01.0:", type=("build", "run"), when="+xarray")
    depends_on("py-zarr@2.12.0:2", type=("build", "run"), when="+zarr")
    depends_on("py-numcodecs@:0.15", type=("build", "run"), when="+zarr")
    depends_on("py-s3fs@2023.1.0:", type=("build", "run"), when="+s3")

    import_modules = ["daskms"]
