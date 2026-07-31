# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Karabo overlay for py-gpy.

Upstream GPy 1.13.2 declares ``numpy<2`` and ``scipy<=1.12``. The builtin
recipe only had lower bounds, which lets a unified env concretize against
numpy 2 / scipy 1.14+ and then fail at build or when ``ps_eor.ml_gpr`` calls
``scipy.integrate.trapz`` (removed after 1.14).
"""

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyGpy(PythonPackage):
    """The Gaussian Process Toolbox."""

    homepage = "https://sheffieldml.github.io/GPy/"
    pypi = "gpy/GPy-1.13.2.tar.gz"
    git = "https://github.com/SheffieldML/GPy.git"

    maintainers("liuyangzhuan")

    license("BSD-3-Clause")

    version("1.13.2", sha256="a38256b4dda536a5b5e6134a3924b42d454e987ee801fb6fc8b55a922da27920")
    version("1.10.0", sha256="a2b793ef8d0ac71739e7ba1c203bc8a5afa191058b42caa617e0e29aa52aa6fb")
    version("1.9.9", sha256="04faf0c24eacc4dea60727c50a48a07ddf9b5751a3b73c382105e2a31657c7ed")
    version("0.8.8", sha256="e135d928cf170e2ec7fb058a035b5a7e334dc6b84d0bfb981556782528341988")

    variant("plotting", default=False, description="Enable plotting")

    depends_on("c", type="build")

    depends_on("py-setuptools", type="build")
    depends_on("py-numpy@1.7:1", type=("build", "run"), when="@1.13:")
    depends_on("py-numpy@1.7:", type=("build", "run"), when="@:1.12")
    depends_on("py-scipy@1.3:1.12", type=("build", "run"), when="@1.13:")
    depends_on("py-scipy@1.3:", type=("build", "run"), when="@1.10:1.12")
    depends_on("py-scipy@0.16:", type=("build", "run"), when="@:1.9")
    depends_on("py-six", type=("build", "run"))
    depends_on("py-paramz@0.9.0:", type=("build", "run"))
    depends_on("py-cython@0.29:", type="build")

    with when("+plotting"):
        depends_on("py-matplotlib@3.0:", type=("build", "run"))
        depends_on("py-plotly@1.8.6:", type=("build", "run"))

    @run_before("install")
    def touch_sources(self):
        # Uses deprecated build_ext; force recythonization.
        # See https://github.com/SheffieldML/GPy/pull/1020
        for src in find(".", "*.pyx"):
            touch(src)
