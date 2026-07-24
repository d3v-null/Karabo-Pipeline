from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, maintainers, version


class PySkaSdpIcal(PythonPackage):
    """
    SKA SDP Self-Calibration Pipeline using Rapthor.
    """

    homepage = (
        "https://gitlab.com/ska-telescope/sdp/"
        "science-pipeline-workflows/ska-sdp-ical"
    )
    git = homepage + ".git"

    maintainers("gemmadanks", "mnijhuis-tos", "astromancer")

    license("BSD-3-Clause")
    version("main", branch="main")
    version("0.7.0", tag="0.7.0")
    version("0.6.1", tag="0.6.1")
    version("0.6.0", tag="0.6.0")
    version("0.5.2", tag="0.5.2")
    version("0.5.1", tag="0.5.1")
    version("0.4.0", tag="0.4.0")
    version("0.3.1", tag="0.3.1")
    version("0.3.0", tag="0.3.0")
    version("0.2.0", tag="0.2.0")
    version("0.1.0", tag="0.1.0")

    # Basic Python dependencies.
    depends_on("python@3.10:3.13", type=("build", "run"))
    depends_on("py-poetry-core@2", type="build")

    # Python dependencies.
    # Each ICAL version uses a specific Rapthor version.
    depends_on("karabo.py-rapthor@2.1.20260630", type="run", when="@0.7.0")
    depends_on("karabo.py-rapthor@2.1.20260529", type="run", when="@0.6.1")
    depends_on("karabo.py-rapthor@2.1.20260522", type="run", when="@0.6.0")
    depends_on("karabo.py-rapthor@2.1.20260409", type="run", when="@0.5.2")
    depends_on("karabo.py-rapthor@2.1.20260320", type="run", when="@0.5.1")
    depends_on("karabo.py-rapthor@2.1.20260219", type="run", when="@0.4.0")
    depends_on("karabo.py-rapthor@2.1.20260216", type="run", when="@0.3.1")
    depends_on("karabo.py-rapthor@2.1.20260203", type="run", when="@0.3.0")
    depends_on("karabo.py-rapthor@2.1.20251217", type="run", when="@0.2.0")
    depends_on("karabo.py-rapthor@2.1", type="run", when="@0.1.0")
