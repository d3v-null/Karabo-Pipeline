# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyFastHistogram(PythonPackage):
    """Fast 1D and 2D histogram functions with no overflow bins."""

    homepage = "https://github.com/astrofrog/fast-histogram"
    pypi = "fast-histogram/fast_histogram-0.14.tar.gz"

    license("BSD-2-Clause")

    version("0.14", sha256="390973b98af22bda85c29dcf6f008ba0d626321e9bd3f5a9d7a43e5690ea69ea")

    depends_on("c", type="build")
    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-numpy", type=("build", "run"))

    import_modules = ["fast_histogram"]
