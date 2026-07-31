# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyUltranest(PythonPackage):
    """Fit and compare complex models reliably and rapidly with advanced nested sampling."""

    homepage = "https://johannesbuchner.github.io/UltraNest/"
    pypi = "ultranest/ultranest-4.4.0.tar.gz"

    license("GPL-3.0-or-later")

    version("4.4.0", sha256="dfebdc4b2bc0138238f65e8f957b70fe296cb094c895172f4a368e792a59b501")

    depends_on("c", type="build")
    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-cython", type="build")
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))

    import_modules = ["ultranest"]
