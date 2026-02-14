from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import depends_on, version
import os
import re


class Lofartools(CMakePackage):
    """Collection of LOFAR-related tools for radio astronomy data processing,
    including model conversion, flagging, rendering, and image manipulation."""

    homepage = "https://gitlab.com/aroffringa/lofartools"
    git = "https://gitlab.com/aroffringa/lofartools.git"

    version(
        "master",
        branch="master",
        submodules=True,
        no_cache=True,
    )

    depends_on("c", type="build")
    depends_on("cxx", type="build")

    depends_on("casacore@3.5.0:")
    depends_on("cfitsio")
    depends_on("hdf5~mpi")
    depends_on("fftw")
    depends_on("boost+date_time+filesystem+system+test")
    depends_on("gsl")
    depends_on("libpng")
    depends_on("libdeflate")
    depends_on("wcslib")
    depends_on("git")
    depends_on("everybeam@0.5.1:", type=("build", "link", "run"))

    def patch(self):
        # Remove targets that use Deflate.h with 1.19+ API
        # (siscostman, siscoinfo, siscompress, unittests, check)
        cmake_file = os.path.join(self.stage.source_path, "CMakeLists.txt")
        with open(cmake_file, "r") as f:
            lines = f.readlines()
        out = []
        skip_targets = {
            "siscostman", "siscoinfo", "siscompress", "unittests", "check",
        }
        skip = False
        for line in lines:
            stripped = line.strip()
            # Detect start of a target we want to skip
            should_skip = False
            for t in skip_targets:
                if re.match(
                    rf"add_(executable|library|custom_target)\s*\(\s*{re.escape(t)}\b",
                    stripped,
                ):
                    should_skip = True
                    break
                if re.match(
                    rf"target_link_libraries\s*\(\s*{re.escape(t)}\b",
                    stripped,
                ):
                    should_skip = True
                    break
            if should_skip:
                out.append("# DISABLED (libdeflate compat): " + line)
                # If line doesn't end the statement, skip continuation
                if line.count("(") > line.count(")"):
                    skip = True
                continue
            if skip:
                out.append("# DISABLED (libdeflate compat): " + line)
                if ")" in line:
                    skip = False
                continue
            out.append(line)
        with open(cmake_file, "w") as f:
            f.writelines(out)

    def cmake_args(self):
        return [
            self.define("PORTABLE", True),
        ]
