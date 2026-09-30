from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyAiobotocore(PythonPackage):
    """Async client for AWS services using botocore and aiohttp.

    Overlay copy: builtin 2.12.1 pins botocore <=1.34.51, whose urllib3
    <2.1 requirement clashes with the image's urllib3 2.3; 2.13.3 allows
    botocore 1.34.162 (urllib3 2.x).
    """

    homepage = "https://github.com/aio-libs/aiobotocore"
    pypi = "aiobotocore/aiobotocore-2.13.3.tar.gz"

    license("Apache-2.0")

    version(
        "2.13.3",
        sha256="ac5620f93cc3e7c2aef7c67ba2bb74035ff8d49ee2325821daed13b3dd82a473",
    )

    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools", type="build")

    depends_on("py-botocore@1.34.70:1.34.162", when="@2.13.3", type=("build", "run"))
    depends_on("py-aiohttp@3.9.2:3", type=("build", "run"))
    depends_on("py-wrapt@1.10.10:1", type=("build", "run"))
    depends_on("py-aioitertools@0.5.1:0", type=("build", "run"))

    import_modules = ["aiobotocore"]
