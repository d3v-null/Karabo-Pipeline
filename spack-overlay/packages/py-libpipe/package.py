# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyLibpipe(PythonPackage):
    """Lightweight pipeline helpers used by ps_eor's ml-gpr extra."""

    homepage = "https://pypi.org/project/libpipe/"
    pypi = "libpipe/libpipe-0.5.tar.gz"

    license("MIT")

    version("0.5", sha256="49586cae82f737c1e487c531811354f9c61e96b732cff8953923faec26be1116")

    depends_on("python@3.8:", type=("build", "run"))
    # libpipe's own pyproject.toml declares build-backend = "poetry.core.masonry.api",
    # not setuptools — pip's --no-build-isolation install needs poetry-core importable
    # in the build env or it fails with "BackendUnavailable: Cannot import
    # 'poetry.core.masonry.api'".
    depends_on("py-poetry-core", type="build")
    depends_on("py-asyncssh@2:", type=("build", "run"))
    depends_on("py-progressbar2@3.40:", type=("build", "run"))
    depends_on("py-toml@0.10:", type=("build", "run"))
    depends_on("py-click@8:", type=("build", "run"))

    import_modules = ["libpipe"]
