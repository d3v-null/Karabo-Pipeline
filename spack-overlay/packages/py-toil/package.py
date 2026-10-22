# ska-sdp-spack 2026.10.3 recipe + Kubernetes batch-system patch.
from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, variant, version, when


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
    pypi = "toil/toil-8.2.0.tar.gz"

    license("Apache-2.0 AND MIT", checked_by="gemmadanks")

    version(
        "9.3.0",
        sha256="d932d52163bc11082b5b23c8e8f7e45e6819155993d2fc6496bb6cd03dc6e7b9",
    )

    version(
        "8.2.0",
        sha256="b4f1e7e1a2847cc0c050ef80bc93c86b43831749bd0592c46fa03d6f93fa5251",
    )
    variant("cwl", default=False, description="Enable CWL support")
    depends_on("py-setuptools@64:", type="build")
    depends_on("py-setuptools-scm@8:", type="build")

    # Requirements for Toil itself
    with when("@9.3.0"):
        depends_on("python@3.10:", type=("build", "run"))
        depends_on("py-dill@0.3.2:0.4", type=("build", "run"))
        # Upstream pins requests<=2.32.5, but Spack deprecates requests@:2.32.5
        # (CVE-2026-25645). Allow 2.33.1, as required by toil@9.4.0:.
        depends_on("py-requests@:2.33.1", type=("build", "run"))

    with when("@8.2.0"):
        depends_on("python@3.9:", type=("build", "run"))
        depends_on("py-dill@0.3.2:0.3", type=("build", "run"))
        depends_on("py-requests@:2.31", type=("build", "run"))

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
    with when("+cwl"):
        with when("@9.3.0"):
            depends_on("py-cwltool@3.1.20260108082145", type="run")
            depends_on("py-galaxy-tool-util@:25", type="run")
            depends_on("py-galaxy-util@:25", type="run")
            depends_on("py-cwl-utils@0.36:", type="run")

        with when("@8.2.0"):
            depends_on("py-cwltool@3.1.20250110105449", type="run")
            depends_on("py-galaxy-tool-util@22.1.5:25", type="run")
            depends_on("py-galaxy-util@:24", type="run")
            depends_on("py-cwl-utils@0.36:", type="run")

        depends_on(
            "py-schema-salad@8.4.20230128170514:8",
            type="run",
            when="+cwl",
        )
        depends_on("py-ruamel-yaml@0.15:0.19", type="run")
        depends_on("py-ruamel-yaml-clib@0.2.6:", type="run")
        depends_on("py-networkx@:2.8.0,2.8.2:3", type="run")
        depends_on("py-cachecontrol+filecache", type="run")

    # SKB-1091: This patch avoids repeatedly concatenating a saved copy
    # of the PATH to the PATH variable. Since the PATH then becomes extremely
    # long PATH, it then causes "Argument list too long" errors.
    # This was fixed in version toil 9.3.0:
    # https://github.com/DataBiosphere/toil/releases/tag/releases%2F9.3.0
    patch("path.patch", when="@:9.2")

    # Not in sdp: Kubernetes worker pods for the WES deployment (shared hostPath mount,
    # security-context loader fix, TOIL_SKIP_IMAGE_CHECK).
    depends_on("py-kubernetes@12:35", type=("build", "run"))
    patch("kubernetes-batch-system.patch", when="@9.3.0")

    # This package does not (yet) include AWS support, which requires botocore
    # and possibly other packages. Also, skip testing modules.
    skip_modules = ["toil.lib.aws", "toil.provisioners.aws", "toil.test"]
