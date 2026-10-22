# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


# Overrides the upstream package: We need a newer version than is made available
class PyPhotutils(PythonPackage):
    """
    Photutils is an Astropy package for detection and photometry of astronomical
    sources.
    """

    homepage = "https://github.com/astropy/photutils"
    git = "https://github.com/astropy/photutils.git"

    license("BSD-3-Clause")

    version(
        "2.3.0",
        tag="2.3.0",
    )

    depends_on("c", type="build")  # generated

    # From pyproject.toml
    depends_on("py-numpy@2:", type=("build", "run"))
    depends_on("py-astropy@5.3:", type=("build", "run"))
    depends_on("py-scipy@1.11.1:", type=("build", "run"))
    depends_on("py-setuptools@77:", type="build")
    depends_on("py-setuptools-scm@8.0:", type="build")
    depends_on("py-cython@3.1.0:3", type="build")
    # pyproject.toml says the minimum version is 1.3, however, the
    # latest version of the py-extension-helpers package is 1.2.
    # As no 1.3 functionality actually seems to be required, using
    # 1.2 as minimum version for now is fine.
    depends_on("py-extension-helpers@1.2:2", type="build")

    def setup_build_environment(self, env):
        # Built from a shallow git commit without tags: give setuptools-scm the real
        # version, or pip sees 0.1.dev1 and may "upgrade" it over the spack install.
        if str(self.version)[0].isdigit():
            env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PHOTUTILS", str(self.version))
