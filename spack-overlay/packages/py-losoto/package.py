import os
import re

from spack.package import *


class PyLosoto(PythonPackage):
    """LoSoTo: LOFAR solutions tool"""

    homepage = "http://github.com/revoltek/losoto/"
    pypi = "losoto/losoto-1.0.0.tar.gz"

    license("GPL-3.0-or-later")

    version(
        "2.6.0",
        sha256="7073409ca9fda29c5060af91ced8c967aea033904e3b38dc28d828f1590ca464",
    )
    version(
        "2.5.0",
        sha256="fa916411f7568d1baeba8ca103f1e929d9339bc4cc5a9bf1d66ab9e6b55ddb75",
    )
    version(
        "2.4.4",
        sha256="94372a12b743b408353ae54ff4a6a479f790f9f7616aecf64db2eebbe87c0b89",
    )

    depends_on("python@3.10:", when="@2.6.0:", type=("build", "run"))
    depends_on("python@3", type=("build", "run"))

    # 2.6.0 pyproject.toml uses PEP 639 bare SPDX string for license,
    # which requires setuptools 77+.  Older versions need setuptools <= 70.
    depends_on("py-setuptools@77:", when="@2.6.0:", type="build")
    depends_on("py-setuptools@:70", when="@:2.5", type="build")

    depends_on("py-configparser", when="@:2.5", type="build")
    depends_on("py-cython", when="@:2.5", type="build")

    depends_on("py-tables@3.9.0:", type="run")
    depends_on("py-numpy@2:", when="@2.6.0:", type="run")
    depends_on("py-numpy@1.9.0:", when="@:2.5", type="run")
    depends_on("py-scipy@1.4:", type="run")
    depends_on("py-matplotlib", type="run")
    depends_on("py-casacore@3.0:", type="run")
    depends_on("py-h5py@3.8.5:", when="@2.5:", type="run")
    # Declared in pyproject but missing from the upstream Spack recipe.
    depends_on("py-progressbar2", type="run")

    def setup_build_environment(self, env):
        # Without a git tree setuptools-scm emits 0.0.0; pin the Spack version.
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LOSOTO", self.spec.version.string)
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION", self.spec.version.string)

    @run_after("install")
    def rewrite_dist_info_version(self):
        """Ensure the installed dist reports the Spack version for pip check."""
        version = self.spec.version.string
        python_version = self.spec["python"].version.up_to(2)
        site = join_path(self.prefix.lib, f"python{python_version}", "site-packages")
        if not os.path.isdir(site):
            return
        for entry in os.listdir(site):
            if not entry.startswith("losoto-") or not entry.endswith(".dist-info"):
                continue
            dist_info = join_path(site, entry)
            metadata = join_path(dist_info, "METADATA")
            if os.path.isfile(metadata):
                text = open(metadata, encoding="utf-8").read()
                text = re.sub(
                    r"(?m)^Version:.*$", f"Version: {version}", text, count=1
                )
                open(metadata, "w", encoding="utf-8").write(text)
            target = join_path(site, f"losoto-{version}.dist-info")
            if dist_info != target and not os.path.exists(target):
                os.rename(dist_info, target)
            break
