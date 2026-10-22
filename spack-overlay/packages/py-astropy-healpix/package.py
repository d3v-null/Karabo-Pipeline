# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the Spack COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


# Overrides the upstream Spack package, adding new versions.
class PyAstropyHealpix(PythonPackage):
    """HEALPix (Hierarchical Equal Area isoLatitude Pixelisation) is
    an algorithm for pixellizing a sphere that is sometimes used in
    Astronomy to store data from all-sky surveys, but the general
    algorithm can apply to any field that has to deal with
    representing data on a sphere."""

    homepage = "https://astropy-healpix.readthedocs.io/en/latest/"
    pypi = "astropy-healpix/astropy_healpix-1.0.3.tar.gz"

    license("BSD-3-Clause")

    version(
        "1.0.3",
        sha256="de5d2a7ec97b167045066971f25a150d1e4061f07159be23649634db36e79746",
    )
    version(
        "1.0.2",
        sha256="056fa6ed9396bedc771d374d877cde83d9460a3f62a78fe05dbf9ba03940323a",
    )
    version(
        "0.5",
        sha256="5ae15da796a840f221fb83e25de791e827b6921bc21a365d99bc1a59c7c0cdad",
    )

    depends_on("py-setuptools", type=("build", "run"))
    # pyproject build-requires it; without it the version silently falls back to 0.0.0
    depends_on("py-setuptools-scm", type="build")
    depends_on("python@3.6:", type=("build", "run"))
    depends_on("py-astropy@2.0:", type=("build", "run"))
    depends_on("py-extension-helpers@1:", type="build", when="@1.0:")
    # https://github.com/astropy/astropy-healpix/pull/214
    depends_on("py-numpy@:1", when="@:1.0.2", type=("build", "run"))
    depends_on("py-numpy@2:", when="@1.0.3:", type=("build", "run"))

    def setup_build_environment(self, env):
        # Without this the spack build reports 0.0.0, which fails `pip check`
        # (reproject requires astropy-healpix>=1.0).
        env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ASTROPY_HEALPIX", str(self.version))
