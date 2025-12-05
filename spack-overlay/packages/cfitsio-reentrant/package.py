# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *


class CfitsioReentrant(AutotoolsPackage):
    """CFITSIO library pinned to version 3.x with reentrant support.

    This package provides CFITSIO 3.49 for packages that require the older API
    (e.g., mwalib, hyperbeam, hyperdrive). The main cfitsio package can use
    version 4.x for other packages.

    CFITSIO is a library of C and Fortran subroutines for reading and writing
    data files in FITS (Flexible Image Transport System) data format.
    """

    homepage = "https://heasarc.gsfc.nasa.gov/fitsio/"
    url = "https://heasarc.gsfc.nasa.gov/FTP/software/fitsio/c/cfitsio-3.49.tar.gz"

    license("custom")

    # Only provide 3.x versions - 4.x has breaking API changes
    version("3.49", sha256="5b65a20d5c53494ec8f638267fca4a629836b7ac8dd0ef0266834eab270ed4b3", preferred=True)
    version("3.48", sha256="91b48ffef544eb8ea3908543052331072c99bf09ceb139cb3c6977fc3e47aac1")
    version("3.47", sha256="418516f10ee1e0f1b520926eeca6b77ce639bed88804c7c545e74f26b3edf4ef")

    depends_on("c", type="build")
    depends_on("fortran", type="build")

    variant("bzip2", default=True, description="Enable bzip2 support")
    variant("shared", default=True, description="Build shared libraries")

    depends_on("zlib")
    depends_on("bzip2", when="+bzip2")

    def configure_args(self):
        spec = self.spec
        extra_args = []
        if spec.satisfies("+bzip2"):
            extra_args.append(f"--with-bzip2={spec['bzip2'].prefix}")
        # Always enable reentrant support - required by mwalib and MWA tools
        extra_args.append("--enable-reentrant")
        return extra_args

    def setup_build_environment(self, env):
        z = self.spec["zlib"].prefix
        env.append_flags("CPPFLAGS", f"-I{z.include}")
        libdir = getattr(z, "lib64", None) or z.lib
        env.append_flags("LDFLAGS", f"-L{libdir}")

    @property
    def build_targets(self):
        targets = ["all"]
        if self.spec.satisfies("+shared"):
            targets += ["shared"]
        return targets

