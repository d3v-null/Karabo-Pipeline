"""Spack recipe for jupyterlab-server 2.x (compatible with tornado 6.1).

This file uses Spack's DSL (version, depends_on, etc.), which confuses static
linters. Disable lints for this file.
"""  # flake8: noqa  # mypy: ignore-errors
# pyright: reportMissingImports=false, reportUndefinedVariable=false, reportMissingModuleSource=false

from spack.package import (version, build_system, PythonPackage, depends_on)

class PyJupyterlabServer(PythonPackage):
    """A set of server components for JupyterLab and JupyterLab-like applications.

    JupyterLab Server 2.x provides core services for JupyterLab 3.x, compatible
    with tornado 6.1.
    """

    homepage = "https://github.com/jupyterlab/jupyterlab_server"
    pypi = "jupyterlab_server/jupyterlab_server-2.27.3.tar.gz"

    # JupyterLab Server 2.x versions
    version("2.27.3", sha256="eb36caca59e74471988f0ae25c77945610b887f777255aa21f8065def9e51ed4")
    version("2.27.2", sha256="15cbb349dc45e954e09bacf81b9f9bcb10815ff660fb2034ecd7417db3a7ea27")
    version("2.27.1", sha256="097b5ac709b676c7284a6c5b370a6f956b5767a8c3074f5e9f0d0762e73bb98a")
    version("2.27.0", sha256="d4e065c19cd4d2a0f3ff8c9475ea6b5676e7bdb821066e9472fabb9d3032f333")
    version("2.22.1", sha256="dfaaf898af84b9d01ae9583b813f378b96ee90c3a66f24c5186ea5d1bbdb2089", preferred=True)

    # Use pip-based build system
    build_system("python_pip")

    # Importable top-level module
    import_modules = ["jupyterlab_server"]

    # Build requirements
    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-jupyter-packaging@0.9:0", when="@:2.14", type="build")
    depends_on("py-hatchling@1.5:", when="@2.16:", type="build")
    depends_on("py-setuptools", when="@:2.14", type="build")
    depends_on("py-pip", type="build")

    # Runtime requirements for JupyterLab Server 2.27+ (matching conda)
    depends_on("py-babel@2.10:", type="run")
    depends_on("py-jinja2@3.0.3:", type="run")
    depends_on("py-json5@0.9:", type="run")
    depends_on("py-jsonschema@4.18:", type="run")
    depends_on("py-jupyter-server@1.21:2", type="run")
    depends_on("py-packaging@21.3:", type="run")
    depends_on("py-requests@2.31:", type="run")

    def setup_build_environment(self, env):
        # Ensure Spack provides dependencies without pip attempting isolation
        env.set("PIP_NO_BUILD_ISOLATION", "1")

    def test_jupyterlab_server_import(self):
        """Verify that jupyterlab_server can be imported successfully."""
        python = self.spec["python"].command
        code = (
            "import jupyterlab_server\n"
            "print(f'JUPYTERLAB_SERVER_IMPORT_OK version={jupyterlab_server.__version__}')\n"
        )
        python("-c", code)
