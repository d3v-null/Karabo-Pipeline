from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, version


class PyStimela(PythonPackage):
    """Stimela 2: framework for system-agnostic (radio astronomy)
    pipelines. The distribution also ships the 'scabha' schema/validation
    library used by QuartiCal."""

    homepage = "https://github.com/caracal-pipeline/stimela"
    pypi = "stimela/stimela-2.1.4.tar.gz"

    license("GPL-2.0-only")

    version(
        "2.1.4",
        sha256="27e72219229d387bf28957638972e32e8011fc71f61d02f71fbbc208c5bf3990",
    )

    depends_on("python@3.9:3.13", type=("build", "run"))
    depends_on("py-hatchling", type="build")

    depends_on("py-munch@2.5.0:2", type=("build", "run"))
    depends_on("py-omegaconf@2.1:2", type=("build", "run"))
    depends_on("py-click@8.1.3:8", type=("build", "run"))
    depends_on("py-pyparsing@3.0.9:3", type=("build", "run"))
    # Upstream pins pydantic<2, psutil<6 and rich<14. The image already
    # carries pydantic 2.10 / psutil 7 / rich 14 (Toil, cwltool, galaxy);
    # scabha's pydantic.dataclasses usage works on pydantic 2 (verified with
    # QuartiCal 0.2.6 config parsing), so the pins are relaxed by patch.
    depends_on("py-pydantic@1.10.2:", type=("build", "run"))
    depends_on("py-psutil@5.9.3:", type=("build", "run"))
    depends_on("py-rich@13.7.0:", type=("build", "run"))
    depends_on("py-dill@0.3.6:0.3", type=("build", "run"))
    depends_on("py-typeguard@4.2.1:4", type=("build", "run"))
    depends_on("py-uritools@5.0.0:5", type=("build", "run"))
    depends_on("py-python-benedict@0.34.1:0.34", type=("build", "run"))
    depends_on("py-networkx@3.0.0:", type=("build", "run"))

    patch("relax-pydantic-psutil-rich-pins.patch", when="@2.1.4")

    import_modules = ["stimela", "scabha"]
