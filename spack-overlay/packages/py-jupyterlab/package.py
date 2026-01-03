"""Spack recipe for jupyterlab 3.x (compatible with tornado 6.1).

This file uses Spack's DSL (version, depends_on, etc.), which confuses static
linters. Disable lints for this file.
"""  # flake8: noqa  # mypy: ignore-errors
# pyright: reportMissingImports=false, reportUndefinedVariable=false, reportMissingModuleSource=false

from spack.package import (version, build_system, depends_on)
from spack_repo.builtin.build_systems.python import PythonPackage

class PyJupyterlab(PythonPackage):
    """JupyterLab is the next-generation web-based user interface for Project Jupyter.

    JupyterLab 3.x is compatible with tornado 6.1 and integrates well with existing
    notebook infrastructure.
    """

    homepage = "https://github.com/jupyterlab/jupyterlab"
    pypi = "jupyterlab/jupyterlab-3.6.8.tar.gz"

    # JupyterLab 4.x versions (matching conda working versions)
    version("4.4.6", sha256="6bb5ec11c4cd1e7985d8f01d88fef20e88d1a8188ab63b5f57c18e15438c1dc7")
    version("4.4.5", sha256="1bf8be9dfddcfe546c7d23e2df0080c2ddc20ff2f15e5fb91e39b0e75ebf46de")
    version("4.2.5", sha256="ae7f3a1b8cb88b4f55009ce79fa7c06f99d70cd63601ee4aa91815d054f46f75")
    version("4.0.8", sha256="c4e9fa6de7f43e3c2e8178b102635a8ee1ef76ecadc60b3ace3c5e0e371c2125", preferred=True)

    # Use pip-based build system
    build_system("python_pip")

    # Importable top-level module
    import_modules = ["jupyterlab"]

    # Optional dependencies needed to install jupyterlab extensions
    depends_on("node-js", type="run")
    depends_on("npm", type="run")

    # Build requirements
    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-hatchling@1.5:", type="build")
    depends_on("py-hatch-jupyter-builder@0.3.2:", type="build")
    depends_on("py-pip", type="build")

    # Runtime requirements for JupyterLab 4.x (matching conda versions)
    depends_on("py-async-lru@1:", type="run")
    depends_on("py-httpx@0.25:", type="run")
    depends_on("py-ipykernel", type="run")
    depends_on("py-jinja2@3.0.3:", type="run")
    depends_on("py-jupyter-core", type="run")
    depends_on("py-jupyter-lsp@2:", type="run")
    depends_on("py-jupyter-server@2.4:2", type="run")
    depends_on("py-jupyterlab-server@2.22:", type="run")
    depends_on("py-notebook-shim@0.2:", type="run")
    depends_on("py-packaging", type="run")
    depends_on("py-tornado@6:", type="run")  # Compatible with 6.5.2
    depends_on("py-traitlets", type="run")

    def setup_build_environment(self, env):
        # Ensure Spack provides dependencies without pip attempting isolation
        env.set("PIP_NO_BUILD_ISOLATION", "1")

    def setup_run_environment(self, env):
        env.set("JUPYTERLAB_DIR", self.prefix.share.jupyter.lab)

    def test_jupyterlab_import(self):
        """Verify that jupyterlab can be imported successfully."""
        python = self.spec["python"].command
        code = (
            "import jupyterlab\n"
            "print(f'JUPYTERLAB_IMPORT_OK version={jupyterlab.__version__}')\n"
        )
        python("-c", code)
