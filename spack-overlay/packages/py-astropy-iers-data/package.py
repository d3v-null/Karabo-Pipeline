# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *
from spack_repo.builtin.build_systems.python import PythonPackage


class PyAstropyIersData(PythonPackage):
    """IERS Earth rotation and leap second table

    Note: This package is not meant for standalone purposes
    but is needed by AstroPy."""

    homepage = "https://github.com/astropy/astropy-iers-data"
    pypi = "astropy-iers-data/astropy_iers_data-0.2024.4.29.0.28.48.tar.gz"

    version(
        "0.2024.5.20.0.29.40",
        sha256="7fff3d3404ae8560533ac0e685db7acc02c4d8984faa4ac3d607096879fba2d1",
    )
    version(
        "0.2024.4.29.0.28.48",
        sha256="a2d5acf97e731f1d4a0eab1c8e4c7f454ddc166af06797b141202dd901bd1dfc",
    )

    depends_on("python@3.8:")
    depends_on("py-setuptools@63", type="build")  # Pin to 63.x which works with PIP_NO_BUILD_ISOLATION
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-wheel", type="build")
    depends_on("py-tomli", type="build")  # Required by setuptools-scm on Python < 3.11

    def setup_build_environment(self, env):
        # Set the version for setuptools-scm to avoid git dependency
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION", self.spec.version.string)

    @run_after("install")
    def fix_version_file(self):
        """Ensure _version.py contains __version__ if setuptools-scm fails."""
        import os

        site_packages = join_path(
            self.prefix,
            "lib",
            f"python{self.spec['python'].version.up_to(2)}",
            "site-packages",
            "astropy_iers_data",
        )

        version_file = join_path(site_packages, "_version.py")

        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                content = f.read()

            if "__version__" not in content:
                with open(version_file, "w") as f:
                    f.write(f'__version__ = "{self.spec.version.string}"\n')

