# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Karabo overlay for py-pyerfa.

Builtin ``@2.0.1.1`` requires ``py-numpy@1.25:1``, which conflicts with
``%gcc@11`` in builtin py-numpy. SWF-8 stays on NumPy 1.24.x + gcc 11, and
``@2.0.1.5:`` wants NumPy 2 at build time — so pin 2.0.1.1 with a 1.24 floor.
"""

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyPyerfa(PythonPackage):
    """Python wrapper for the ERFA library."""

    homepage = "https://github.com/liberfa/pyerfa"
    pypi = "pyerfa/pyerfa-2.0.1.1.tar.gz"

    license("BSD-3-Clause")

    version("2.0.1.5", sha256="17d6b24fe4846c65d5e7d8c362dcb08199dc63b30a236aedd73875cc83e1f6c0")
    version("2.0.1.1", sha256="dbac74ef8d3d3b0f22ef0ad3bbbdb30b2a9e10570b1fa5a98be34c7be36c9a6b")
    version("2.0.0.1", sha256="2fd4637ffe2c1e6ede7482c13f583ba7c73119d78bef90175448ce506a0ede30")

    depends_on("c", type="build")
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-packaging", type="build")
    depends_on("py-jinja2@2.10.3:", type="build")
    depends_on("erfa", type=("build", "link", "run"))

    depends_on("py-numpy@2.0.0rc1:", when="@2.0.1.5:", type="build")
    depends_on("py-numpy@1.19.3:", when="@2.0.1.5:", type=("build", "run"))
    # Relaxed from builtin @1.25:1 so gcc-11 + numpy 1.24.x environments work.
    depends_on("py-numpy@1.24:1", when="@2.0.1.1", type=("build", "run"))
    depends_on("py-numpy@1.17:", type=("build", "run"))

    import_modules = ["erfa"]
