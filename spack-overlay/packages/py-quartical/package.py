from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, license, patch, version


class PyQuartical(PythonPackage):
    """QuartiCal: fast and flexible calibration suite for radio
    interferometer data (Jones-chain, dask-based, from RATT)."""

    homepage = "https://github.com/ratt-ru/QuartiCal"
    pypi = "quartical/quartical-0.2.6.tar.gz"

    license("MIT")

    version(
        "0.2.6",
        sha256="039fa69f7951da1206f009d1c55074875bcda080207a7dbe7d9e21675883c7db",
    )

    depends_on("python@3.10:3.12", type=("build", "run"))
    depends_on("py-poetry-core", type="build")

    # Pins follow pyproject.toml of 0.2.6 (poetry). The image provides
    # numpy 2.2 / dask+distributed 2024.8.0 / xarray 2024.10.0 /
    # python-casacore 3.7.1 / astropy 6.1.0 / matplotlib 3.9.2, all inside
    # QuartiCal's ranges, so no QuartiCal-level pins had to be relaxed.
    depends_on("py-astro-tigger-lsm@1.7.2:1.7.3", type=("build", "run"))
    depends_on(
        "py-codex-africanus@0.4.1:0.4.3+dask+scipy+astropy+casacore",
        type=("build", "run"),
    )
    depends_on("py-colorama@0.4.6", type=("build", "run"))
    depends_on("py-columnar@1.4.1", type=("build", "run"))
    # dask[diagnostics] only adds bokeh for the profiler visualizer; the
    # ProgressBar QuartiCal uses is pure dask.
    depends_on("py-dask@2023.5.0:2024.10.0", type=("build", "run"))
    depends_on("py-dask-ms@0.2.23:0.2.27+s3+xarray+zarr", type=("build", "run"))
    depends_on("py-distributed@2023.5.0:2024.10.0", type=("build", "run"))
    depends_on("py-loguru@0.7.0:0.7.3", type=("build", "run"))
    depends_on("py-matplotlib@3.5.1:3.9.2", type=("build", "run"))
    depends_on("py-omegaconf@2.3.0", type=("build", "run"))
    depends_on("py-pytest@7.3.1:9.0.2", type=("build", "run"))
    depends_on("py-requests@2.31.0:2.32.5", type=("build", "run"))
    # Upstream wants ruamel.yaml>=0.17.26, but py-cwl-upgrader (Toil/CWL
    # stack) pins ruamel.yaml<=0.17.21; QuartiCal only uses plain YAML
    # load/dump, so the floor is relaxed to keep a single ruamel.yaml.
    depends_on("py-ruamel-yaml@0.17.6:0.19.1", type=("build", "run"))
    # QuartiCal imports scabha (schema_utils, cargo), shipped inside the
    # stimela 2 distribution.
    depends_on("py-stimela@2.0:", type=("build", "run"))
    depends_on("py-tbump@6.10.0:6.11.0", type=("build", "run"))

    patch("relax-ruamel-yaml-pin.patch", when="@0.2.6")

    import_modules = ["quartical", "quartical.config"]
