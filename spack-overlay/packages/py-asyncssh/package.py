# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import *


class PyAsyncssh(PythonPackage):
    """AsyncSSH: Asynchronous SSHv2 client and server library."""

    homepage = "https://asyncssh.readthedocs.io/"
    pypi = "asyncssh/asyncssh-2.21.0.tar.gz"

    license("EPL-2.0")

    version("2.21.0", sha256="450fe13bb8d86a8f4e7d7b5fafce7791181ca3e7c92e15bbc45dfb25866e48b3")

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-cryptography@39:", type=("build", "run"))
    depends_on("py-typing-extensions@4:", type=("build", "run"))

    import_modules = ["asyncssh"]
