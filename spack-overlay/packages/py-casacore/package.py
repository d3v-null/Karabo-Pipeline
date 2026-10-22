from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import EnvironmentModifications, depends_on, license, maintainers, version


class PyCasacore(PythonPackage):
    """
    ska-sdp-spack recipe + a real version for setuptools-scm (see setup_build_environment).

    Python-casacore is a set of Python bindings for casacore, a c++
    library used in radio astronomy.
    """

    homepage = "https://github.com/casacore/python-casacore"
    url = (
        "https://github.com/casacore/python-casacore/"
        "archive/refs/tags/v3.6.1.tar.gz"
    )
    git = "https://github.com/casacore/python-casacore"

    maintainers("saliei")

    license("LPGL-3.0")

    # Since Python-casacore extracts its version from the .git tree, disable
    # caching. Spack omits the .git tree from cached sources.
    version("master", branch="master", no_cache=True)
    version(
        "3.7.1",
        tag="v3.7.1",
        commit="4772a710ba7884c10a8dfb312e9fd4bae3513588",
        no_cache=True,
    )
    version("3.6.1", tag="v3.6.1", no_cache=True)
    version(
        "3.5.2",
        sha256="ad70c8e08893eec928b3e38c099bda8863f5aa9d099fd00694ad2b0d48eba08f",
    )
    version(
        "3.5.1",
        sha256="a577233c7311f64a8048180ee82d6946fee16e0dce2976eb516784a32d8b9133",
    )
    version(
        "3.5.0",
        sha256="47ac85d47051074d64415414212c8c2cfcb49a2037f5c3d78f71ab5b162d1e8b",
    )
    version(
        "3.4.0",
        sha256="f654781292308de70c037981f5f7f5aeb02cf980a6f1367d1c294e7b4fca42ce",
    )

    depends_on("c")
    depends_on("cxx")
    depends_on("py-scikit-build-core+pyproject", type="build")
    depends_on("py-setuptools-scm", type="build")
    depends_on("py-setuptools", type="build")
    depends_on("boost+python", type="build")
    depends_on("cfitsio", type="build")
    depends_on("wcslib", type="build")
    depends_on("ninja", type="build")
    depends_on("cmake", type="build")

    depends_on("casacore+python", type=("build", "link"))

    # Resembles the dependencies in the project's pyproject.toml file.
    depends_on("py-six", type="run", when="@:3.6.1")
    depends_on("py-numpy", type="run")

    # Disable RPATH stripping on CMake install. scikit-build-core
    # encapsulation prevents spack to do that automatically
    def config_settings(self, _spec, _prefix):
        return {"cmake.define.CMAKE_INSTALL_RPATH_USE_LINK_PATH": "ON"}

    def flag_handler(self, name, flags):
        """
        Add C++17 flag for Apple Clang, which is the default compiler on macOS.
        """
        if self.spec.compiler.name == "apple-clang" and self.spec[
            "casacore"
        ].satisfies("@3.8.0:"):
            if name == "cxxflags":
                flags.append("-std=c++17")
        return (flags, None, None)

    def setup_build_environment(self, env: EnvironmentModifications) -> None:
        # Spack's shallow commit checkout has no tags, so setuptools-scm reports
        # 0.1.dev1+g<sha> and pip later "upgrades" it to a PyPI wheel.
        if not self.spec.satisfies("@master"):
            env.set("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYTHON_CASACORE", str(self.version))
