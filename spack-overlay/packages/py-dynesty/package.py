# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyDynesty(PythonPackage):
    """A dynamic nested sampling package for computing Bayesian posteriors and evidences."""

    homepage = "https://github.com/joshspeagle/dynesty"
    pypi = "dynesty/dynesty-2.1.4.tar.gz"

    license("MIT")

    version("2.1.4", sha256="cd98cfded1af86487b76dba2bd89824c803f1e0c451fcb14a0b208c5ca1a8004")

    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))

    import_modules = ["dynesty"]
