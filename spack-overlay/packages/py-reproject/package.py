# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the Spack COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


# ska-sdp-spack 2026.10.3 recipe + the missing 0.14 runtime dependencies.
class PyReproject(PythonPackage):
    """The reproject package is a Python package to reproject
    astronomical images using various techniques via a uniform
    interface. By reprojection, we mean the re-gridding of images from
    one world coordinate system to another (for example changing the
    pixel resolution, orientation, coordinate system). Currently, we
    have implemented reprojection of celestial images by interpolation
    (like SWARP), as well as by finding the exact overlap between
    pixels on the celestial sphere (like Montage). It can also
    reproject to/from HEALPIX projections by relying on the
    astropy-healpix package."""

    homepage = "https://reproject.readthedocs.io/"
    pypi = "reproject/reproject-0.14.1.tar.gz"

    license("BSD-3-Clause")

    version(
        "0.14.1",
        sha256="53c8ea279b8b557f33a1e430af5e053cd747002440e072bae6ad9302d46be579",
    )
    version(
        "0.11.0",
        sha256="37184a807c15a5e214564c44a541399f6ceffcb6b1ac624935022d1b31c5075c",
    )
    version(
        "0.10.0",
        sha256="38ac4f3ca71556b11550647c65aa619fbbabf473aea9029af609cca3645040c1",
    )
    version(
        "0.9",
        sha256="ce18c8e0c8e5095f734749cd72cb3e0b7e8265763f8a61ac6a57ca30669c7e2d",
    )
    version(
        "0.7.1",
        sha256="95c0fa49e6b4e36455b91fa09ad1b71b230c990ad91d948af67ea3509a1a4ccb",
    )

    depends_on("python@3.6:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-cython@0.29.32:", type="build")
    depends_on("py-extension-helpers@1:", type="build", when="@0.10:")
    depends_on("py-extension-helpers", type="build")
    depends_on("py-numpy@1.13:", type=("build", "run"))
    depends_on("py-astropy@6.1:", type=("build", "run"), when="@0.10:")
    depends_on("py-astropy", type=("build", "run"))
    depends_on("py-scipy@1.1:", type=("build", "run"))
    depends_on("py-astropy-healpix@1.0:", type=("build", "run"), when="@0.10:")
    depends_on("py-astropy-healpix@0.2:", type=("build", "run"))
    # Undocumented dependency
    depends_on("py-dask@2021.8:", type=("build", "run"), when="@0.11:")
    # Not in sdp: install_requires of 0.14; zarr backs dask-array inputs and parallel mode.
    depends_on("py-cloudpickle", type=("build", "run"), when="@0.14:")
    depends_on("py-fsspec", type=("build", "run"), when="@0.14:")
    depends_on("py-zarr", type=("build", "run"), when="@0.14:")
