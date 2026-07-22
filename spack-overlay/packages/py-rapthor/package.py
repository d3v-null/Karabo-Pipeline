from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, version


class PyRapthor(PythonPackage):
    """Rapthor DDE pipeline.

    Rapthor is a pipeline for correcting direction-dependent effects in radio
    astronomy data, using multiple self-calibration cycles.
    """

    homepage = "https://git.astron.nl/RD/rapthor"
    git = "https://git.astron.nl/RD/rapthor.git"

    license("GPL-3.0-only", checked_by="gemmadanks")

    # Since Rapthor determines its version from the .git tree (using
    # setuptools_scm), disable caching.
    # Otherwise, Spack omits the .git tree from cached sources.
    version(
        "2.0.20250630",
        commit="86650e841bbbeb7b1af2c46595c879f4284e113a",
        no_cache=True,
    )
    version(
        "2.0.20250808",
        commit="d46dcbc1db3c7997dbc7ac5f84b2ecbe2a5c84d9",
        no_cache=True,
    )
    version(
        "2.0.20250915",
        commit="d46dcbc1db3c7997dbc7ac5f84b2ecbe2a5c84d9",
        no_cache=True,
    )
    version(
        "2.0.20251104",
        commit="683b8257d71be211a8111580c784e8041bce23a4",
        no_cache=True,
    )
    version(
        "2.0.20251106",
        commit="a3d18d8d2830ce058367eedc4b35bafe24646431",
        no_cache=True,
    )
    version("2.1", tag="v2.1", no_cache=True)
    version(
        "2.1.20251217",
        commit="e73d0eb77b918c84871f5e3ea02880f029cbd0d5",
        no_cache=True,
    )
    version(
        "2.1.20260203",
        commit="1b52818ff63bd056a29583e7b01506a3a9861008",
        no_cache=True,
    )

    version(
        "2.1.20260216",
        commit="3b47f4c32e1bd0c8c9aba70feb969ac65355889a",
        no_cache=True,
    )

    version(
        "2.1.20260219",
        commit="092a5db2c36025cfefb439048c9f38ac87b065d7",
        no_cache=True,
    )

    version(
        "2.1.20260320",
        commit="2197148801bb3d83bc5e150fa884d0434144b402",
        no_cache=True,
    )
    version(
        "2.1.20260409",
        commit="40c95787c447492d52981b8608111c628fc77b3f",
        no_cache=True,
    )
    version(
        "2.1.20260522",
        commit="3e4eca1967bb3d7420fc8672d28973aeed809a2e",
        no_cache=True,
    )
    version(
        "2.1.20260529",
        commit="908f83c9e75fa54d87718ab7dfcedf8137e8d093",
        no_cache=True,
    )
    version(
        "2.1.20260630",
        commit="01a81e11d75ce94ddd1b395d23ea9dca6be3a7d1",
        no_cache=True,
    )
    version(
        "2.1.20260710",
        commit="01a81e11d75ce94ddd1b395d23ea9dca6be3a7d1",
        no_cache=True,
    )

    version("master", branch="master", no_cache=True)

    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-setuptools@45:70", type="build")
    depends_on("py-setuptools-scm@6.2:+toml", type="build")
    depends_on("py-wheel", type="build")

    depends_on("py-astropy@6.1.0:", type=("build", "run"))
    depends_on("py-bdsf@1.12.0", type=("build", "run"), when="@:2.0.20250808")
    depends_on(
        "py-bdsf@1.13.0.20251010",
        type=("build", "run"),
        when="@2.0.20250915:2.1.20260320",
    )
    depends_on(
        "py-bdsf@1.13.0.20260409",
        type=("build", "run"),
        when="@2.1.20260409:2.1.20260709",
    )
    depends_on(
        "py-bdsf@1.14.1.20260710", type=("build", "run"), when="@2.1.20260710:"
    )
    depends_on("py-jinja2", type=("build", "run"))
    depends_on("py-losoto@2.4.3:", type=("build", "run"))
    depends_on(
        "py-lsmtool@1.6:1.6.2.0", type=("build", "run"), when="@:2.0.20250915"
    )
    depends_on(
        "py-lsmtool@1.6.2.20251104",
        type=("build", "run"),
        when="@2.0.20251104:2.0.20251106",
    )
    depends_on(
        "py-lsmtool@1.8.0.20251128",
        type=("build", "run"),
        when="@2.1:2.1.20260219",
    )
    depends_on(
        "py-lsmtool@1.8.0.20260407",
        type=("build", "run"),
        when="@2.1.20260409:2.1.20260506",
    )
    depends_on(
        "py-lsmtool@1.8.0.20260522", type=("build", "run"), when="@2.1.20260522"
    )
    depends_on(
        "py-lsmtool@1.8.0.20260605", type=("build", "run"), when="@2.1.20260529"
    )
    depends_on(
        "py-lsmtool@1.8.0.20260630", type=("build", "run"), when="@2.1.20260629:"
    )
    # matplotlib 3.10 removed the deprecated anchored_artists.AnchoredEllipse
    depends_on("py-matplotlib@:3.9", type=("build", "run"))
    depends_on("py-mocpy@0.18.0:", type=("build", "run"))
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-casacore@3.7.1:", type=("build", "run"))
    depends_on("py-python-dateutil", type=("build", "run"))
    depends_on("py-reproject", type=("build", "run"))
    depends_on("py-requests", type=("build", "run"))
    depends_on("py-rtree@1.4.0:", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))
    depends_on("py-shapely", type=("build", "run"))

    # Keep the nested Rapthor driver ABI-aligned with the Toil 9.3 WES
    # deployment that creates its Kubernetes worker pods.
    depends_on("karabo.py-toil@9.3.0:+cwl", type=("build", "run"))

    # Add run-time dependencies on other packages
    depends_on("aoflagger@3.4.0:", type="run")
    depends_on("dp3@6.4.1:", type="run")
    depends_on("wsclean@3.6.20250630:", type="run")
    depends_on("cfitsio+utils", type="run")  # Rapthor uses 'fpack' from cfitsio.

    patch("kubernetes-batch-system.patch", when="@2.1.20260630")
    patch("toil-runtime-options.patch", when="@2.1.20260630")
    # StreamFlow is an alternate CWL runner; SKA images use Toil/WES. Keep it
    # optional so `pip check` does not require an unused heavy dependency.
    patch("streamflow-optional.patch", when="@2.1.20260630")

    import_modules = [
        "rapthor",
        "rapthor.process",
    ]
