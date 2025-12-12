# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *
from spack.pkg.builtin.fftw import Fftw as BuiltinFftw


class Fftw(BuiltinFftw):
    """Overlay to disable CPU-specific optimizations to prevent illegal instruction errors.

    This package extends Spack's builtin FFTW to ensure it's compiled with generic
    CPU instructions that work across all x86_64 processors, avoiding issues when
    binaries built on newer CPUs (with AVX-512) are run on older CPUs.
    """

    def configure_args(self):
        """Add configure arguments to disable CPU-specific optimizations."""
        args = super().configure_args()

        # Disable SIMD optimizations that can cause illegal instruction errors
        # when running on CPUs that don't support them
        if self.spec.target.family == "x86_64":
            # Disable all SIMD optimizations to ensure portability
            args.extend([
                "--disable-sse2",
                "--disable-avx",
                "--disable-avx2",
                "--disable-avx-128-fma",
                "--disable-avx512",
                "--disable-altivec",
                "--disable-vsx",
            ])

        return args

    def setup_build_environment(self, env):
        """Set compiler flags to ensure generic x86_64 compilation."""
        super().setup_build_environment(env)

        # Force generic x86_64 compilation without CPU-specific optimizations
        # This ensures FFTW works on all x86_64 CPUs, not just the build machine
        if self.spec.target.family == "x86_64":
            # Set generic x86_64 target explicitly to avoid CPU-specific instructions
            env.append_flags("CFLAGS", "-march=x86-64 -mtune=generic")
            env.append_flags("CXXFLAGS", "-march=x86-64 -mtune=generic")
            env.append_flags("FFLAGS", "-march=x86-64 -mtune=generic")

