from spack.package import *


class PySchemaSalad(PythonPackage):
    """Schema Annotations for Linked Avro Data (SALAD)"""

    homepage = "https://schema-salad.readthedocs.io/"
    pypi = "schema-salad/schema_salad-8.9.20260417192335.tar.gz"

    license("Apache-2.0")

    version(
        "8.8.20250205075315",
        sha256="444a45509fb048347e0ec205b2af6390f0bb145f7183716ba6af2f75a22b8bdd",
    )
    version(
        "8.9.20260417192335",
        sha256="5ad4599231dcf7ae8ae2fc841a677db9c120544b36a6d6347ae87875b2c1b083",
    )

    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-setuptools@50:", type="build")
    depends_on("py-setuptools-scm@8:", type="build")

    # Runtime dependencies from upstream setup.py install_requires
    depends_on("py-requests@1:", type=("build", "run"))
    depends_on("py-ruamel-yaml@0.17.6:0.19", type=("build", "run"))
    depends_on("py-rdflib@4.2.2:7", type=("build", "run"))
    depends_on("py-mistune@3:3.2", type=("build", "run"))
    depends_on("py-cachecontrol@0.13.1:0.14", type=("build", "run"))
    depends_on("py-mypy-extensions", type=("build", "run"))
    depends_on("py-rich-argparse", type=("build", "run"))

    # Optional pycodegen extra
    depends_on("py-black", type=("build", "run"))
