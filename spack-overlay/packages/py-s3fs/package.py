from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyS3fs(PythonPackage):
    """S3FS: a Pythonic file interface to S3 built on fsspec.

    Overlay copy: s3fs pins fsspec to the exact same release; the image
    ships fsspec 2025.9.0, which builtin Spack's s3fs versions predate.
    """

    homepage = "https://github.com/fsspec/s3fs"
    pypi = "s3fs/s3fs-2025.9.0.tar.gz"

    license("BSD-3-Clause")

    version(
        "2025.9.0",
        sha256="6d44257ef19ea64968d0720744c4af7a063a05f5c1be0e17ce943bef7302bc30",
    )

    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-setuptools", type="build")

    depends_on("py-aiobotocore@2.5.4:2", type=("build", "run"))
    depends_on("py-fsspec@2025.9.0", when="@2025.9.0", type=("build", "run"))
    depends_on("py-aiohttp", type=("build", "run"))

    import_modules = ["s3fs"]
