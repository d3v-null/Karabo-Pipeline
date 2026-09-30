from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyCacheout(PythonPackage):
    """cacheout: a caching library for Python (LRU/LFU/TTL caches)."""

    homepage = "https://github.com/dgilland/cacheout"
    pypi = "cacheout/cacheout-0.16.0.tar.gz"

    license("MIT")

    version(
        "0.16.0",
        sha256="ee264897cbaa089ae5f406da11952697d99fa7f3583cfab69fe8a00ff8e1952d",
    )

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")

    import_modules = ["cacheout"]
