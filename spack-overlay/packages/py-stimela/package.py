from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, version


class PyStimela(PythonPackage):
    """stimela workflow framework; installed here for the scabha package it
    ships, which breizorro's command-line interface uses."""

    homepage = "https://github.com/caracal-pipeline/stimela"
    pypi = "stimela/stimela-2.1.4.tar.gz"

    license("GPL-2.0-only")

    version("2.1.4", sha256="27e72219229d387bf28957638972e32e8011fc71f61d02f71fbbc208c5bf3990")

    depends_on("python@3.9:3.13", type=("build", "run"))
    depends_on("py-hatchling", type="build")

    # What scabha imports (the breizorro path). stimela's metadata pins
    # pydantic<2, rich<14 and psutil<6; scabha only uses pydantic dataclasses
    # and ValidationError, which pydantic 2 keeps, and breizorro's
    # clickify_parameters path does not run pydantic validation, so these
    # are left unpinned to match the image. The `stimela` CLI's own deps
    # (munch, networkx, python-benedict, psutil) are not installed: only
    # scabha is supported here.
    depends_on("py-click@8.1.3:8", type="run")
    depends_on("py-dill@0.3.6:", type="run")
    depends_on("py-omegaconf@2.1:2", type="run")
    depends_on("py-pydantic", type="run")
    depends_on("py-pyparsing@3.0.9:3", type="run")
    depends_on("py-pyyaml", type="run")
    depends_on("py-rich@13.7:", type="run")
    depends_on("py-typeguard@4.2.1:4", type="run")
    depends_on("py-uritools@5:5", type="run")
