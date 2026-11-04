from spack_repo.builtin.build_systems.python import PythonPackage

from spack.package import depends_on, filter_file, maintainers, version


class PyLofarFacetSelfcal(PythonPackage):
    """facetselfcal: direction-dependent (facet) self-calibration for LOFAR,
    MeerKAT, uGMRT and other interferometers, driving DP3 and WSClean.

    Installs the `facetselfcal`, `h5_merger`, `ds9facetgenerator`,
    `sub_sources_outside_region` and related entry points.
    """

    homepage = "https://github.com/rvweeren/lofar_facet_selfcal"
    git = "https://github.com/rvweeren/lofar_facet_selfcal.git"

    maintainers("d3v-null")

    # No license is declared upstream (no LICENSE file; CITATION.cff license field empty).

    # Upstream has no release tags; the pyproject version (21.0.0) plus the commit date.
    version("main", branch="main")
    version("21.0.0.20261030", commit="58e9cc5234b629a30c1de94739a5e336cb45d9ff")

    depends_on("python@3.9:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-wheel", type="build")

    # Imported when facetselfcal starts
    depends_on("py-numpy", type="run")
    depends_on("py-scipy", type="run")
    depends_on("py-astropy", type="run")
    depends_on("py-astroquery", type="run")
    depends_on("py-bdsf", type="run")
    depends_on("py-casacore", type="run")
    depends_on("py-joblib", type="run")
    depends_on("py-losoto", type="run")
    depends_on("py-matplotlib", type="run")
    depends_on("py-pandas", type="run")
    depends_on("py-psutil", type="run")
    depends_on("py-pyregion", type="run")
    depends_on("py-tables", type="run")
    # Imported by the facet, h5, plotting and source-selection code paths
    depends_on("py-lsmtool", type="run")
    depends_on("py-h5py", type="run")
    depends_on("py-shapely", type="run")
    depends_on("py-scikit-image", type="run")
    depends_on("py-requests", type="run")
    depends_on("py-tqdm", type="run")
    depends_on("py-regions", type="run")
    depends_on("py-pyvo", type="run")
    # Tools it runs or imports: DP3 (incl. its python module), WSClean, EveryBeam, aoflagger CLI
    depends_on("dp3+python", type="run")
    depends_on("wsclean", type="run")
    depends_on("everybeam+python", type="run")
    depends_on("aoflagger", type="run")
    # input_checks.inputchecker() refuses to start unless `breizorro` (mask making),
    # `taql` (casacore), `DP3` and `wsclean` are on PATH
    depends_on("py-breizorro", type="run")
    depends_on("casacore", type="run")

    def patch(self):
        # main.py and submods look up <package>/flagging_strategies/*.lua and
        # <package>/data/* (e.g. MeerKATlayout.csv) next to the installed
        # facetselfcal package, but pyproject only ships data/*.skymodel and
        # data/setjy/*, so a wheel install leaves them out.
        filter_file(
            r'facetselfcal = \["data/\*\.skymodel", "data/setjy/\*"\]',
            'facetselfcal = ["data/*", "data/setjy/*", "flagging_strategies/*.lua"]',
            "pyproject.toml",
        )
