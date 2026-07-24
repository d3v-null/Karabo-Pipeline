from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyCwltool(PythonPackage):
    """Common Workflow Language reference implementation."""

    homepage = "https://github.com/common-workflow-language/cwltool"
    pypi = "cwltool/cwltool-3.1.20260108082145.tar.gz"

    license("Apache-2.0")

    version(
        "3.1.20260108082145",
        sha256="a12124fa8c1337539b8f291690a01e92f7ab12e4259cc062d40e50f60908bec3",
    )

    depends_on("python@3.9:3", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm@8.0.4:8", type="build")

    depends_on("py-requests@2.6.1:", type=("build", "run"))
    depends_on("py-ruamel-yaml@0.16:0.18", type=("build", "run"))
    depends_on("py-rdflib@4.2.2:7.1", type=("build", "run"))
    depends_on("py-schema-salad@8.7:8", type=("build", "run"))
    depends_on("py-prov@1.5.1", type=("build", "run"))
    depends_on("py-mypy-extensions", type=("build", "run"))
    depends_on("py-psutil@5.6.6:", type=("build", "run"))
    depends_on("py-typing-extensions", type=("build", "run"))
    depends_on("py-coloredlogs", type=("build", "run"))
    depends_on("py-pydot@1.4.1:2", type=("build", "run"))
    depends_on("py-argcomplete@1.12:", type=("build", "run"))
    depends_on("py-pyparsing@:3.0.1,3.0.3:", type=("build", "run"))
    depends_on("py-cwl-utils@0.32:", type=("build", "run"))
    depends_on("py-spython@0.3.0:", type=("build", "run"))
    depends_on("py-rich-argparse", type=("build", "run"))
    depends_on("node-js", type="run")
