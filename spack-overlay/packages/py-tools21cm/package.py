"""Spack recipe for tools21cm.

This file uses Spack's DSL (version, depends_on, etc.), which confuses static
linters. Disable lints for this file.
"""  # flake8: noqa  # mypy: ignore-errors
# pyright: reportMissingImports=false, reportUndefinedVariable=false, reportMissingModuleSource=false

from spack.package import (version, build_system, PythonPackage, depends_on, filter_file)

class PyTools21cm(PythonPackage):
    """Tools for analysing cosmological simulations of the 21cm signal.

    A package providing tools to analyse cosmological simulations of reionization
    and understand the distribution of ionized, neutral, and partially ionized
    regions in the intergalactic medium during the Epoch of Reionization.
    """

    homepage = "https://github.com/sambit-giri/tools21cm"
    git = "https://github.com/sambit-giri/tools21cm.git"
    pypi = "tools21cm/tools21cm-2.3.8.tar.gz"

    # Pin the exact version used in docker builds
    version("2.3.8", tag="v2.3.8", preferred=True)

    # Use pip-based build system
    build_system("python_pip")

    # Importable top-level module
    import_modules = ["tools21cm"]

    # Build requirements from pyproject.toml
    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools@42:", type="build")
    depends_on("py-setuptools-scm@6:", type="build")
    depends_on("py-pip", type="build")
    depends_on("py-wheel", type="build")

    # Build-time requirements for Cython extensions
    depends_on("py-cython", type="build")
    depends_on("py-numpy", type=("build", "run"))

    # Runtime requirements from requirements.txt
    depends_on("py-scipy", type="run")
    depends_on("py-matplotlib", type="run")
    depends_on("py-astropy", type="run")
    depends_on("py-scikit-learn", type="run")
    depends_on("py-scikit-image", type="run")
    depends_on("py-tqdm", type="run")
    depends_on("py-joblib", type="run")
    depends_on("py-pandas", type="run")
    depends_on("py-openpyxl", type="run")
    depends_on("py-pytest", type="run")
    # torch and numba are commented out in requirements.txt, so we don't add them

    def patch(self):
        # Inject version into setup.py to use setuptools_scm
        filter_file(
            "setup(",
            "setup(\n    use_scm_version={'write_to': 'src/tools21cm/_version.py'},",
            "setup.py",
            string=True
        )
        # Remove hardcoded version line
        filter_file(
            r"^\s*version=.*,$",
            "",
            "setup.py",
            backup=False
        )
        # Inject version import into __init__.py
        filter_file(
            "import sys",
            "import sys\ntry:\n    from ._version import version as __version__\nexcept ImportError:\n    __version__ = 'unknown'\n",
            "src/tools21cm/__init__.py",
            string=True
        )

    def setup_build_environment(self, env):
        # Ensure Spack provides dependencies without pip attempting isolation
        env.set("PIP_NO_BUILD_ISOLATION", "1")
        # Provide deterministic version metadata via setuptools-scm
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION", self.spec.version.string)
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TOOLS21CM", self.spec.version.string)

    def test_tools21cm_import(self):
        """Verify that tools21cm can be imported successfully."""
        python = self.spec["python"].command
        code = (
            "import tools21cm\n"
            "import tools21cm.power_spectrum\n"
            "import tools21cm.lightcone\n"
            "# Check version via __version__ attribute\n"
            "assert hasattr(tools21cm, '__version__'), 'Missing __version__ attribute'\n"
            "print(f'TOOLS21CM_IMPORT_OK version={tools21cm.__version__}')\n"
            "# Also verify importlib.metadata works\n"
            "from importlib.metadata import version\n"
            "pkg_version = version('tools21cm')\n"
            "print(f'Package metadata version={pkg_version}')\n"
        )
        python("-c", code)

