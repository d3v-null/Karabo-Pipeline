# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.packages.glib import package as builtin_glib


class Glib(builtin_glib.Glib):
    """Builtin glib with its test suite disabled (see MesonBuilder below)."""


class MesonBuilder(builtin_glib.MesonBuilder):
    def meson_args(self):
        args = super().meson_args()
        # glib's test resource generation fails with EPERM inside BuildKit sandboxes.
        if self.spec.satisfies("@2.74:"):
            args += ["-Dtests=false", "-Dinstalled_tests=false"]
        return args
