"""Spack recipe for notebook 6.x (compatible with tornado 6.1).

This file uses Spack's DSL (version, depends_on, etc.), which confuses static
linters. Disable lints for this file.
"""  # flake8: noqa  # mypy: ignore-errors
# pyright: reportMissingImports=false, reportUndefinedVariable=false, reportMissingModuleSource=false

from spack.package import (version, build_system, PythonPackage, depends_on)

class PyNotebook(PythonPackage):
    """Jupyter Interactive Notebook (version 6.x - compatible with tornado 6.1).

    Notebook 6.x is the classic Jupyter Notebook interface, compatible with
    existing tornado 6.1 dependencies in the environment.
    """

    homepage = "https://github.com/jupyter/notebook"
    pypi = "notebook/notebook-6.5.7.tar.gz"

    # Notebook 7.x versions (part of JupyterLab 4 stack)
    version("7.4.7", sha256="e53b28af15f28d1bb8edc3ef5adc4b41a4329fbed90de2dcae94e73db55c1e97")
    version("7.2.2", sha256="2ef07d4220421623ad3fe88118d687bc0450055570cdd160814a59cf3a1c516e")
    version("7.0.8", sha256="e43f4c3f0735e0a19f304a13c5d3e3a83fc0c61e5e2fa00df1eeb9e36b8f53a6", preferred=True)

    # Use pip-based build system
    build_system("python_pip")

    # Importable top-level module
    import_modules = ["notebook"]

    # Build requirements
    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-hatchling@1.5:", type="build")
    depends_on("py-hatch-jupyter-builder@0.8.1:", type="build")
    depends_on("py-jupyterlab@4:", type="build")
    depends_on("py-pip", type="build")

    # Runtime requirements for notebook 7.x (part of JupyterLab 4)
    depends_on("py-jupyter-server@2.4:", type="run")
    depends_on("py-jupyterlab@4:", type="run")
    depends_on("py-jupyterlab-server@2.22:", type="run")
    depends_on("py-notebook-shim@0.2:", type="run")
    depends_on("py-tornado@6:", type="run")  # Compatible with 6.5.2

    def setup_build_environment(self, env):
        # Ensure Spack provides dependencies without pip attempting isolation
        env.set("PIP_NO_BUILD_ISOLATION", "1")

    def test_notebook_import(self):
        """Verify that notebook can be imported successfully."""
        python = self.spec["python"].command
        code = (
            "import notebook\n"
            "print(f'NOTEBOOK_IMPORT_OK version={notebook.__version__}')\n"
        )
        python("-c", code)
