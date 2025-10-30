# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *
from spack.pkg.builtin.pocl import Pocl as BuiltinPocl


class Pocl(BuiltinPocl):
    """Overlay to fix pocl ARM build issues and LLVM compatibility.

    Portable Computing Language (pocl) is an open source implementation
    of the OpenCL standard. This overlay adds ARM CPU detection and ensures
    compatibility with newer LLVM versions.
    """

    def cmake_args(self):
        """Add ARM-specific configuration to CMake args."""
        args = super().cmake_args()

        # Fix ARM CPU detection issues
        # pocl's LLVM.cmake fails to detect ARM CPUs automatically
        if self.spec.target.family in ("aarch64", "arm"):
            # Set a generic ARM CPU target that works across ARM variants
            if self.spec.target.family == "aarch64":
                args.append(self.define("LLC_HOST_CPU", "generic"))
            else:
                args.append(self.define("LLC_HOST_CPU", "generic"))

        return args

    def setup_build_environment(self, env):
        """Set up environment variables for the build."""
        super().setup_build_environment(env)

        # Help pocl find LLVM components on ARM
        if "+llvm" in self.spec:
            llvm_prefix = self.spec["llvm"].prefix
            env.set("LLVM_CONFIG", llvm_prefix.bin.join("llvm-config"))
