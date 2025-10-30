# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *
from spack.pkg.builtin.llvm import Llvm as BuiltinLlvm


class Llvm(BuiltinLlvm):
    """Overlay to add newer LLVM versions and deprecate problematic ones.

    The LLVM Project is a collection of modular and reusable compiler and
    toolchain technologies. This overlay adds version 19.1.7 which fixes
    issues with ARM builds and marks older 19.1.x versions as deprecated.
    """

    # Add the stable 19.1.7 version (fixes ARM build issues)
    version("19.1.7", sha256="59abea1c22e64933fad4de1671a61cdb934098793c7a31b333ff58dc41bff36c")

    # Mark problematic 19.1.x versions as deprecated (especially for ARM)
    # These versions are known to hang during installation on ARM platforms
    with default_args(deprecated=True):
        version(
            "19.1.6", sha256="f07fdcbb27b2b67aa95e5ddadf45406b33228481c250e65175066d36536a1ee2"
        )
        version(
            "19.1.5", sha256="e2204b9903cd9d7ee833a2f56a18bef40a33df4793e31cc090906b32cbd8a1f5"
        )
        version(
            "19.1.4", sha256="010e1fd3cabee8799bd2f8a6fbc68f28207494f315cf9da7057a2820f79fd531"
        )
        version(
            "19.1.3", sha256="e5106e2bef341b3f5e41340e4b6c6a58259f4021ad801acf14e88f1a84567b05"
        )
        version(
            "19.1.2", sha256="622cb6c5e95a3bb7e9876c4696a65671f235bd836cfd0c096b272f6c2ada41e7"
        )
        version(
            "19.1.1", sha256="115dfd98a353d05bffdab3f80db22f159da48aca0124e8c416f437adcd54b77f"
        )
        version(
            "19.1.0", sha256="0a08341036ca99a106786f50f9c5cb3fbe458b3b74cab6089fd368d0edb2edfe"
        )
