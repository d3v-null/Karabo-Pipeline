from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, variant, version


class PyToil(PythonPackage):
    """Toil: Scalable, efficient, cross-platform pipeline management system.

    Toil is a scalable, efficient, cross-platform (Linux & macOS) pipeline
    management system, written entirely in Python, and designed around the
    principles of functional programming. It supports running workflows
    written in either Common Workflow Language (CWL) 1.0-1.2 or Workflow
    Description Language (WDL) 1.0-1.1, as well as having its own rich Python
    API for writing workflows against. It supports running workflows locally
    on your system (e.g. a laptop), on an HPC cluster, or in the cloud.
    """

    homepage = "https://toil.ucsc-cgl.org"
    pypi = "toil/toil-9.3.0.tar.gz"

    license("Apache-2.0 AND MIT", checked_by="gemmadanks")

    version(
        "9.3.0",
        sha256="d932d52163bc11082b5b23c8e8f7e45e6819155993d2fc6496bb6cd03dc6e7b9",
    )
    variant("cwl", default=False, description="Enable CWL support")
    depends_on("python@3.10:", type=("build", "run"))
    depends_on("py-setuptools@64:", type="build")
    depends_on("py-setuptools-scm@8:", type="build")

    # Requirements for Toil itself
    depends_on("py-dill@0.3.2:0.4", type=("build", "run"))
    depends_on("py-requests@:2.32.5", type=("build", "run"))
    depends_on("py-docker@6.1.0:7", type=("build", "run"))
    depends_on("py-urllib3@1.26.0:2", type=("build", "run"))
    depends_on("py-python-dateutil", type=("build", "run"))
    depends_on("py-psutil@6.1.0:7", type=("build", "run"))
    depends_on("py-pypubsub@4.0.3:4", type=("build", "run"))
    depends_on("py-addict@2.2.1:2.4", type=("build", "run"))
    depends_on("py-enlighten@1.5.2:1", type=("build", "run"))
    depends_on("py-configargparse@1.7:1", type=("build", "run"))
    depends_on("py-pyyaml@6", type=("build", "run"))
    depends_on("py-typing-extensions@4.6.2:4", type=("build", "run"))
    depends_on("py-coloredlogs@15", type=("build", "run"))
    depends_on("py-prompt-toolkit@3", type=("build", "run"))

    # Requirements when using CWL
    depends_on("py-cwltool@3.1.20260108082145", type="run", when="+cwl")
    depends_on(
        "py-schema-salad@8.9:8",
        type="run",
        when="+cwl",
    )
    depends_on("py-galaxy-tool-util@22.1.5:25", type="run", when="+cwl")
    depends_on("py-galaxy-util@:25", type="run", when="+cwl")
    depends_on("py-ruamel-yaml@0.15:0.19", type="run", when="+cwl")
    depends_on("py-ruamel-yaml-clib@0.2.6:", type="run", when="+cwl")
    depends_on("py-networkx@:2.8.0,2.8.2:3", type="run", when="+cwl")
    depends_on("py-cachecontrol+filecache", type="run", when="+cwl")
    depends_on("py-cwl-utils@0.36:", type="run", when="+cwl")

    # Enable Kubernetes worker pods and deployment-provided shared storage.
    depends_on("py-kubernetes@12:35", type=("build", "run"))

    # Matches the Toil 9.3 Kubernetes worker-pod patch point used by the
    # deployed WES service, retaining shared storage for nested workers.
    patch("kubernetes-batch-system.patch", when="@9.3.0")

    # This package does not (yet) include AWS support, which requires botocore
    # and possibly other packages. Also, skip testing modules.
    skip_modules = ["toil.lib.aws", "toil.provisioners.aws", "toil.test"]
