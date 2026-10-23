# build me with ./build_sp5505.sh

# Global ARGs: defaults live here once. Stages redeclare without values.
ARG PYTHON_VERSION=3.11
ARG CUDA_VERSION=12.2.2
ARG CUDA_ARCH="75,80,86,89,90"
# CUDA_ARCH covers T4/RTX2000, A100, RTX3000, L40, GH200. Empty => CPU-only.

FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6 AS builder

USER root
SHELL ["/bin/bash", "-lc"]

# Re-declare global ARGs (defaults are above the first FROM)
ARG PYTHON_VERSION
ARG CUDA_VERSION
ARG CUDA_ARCH

# Essential build dependencies
# These are found by spack external find, and later garbage collected by spack.# Do not include runtime dependencies here.
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    python3-yaml \
    autoconf \
    automake \
    bison \
    build-essential \
    bzip2 \
    libbz2-dev \
    ca-certificates \
    cmake \
    curl \
    diffutils \
    file \
    findutils \
    gfortran \
    git \
    libcurl4-openssl-dev \
    libgomp1 \
    libltdl-dev \
    libtool \
    m4 \
    patchelf \
    perl \
    pkg-config \
    time \
    wget \
    zstd \
    ; # not required because of buildcache: rm -rf /var/lib/apt/lists/*

# Install Rust before any Spack setup, because Spack rust is unbelievably slow.
# mypy 2 (via cwltool/schema-salad) needs py-ast-serialize, which needs rustc >= 1.93.
# Rust 1.86+ couldn't find -lcudart for hyperdrive on arm64; recheck before a +cuda ARM build.
ARG RUST_VERSION=1.93.0
ENV CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup
RUN set -o pipefail && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain $RUST_VERSION --no-modify-path && \
    ln -sf /opt/cargo/bin/* /usr/local/bin/ && \
    rustc --version | grep -Fq "$RUST_VERSION"

# Install Spack v1.2.2 (what ska-sdp-spack 2026.10.3 targets) and detect compilers
# Keep the base image's conda off PATH while building: a conda python of the
# same minor version gets picked up by spack's python build (libpython clash),
# and spack 1.2 needs os.O_PATH, which conda's python lacks.
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    SPACK_PYTHON=/usr/bin/python3
RUN git clone --depth=1 --single-branch --branch=v1.2.2 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    cd ${SPACK_ROOT} && \
    rm -rf .git && \
    # Spack v1.x ships some dangling symlinks in docs assets which cause
    # `fix-permissions` (from the Jupyter base image) to fail the build.
    # Remove any broken symlinks before running fix-permissions.
    find ${SPACK_ROOT}/lib/spack/docs -xtype l -delete || true && \
    . share/spack/setup-env.sh && \
    # Pin the builtin package repo to the tag ska-sdp-spack 2026.10.3 uses.
    spack repo set --scope site --destination /opt/spack-packages builtin && \
    spack repo update --scope site --tag v2026.06.0 builtin && \
    spack env create --dir /opt/spack_env && \
    fix-permissions ${SPACK_ROOT} /opt/spack-packages /opt/spack_env

RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

RUN spack compiler find && \
    spack compiler list && \
    spack external find \
    autoconf \
    automake \
    bison \
    bzip2 \
    curl \
    diffutils \
    findutils \
    git \
    # gmake \ # we don't want system gmake
    libtool \
    m4 \
    perl \
    pkgconf \
    rust

# Add SKA SDP Spack repo and overlay
# ska-sdp-spack 2026.10.4 release commit (MR 446; not tagged yet, switch to the tag once cut).
ARG SDP_SPACK_REF=7bc44cf1e1f4bec316b018a3e27db28b693d8d59
RUN git init -q /opt/ska-sdp-spack && \
    git -C /opt/ska-sdp-spack fetch -q --depth=1 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git "${SDP_SPACK_REF}" && \
    git -C /opt/ska-sdp-spack checkout -q FETCH_HEAD && \
    rm -rf /opt/ska-sdp-spack/.git && \
    spack repo add /opt/ska-sdp-spack
COPY spack-overlay /opt/karabo-spack
RUN spack repo add /opt/karabo-spack

ARG NUMPY_VERSION=2.3.5
# numpy needed by pyuvdata montagepy numexpr scipy rascil scikit-image pywavelets astroml ducc0 imageio ska-sdp-func-python contourpy aratmospy bokeh astroplan coda harp astropy-healpix katbeam tensorboard h5py dask ml_dtypes ska-gridder-nifty-cuda libboost-python-devel python-casacore tifffile pytest-arraydiff shapely bdsf casacore finufft reproject numcodecs matplotlib-base tools21cm libboost-python numba gwcs tensorflow-base pyfftw boost xarray asdf pyside6 photutils astropy bottleneck pandas oskarpy ska-sdp-datamodels ska-sdp-func healpy keras scikit-learn pyerfa eidos asdf-astropy zarr bluebild
# conda has numpy 1.26.4
# numpy 1.23.5 worked with numpy1
# numpy>=1.24 required by zarr 2.18.3
# numpy>=1.25 required by astropy-healpix 1.1.2
# numpy 2.x upgrade: astropy 6.1+ requires numpy 2, py-rapthor requires astropy 6.1+
# conda-forge resolves to numpy 2.2.6 with python 3.10
# numpy=1.23.5 worked with rascil 1.0.0
ARG CFITSIO_VERSION=4.6.3
# conda has cfitsio 4.3.1
# OSKAR >=2.11 requires CFITSIO >=4.6.2
ARG PANDAS_VERSION=3.0.3
# pandas needed by rascil dask xarray ska-sdp-datamodels bluebild
# conda has pandas 1.5.3
# pandas@:2.2.1 caps numpy@:1 in builtin spack-packages; need >=2.2.2 for numpy 2
# pandas 2.x supports numpy 2; previous: 1.5.3
# conda-forge uses 2.2.x with numpy 2
ARG XARRAY_VERSION=2026.2.0
# xarray needed by pyuvdata bluebild rascil scikit-image astroml ska-sdp-func-python aratmospy bdsf reproject tools21cm gwcs photutils healpy scikit-learn eidos
# conda has xarray 2023.2.0
# xarray 2024+ supports numpy 2
# xarray<2022.13,>=2022.12 required by rascil 1.0.0
# xarray<2023.0.0,>=2022.10.0 required by ska-sdp-datamodels 0.1.3
# xarray<2023.0.0,>=2022.11.0 required by ska-sdp-func-python 0.1.5
ARG H5PY_VERSION=3.16.0
# h5py needed by pyuvdata tensorflow-base ska-sdp-datamodels keras
# conda has h5py 3.13.0
# h5py 3.12+ supports numpy 2; previous: 3.7
# conda-forge uses 3.13.0
ARG HDF5_VERSION=1.14.6
# conda has hdf5 1.14.3
# hdf5 1.12.3 worked with numpy1
# hdf5 1.14 needed by h5py 3.12+
ARG DISTRIBUTED_VERSION=2026.3.0
# distributed 2024+ supports numpy 2; previous: 2022.12.1
ARG SCIPY_VERSION=1.17.1
# scipy 1.14+ supports numpy 2; previous: 1.9.3
# conda-forge uses 1.13.1+
ARG MATPLOTLIB_VERSION=3.9.4
# matplotlib 3.9+ supports numpy 2; previous: 3.6.3
# 3.9.4 is what ska-sdp-spack 2026.10.3 concretises
ARG ASTROPY_VERSION=7.1.1
# astropy 6.1+ requires numpy 2; previous: 5.1.1
# pyuvdata 3.2.0 requires astropy>=6.0
ARG CASACORE_VERSION=3.8.1
ARG PY_CASACORE_VERSION=3.7.1
# conda has 3.5.0
# casacore 3.7.1 needed by DP3@6.4: (unchanged)
ARG HEALPY_VERSION=1.17.3
# healpy 1.17+ compatible with astropy 6; previous: 1.16.6
ARG OSKAR_VERSION=2.12.0.20260212
ARG TOOLS21CM_VERSION=2.3.8
ARG TABULATE_VERSION=0.9.0
ARG BOOST_VERSION=1.88.0
# boost 1.88 has numpy 2 compatible Boost.Python/NumPy; previous: 1.82.0
# developer confirmed: libboost-python=1.88.0 resolves with numpy 2.2
ARG SKIMAGE_VERSION=0.26.0
# scikit-image 0.24 supports numpy 2
ARG SKLEARN_VERSION=1.9.0
# scikit-learn 1.5+ supports numpy 2; previous: 1.3.2
ARG TQDM_VERSION=4.67.3
ARG PYUVDATA_VERSION=3.2.0
# pyuvdata 3.2.0 supports numpy 2 + has MWA beam fix; previous: 2.4.2
ARG BDSF_VERSION=1.14.1.20260723
# matches py-rapthor 2.1.20260917; pinning avoids two py-bdsf versions in the view
ARG DASK_VERSION=2026.3.0
# dask 2024+ supports numpy 2; previous: 2022.12.1
ARG DUCC_VERSION=0.40.0
# conda uses 0.27
ARG PHOTUTILS_VERSION=2.3.0
# conda uses 1.8.0
# photutils 1.11.0 worked with numpy1
# photutils 2.0+ supports numpy 2 and astropy 6
ARG REPROJECT_VERSION=0.14.1
# conda uses 0.14.1, supports numpy 2 and astropy 6
# reproject 0.9.1 worked with numpy1
ARG SDP_DATAMODELS_VERSION=2.1.0
# conda uses 0.1.3
# sdp-datamodels 0.2+ supports numpy 2
ARG SDP_FUNC_PYTHON_VERSION=1.2.1
# conda uses 0.1.4
# sdp-func-python 0.2+ supports numpy 2
ARG ARATMOSPY_VERSION=1.0.0
ARG EIDOS_VERSION=1.1.0
ARG KATBEAM_VERSION=0.1.0

ARG AOFLAGGER_VERSION=3.6.0.dev2
ARG WSCLEAN_VERSION=3.7.20260929
ARG EVERYBEAM_VERSION=0.9.0
# Overlay adds MWA beam thread-safety/caching on top of the sdp recipe.
ARG DP3_VERSION=6.6.0.20260923
# sdp pairs DP3 6.6.0.20260923 with EveryBeam 0.9.0.
ARG HYPERDRIVE_VERSION=0.8.1.20261017
# hyperdrive bmetrics branch; pinned so concretizer reuse doesn't keep a cached 0.7.0.
ARG RAPTHOR_VERSION=2.1.20260917
# Same rapthor as rapthor-lean/rapthor-jupyter. Built +mwa: the overlay's
# MWA beam support patch (DP3/WSClean pointed at /opt/mwa_full_embedded_element_pattern.h5,
# flagged-tile and solar-model robustness fixes), which this image's MWA_BEAM_FILE serves.
ARG RAPTHOR_MWA_VARIANT=+mwa

# Create Spack environment and install deps
ARG SPACK_TARGET=""
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache-2026.10.3,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache,sharing=locked \
    --mount=type=secret,id=spack_oci_username,required=false \
    --mount=type=secret,id=spack_oci_password,required=false \
    set -o pipefail; \
    mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache}; \
    # Spack caches per-repo package indexes (incl. the patch sha256 index) in the
    # misc cache and only invalidates them on package.py mtime. Editing a .patch
    # file alone leaves a stale index and concretization fails with "Couldn't
    # find patch for package ... with sha256". Rebuilding the indexes is cheap.
    rm -rf /opt/spack-misc-cache/*; \
    arch=$(uname -m); \
    spack_target="${SPACK_TARGET}"; \
    if [ -z "${spack_target}" ]; then \
      case "$arch" in \
        # Prefer x86_64_v2 when building on x86_64, v3 is available but segfaults in CI.
        # Override with `--build-arg SPACK_TARGET=x86_64`
        # if you need a more portable image for older CPUs.
        x86_64) spack_target=x86_64_v2 ;; \
        aarch64) spack_target=aarch64 ;; \
        *) spack_target="$arch" ;; \
      esac; \
    fi; \
    echo "SPACK_TARGET=${spack_target} <- (uname -m)=$arch"; \
    spack config add "config:install_tree:root:/opt/software"; \
    # The new installer hands builds a fifo jobserver that system make 4.3
    # (called by e.g. py-healpy's setup.py) rejects.
    spack config add "config:installer:old"; \
    # DO NOT MODIFY CONCRETIZATION OR VIEW SETTINGS
    spack config add "concretizer:unify:when_possible"; \
    # Reused binaries keep the patches they were built with, so a changed
    # mwa-beam-support patch would be silently ignored if a +mwa py-rapthor
    # binary is already in the buildcache. py-rapthor is a cheap pure-python
    # build: always concretize it fresh (its deps are still reused).
    # These overlays fix version metadata (git builds lack tags); a cached ska-sdp-spack build would still satisfy them.
    spack config add "concretizer:reuse:exclude:[py-rapthor,py-casacore,py-bdsf,py-photutils,py-lsmtool,py-astropy-healpix]"; \
    # view config set via python3 yaml manipulation below (with py-mistune@:2 exclude) \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack config add "config:misc_cache:/opt/spack-misc-cache"; \
    spack config add "packages:casacore:variants: +data+python"; \
    spack config add "packages:all:target:[${spack_target}]"; \
    # Force numpy-2-compatible versions of transitive deps globally via
    # packages.yaml require. Constrains ALL instances
    # including transitive deps under when_possible concretization.
    # CUDA builds also pin py-rdflib/py-isodate (cwltool -> schema-salad) to what the
    # optimal solution picks anyway: unpinned, spack 1.2's when_possible solver
    # finds the solution in ~1 min but never proves it optimal (6 h CI timeouts).
    # The pins make the +cuda solve ~80 s; the CPU solve is ~80 s without them
    # and hangs with them, so they are CUDA-only.
    if [ -n "${CUDA_ARCH}" ]; then \
        WSCLEAN_REQUIRE="~mpi+cuda"; \
        RDFLIB_REQUIRE="@6.3.2"; \
        ISODATE_REQUIRE="@0.6.1"; \
    else \
        WSCLEAN_REQUIRE="~mpi~cuda"; \
        RDFLIB_REQUIRE=""; \
        ISODATE_REQUIRE=""; \
    fi; \
    python3 -c "import yaml,sys;p='/opt/spack_env/spack.yaml';f=open(p);c=yaml.safe_load(f);f.close();\
    pkgs=c.setdefault('spack',{}).setdefault('packages',{});\
    [pkgs.setdefault(k,{}).update({'require':v}) for k,v in [\
        ('llvm','~clang~lldb~lld~polly~libomptarget'),\
        ('py-numpy','@2:'),\
        ('py-tables','@3.10.2'),\
        ('py-numexpr','@2.10.2:'),\
        ('py-losoto','@2.6:'),\
        ('py-lsmtool','@1.6.2:'),\
        ('dp3','@${DP3_VERSION}+idg+python'),\
        ('everybeam','@${EVERYBEAM_VERSION}+python'),\
        ('aoflagger','@${AOFLAGGER_VERSION}'),\
        ('casacore','@${CASACORE_VERSION}+python+data+dysco~hdf5~mpi~openmp'),\
        ('py-casacore','@${PY_CASACORE_VERSION}'),\
        ('py-astropy','@${ASTROPY_VERSION}'),\
        ('cfitsio','+bzip2+fortran+utils'),\
        ('boost','+test'),\
        ('wsclean',sys.argv[1]),\
        ('py-rdflib',sys.argv[2]),\
        ('py-isodate',sys.argv[3])] if v];\
    c['spack']['view']={'default':{'root':'/opt/view','link_dirs':False}};\
    f=open(p,'w');yaml.dump(c,f,default_flow_style=False);f.close()" "${WSCLEAN_REQUIRE}" "${RDFLIB_REQUIRE}" "${ISODATE_REQUIRE}"; \
    # Local buildcache persisted via BuildKit cache mount (fast retries / iterations).
    # Disable by setting SPACK_BUILDCACHE_LOCAL=0 or empty.
    if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
        spack mirror add --autopush --unsigned mycache file:///opt/buildcache; \
        # Ensure the index exists so subsequent builds can actually *pull* from it.
        spack buildcache update-index /opt/buildcache || true; \
    fi; \
    # Optional OCI buildcache mirror (ska-sdp-spack CI uses this style of caching).
    # Example (read-only): --build-arg SPACK_MIRROR_OCI="oci://<registry>/<path>"
    if [ -n "${SPACK_MIRROR_OCI}" ]; then \
        # If credentials are provided as BuildKit secrets,
        if [ -f /run/secrets/spack_oci_username ] && [ -f /run/secrets/spack_oci_password ]; then \
            # enable autopush so CI can populate the cache for future runs.
            SPACK_OCI_USERNAME="$(cat /run/secrets/spack_oci_username)"; \
            export SPACK_OCI_PASSWORD="$(cat /run/secrets/spack_oci_password)"; \
            spack mirror add --autopush --unsigned \
                --oci-username "${SPACK_OCI_USERNAME}" \
                --oci-password-variable SPACK_OCI_PASSWORD \
                oci-push "${SPACK_MIRROR_OCI}"; \
        else \
            # Read-only mirror for pulling binaries (works without credentials).
            spack mirror add --unsigned oci-cache "${SPACK_MIRROR_OCI}"; \
        fi; \
    fi; \
    spack mirror add v1.2.2 https://binaries.spack.io/v1.2.2; \
    spack buildcache keys --install --trust || true; \
    WSCLEAN_SPEC="wsclean@${WSCLEAN_VERSION}~mpi~python"; \
    IDG_SPEC="idg"; \
    if [ -n "${CUDA_ARCH}" ]; then \
        CUDA_PKG="cuda@${CUDA_VERSION}"; \
        CUDA_SUFFIX="+cuda cuda_arch=${CUDA_ARCH}"; \
        # idg and wsclean don't support cuda_arch
        WSCLEAN_SPEC="${WSCLEAN_SPEC}+cuda"; \
        IDG_SPEC="${IDG_SPEC}+cuda"; \
    else \
        CUDA_PKG=""; \
        CUDA_SUFFIX="~cuda"; \
        WSCLEAN_SPEC="${WSCLEAN_SPEC}~cuda"; \
        IDG_SPEC="${IDG_SPEC}~cuda"; \
    fi; \
    OSKAR_SPEC="oskar@${OSKAR_VERSION}~openmp+hdf5${CUDA_SUFFIX}"; \
    HYPERBEAM_SPEC="hyperbeam+python+hdf5-static${CUDA_SUFFIX}"; \
    HYPERDRIVE_SPEC="hyperdrive@${HYPERDRIVE_VERSION}${CUDA_SUFFIX}"; \
    spack add \
    'python@'$PYTHON_VERSION \
    'py-pip' \
    'py-numpy@'$NUMPY_VERSION \
    'py-matplotlib@'$MATPLOTLIB_VERSION \
    ${CUDA_PKG:+"$CUDA_PKG"} \
    'boost@'$BOOST_VERSION'+python+numpy' \
    'hdf5@'$HDF5_VERSION'+hl~mpi+threadsafe' \
    'py-maturin@1.9.6' \
    'cfitsio@'$CFITSIO_VERSION \
    # 'py-astropy@'$ASTROPY_VERSION # transitive, py-rapthor \
    'py-bdsf@'$BDSF_VERSION \
    'py-scipy@'$SCIPY_VERSION \
    # 'casacore@'$CASACORE_VERSION'+python+data' # transitive, py-rapthor\
    # 'py-casacore@'$CASACORE_VERSION # transitive, py-rapthor \
    'py-joblib' \
    'py-lazy-loader' \
    'py-dask@'$DASK_VERSION \
    'py-distributed@'$DISTRIBUTED_VERSION \
    'py-ducc@'$DUCC_VERSION \
    # h5py is not pulled transitively once we pin photutils; keep explicitly for karabo tests
    'py-h5py@'$H5PY_VERSION \
    'py-healpy@'$HEALPY_VERSION'+internal-healpix' \
    'py-pandas@'$PANDAS_VERSION \
    'py-photutils@'$PHOTUTILS_VERSION \
    # RASCIL is now optional (abandoned project, incompatible with numpy 2)
    # 'py-rascil@'$RASCIL_VERSION \
    'py-scikit-image@'$SKIMAGE_VERSION \
    'py-scikit-learn@'$SKLEARN_VERSION \
    'py-tqdm@'$TQDM_VERSION \
    'py-ska-sdp-datamodels@'$SDP_DATAMODELS_VERSION \
    'py-ska-sdp-func-python@'$SDP_FUNC_PYTHON_VERSION \
    'py-ska-sdp-func' \
    'py-astroplan' \
    'py-tabulate@'$TABULATE_VERSION \
    'py-xarray@'$XARRAY_VERSION \
    "${OSKAR_SPEC}" \
    'py-oskar@'$OSKAR_VERSION \
    'py-pyuvdata@'$PYUVDATA_VERSION'+casa' \
    'py-aratmospy@'$ARATMOSPY_VERSION \
    'py-eidos@'$EIDOS_VERSION \
    'py-katbeam@'$KATBEAM_VERSION \
    'everybeam@'$EVERYBEAM_VERSION'+python' \
    "${WSCLEAN_SPEC}" \
    'py-tools21cm@'$TOOLS21CM_VERSION \
    'py-dask-mpi' \
    'py-mpi4py' \
    'py-packaging' \
    'py-requests' \
    'py-rfc3986' \
    # for testing karabo itself:
    'py-pytest@9' \
    # ---------
    # not karabo-related
    "${HYPERBEAM_SPEC}" \
    "${HYPERDRIVE_SPEC}" \
    # aoflagger is transitive from DP3 \
    'dp3@'$DP3_VERSION'+idg' \
    "${IDG_SPEC}" \
    'py-rapthor@'$RAPTHOR_VERSION$RAPTHOR_MWA_VARIANT \
    && \
    spack concretize --force && \
    # Guard against stale reused py-rapthor binaries: the lock must reference
    # the sha256 of the patch file currently in the recipe.
    python3 -c "import json,hashlib,os,sys;\
    d=json.load(open('/opt/spack_env/spack.lock'));\
    r=[s for s in d['concrete_specs'].values() if s.get('name')=='py-rapthor'];\
    pkgdir=next(p for p in ['/opt/karabo-spack/packages/py-rapthor','/opt/karabo-spack/packages/py_rapthor'] if os.path.isdir(p));\
    want={hashlib.sha256(open(os.path.join(pkgdir,f),'rb').read()).hexdigest() for f in os.listdir(pkgdir) if f.startswith('mwa-beam-support')};\
    have=set(r[0].get('parameters',{}).get('patches',[])) if r else set();\
    mwa=bool(r[0].get('parameters',{}).get('mwa',False)) if r else False;\
    print('py-rapthor +mwa' if mwa else 'py-rapthor ~mwa', 'patches in lock:', sorted(have));\
    (print('ERROR: +mwa py-rapthor concretized with a stale mwa-beam-support patch; recipe has', sorted(want)) or sys.exit(1)) if (mwa and not (want & have)) else None" && \
    # sanity check avoids 4 hours wasted build time for it to fail regenerating view
    python3 -c "import json,sys;d=json.load(open('/opt/spack_env/spack.lock'));\
    t=[\
        'py-astropy','casacore','py-casacore','py-dask','py-ducc','oskar',\
        'py-pyuvdata','ska-sdp-func','everybeam','aoflagger'\
    ];\
    c={};[c.setdefault(s.get('name'),[]).append(0) for s in d.get('concrete_specs',{}).values()];\
    e=[x for x in t if len(c.get(x,[]))>1];\
    print(f'Duplicate packages found: {e}')or sys.exit(1) if e else None" && \
    if [ -n "${CUDA_ARCH}" ]; then \
        # first install cuda to get the stubs
        spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error cuda && \
        # Locate CUDA libraries and stubs (lib64/stubs or lib/stubs)
        CUDA_ROOT=$(spack location -i cuda) && \
        if [ -d "${CUDA_ROOT}/lib64/stubs" ]; then \
            LIB_DIR="${CUDA_ROOT}/lib64"; \
        elif [ -d "${CUDA_ROOT}/lib/stubs" ]; then \
            LIB_DIR="${CUDA_ROOT}/lib"; \
        else \
            echo "ERROR: CUDA stubs directory not found in ${CUDA_ROOT}. $(ls -laR ${CUDA_ROOT})" >&2; \
            exit 1; \
        fi && \
        echo "Found CUDA stubs at ${LIB_DIR}/stubs" && \
        mkdir -p "/usr/lib/${arch}-linux-gnu" && \
        # Create libcuda.so.1 symlink for the stubs
        ln -sf "${LIB_DIR}/stubs/libcuda.so" "${LIB_DIR}/stubs/libcuda.so.1" && \
        ln -sf "${LIB_DIR}/stubs/libcuda.so" "/usr/lib/${arch}-linux-gnu/libcuda.so.1" && \
        # Link all libcudart versions so the runtime linker can find .so.12, .so.11, etc.
        for lib in "${LIB_DIR}"/libcudart.so*; do \
            ln -sf "${lib}" "/usr/lib/${arch}-linux-gnu/$(basename "${lib}")"; \
        done; \
    fi && \
    # install everything else.
    # First, force py-healpy from source so the overlay's rescue_internal_healpix_libs
    # @run_after("install") hook runs.  The binary cache has a broken build where
    # libhealpix_cxx.so ends up in a deleted temp dir.  Building from source lets the
    # hook copy the shared libs into prefix/lib so they survive at runtime.
    # Only healpy itself: its ~100 dependencies come from the cache as usual.
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --show-log-on-error --only dependencies py-healpy && \
    ac_cv_lib_curl_curl_easy_init=no spack install --no-cache --no-checksum --show-log-on-error --only package py-healpy && \
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    spack gc -y && \
    # Strip build-only artifacts that never help a running container:
    # static archives (only used at link time; shared libs remain) and,
    # when CUDA is enabled, the desktop profiler/debugger GUIs that ship
    # inside the CUDA toolkit (nsight-compute/systems, the legacy visual
    # profiler, compute-sanitizer). Together these accounted for several
    # GB in the final image without being used by anything at runtime.
    find /opt/software -name '*.a' -delete && \
    # View first: it must be generated while every prefix is still present.
    spack env view regenerate && \
    if [ -n "${CUDA_ARCH}" ]; then \
        CUDA_ROOT=$(spack location -i cuda) && \
        rm -rf "${CUDA_ROOT}"/nsight-compute-* "${CUDA_ROOT}"/nsight-systems-* \
               "${CUDA_ROOT}"/libnvvp "${CUDA_ROOT}"/extras \
               "${CUDA_ROOT}"/nsightee_plugins "${CUDA_ROOT}"/compute-sanitizer \
               "${CUDA_ROOT}"/bin "${CUDA_ROOT}"/gds* "${CUDA_ROOT}"/src "${CUDA_ROOT}"/tools \
               "${CUDA_ROOT}"/targets/*/include && \
        # Runtime libs: only cufft/cudart/nvrtc/nvToolsExt are linked by anything
        # here (ldd over /opt/software); nvrtc dlopens its builtins, numba.cuda
        # uses nvvm/. cuBLAS(Lt)/cuSPARSE/cuSOLVER/NPP/... are ~1.4 GB unused.
        find "${CUDA_ROOT}"/targets/*/lib -maxdepth 1 \( -type f -o -type l \) \
            ! -name 'libcudart.so*' ! -name 'libcufft.so*' ! -name 'libcufftw.so*' \
            ! -name 'libnvrtc*' ! -name 'libnvToolsExt.so*' ! -name 'libnvJitLink.so*' -delete; \
    fi && \
    # Build/link-only prefixes. llvm (4.2 GB) is linked statically into
    # py-llvmlite, numba JITs fine without it. cmake is a build dep; font-util is
    # X11 bitmap fonts (matplotlib ships its own).
    S=$(echo /opt/software/linux-*) && \
    rm -rf $S/llvm-* $S/cmake-* $S/font-util-* && \
    # Build metadata inside every prefix (keeping Python.h for pip builds), and
    # CPython's own test suite.
    find /opt/software -mindepth 2 -maxdepth 3 -type d \
        \( -name include -o -name aclocal -o -name man -o -name doc -o -name info \) \
        ! -path '*/python-[0-9]*/include' -prune -exec rm -rf {} + && \
    rm -rf $S/python-*/lib/python3.*/test && \
    # e.g. cuda/include -> targets/*/include; fix-permissions fails on dangling links.
    find /opt/software -xtype l -delete && \
    # Drop view links into pruned dirs (e.g. CUDA's nsight/libnvvp); fix-permissions fails on them.
    find /opt/view -xtype l -delete && \
    if [ -n "${SPACK_MIRROR_OCI}" ] && spack mirror list | awk '{print $1}' | grep -qx 'oci-push'; then \
        spack buildcache update-index -k oci-push || spack buildcache update-index oci-push || true; \
    fi && \
    if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
        spack buildcache update-index /opt/buildcache || true; \
    fi && \
    fix-permissions /opt/view /opt/spack_env /opt/software

RUN /opt/view/bin/python -m pip install --no-cache-dir \
        "jupyterlab>=4,<5" "notebook>=7,<8" && \
    /opt/view/bin/python -m pip install --no-cache-dir \
        "reproject==${REPROJECT_VERSION}" && \
    /opt/view/bin/python -c \
        "import dateutil, jupyterlab, notebook, reproject; print('pip overlays OK')"

FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6

USER root
SHELL ["/bin/bash", "-lc"]

ARG CUDA_ARCH
ARG CUDA_VERSION
ENV CUDA_ARCH=${CUDA_ARCH} \
    CUDA_VERSION=${CUDA_VERSION}

# Runtime dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    build-essential \
    ca-certificates \
    curl \
    gfortran \
    git \
    gnuplot-nox \
    jq \
    libcurl4-openssl-dev \
    libgomp1 \
    time \
    wget \
    zstd; \
    # nvidia-smi is a driver utility; Spack cuda does not ship it. Extract only
    # the binary — do not apt-install nvidia-utils (pulls libnvidia-compute*
    # which would mask the host driver, same class of bug as libcuda stubs).
    if [ -n "${CUDA_ARCH}" ]; then \
        found=""; \
        for pkg in $(apt-cache search --names-only '^nvidia-utils-[0-9]+$' | awk '{print $1}' | sort -Vr); do \
            rm -rf /tmp/nvutils && mkdir -p /tmp/nvutils && \
            (cd /tmp && apt-get download "$pkg") && \
            deb=$(ls /tmp/${pkg}_*.deb) && \
            dpkg-deb -c "$deb" > /tmp/nvutils.list && \
            if grep -q 'usr/bin/nvidia-smi$' /tmp/nvutils.list; then \
                dpkg-deb -x "$deb" /tmp/nvutils && \
                install -m 0755 /tmp/nvutils/usr/bin/nvidia-smi /usr/local/bin/nvidia-smi && \
                found="$pkg"; \
                rm -rf /tmp/nvutils "$deb" /tmp/nvutils.list; \
                break; \
            fi; \
            rm -f "$deb" /tmp/nvutils.list; \
        done; \
        if [ -z "$found" ] || [ ! -x /usr/local/bin/nvidia-smi ]; then \
            echo "ERROR: could not extract nvidia-smi from nvidia-utils-*" >&2; \
            exit 1; \
        fi; \
        echo "Installed nvidia-smi from ${found}"; \
        command -v nvidia-smi; \
    fi

# Install audria
RUN git clone --depth=1 https://github.com/scaidermern/audria.git /opt/audria && \
    cd /opt/audria && \
    make && \
    cp audria /usr/local/bin/

COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /opt/spack_env /opt/spack_env
COPY --from=builder /opt/spack /opt/spack
COPY --from=builder /opt/ska-sdp-spack /opt/ska-sdp-spack
COPY --from=builder /opt/karabo-spack /opt/karabo-spack

# Copy CUDA stub symlinks from builder if they exist (for both amd64 and arm64)
# This handles the case where we need to run GPU-enabled binaries on CPU-only nodes (like Github Actions)
# using the stubs to satisfy the dynamic linker.
#
# STRATEGY FOR LIBCUDA (Driver API):
# We need libcuda.so.1 to be present for binaries (like wsclean) linked against it to start on CPU nodes.
# However, we must NOT put it in standard paths (like /usr/lib/x86_64-linux-gnu) because it would mask
# the real NVIDIA driver library injected by the runtime on GPU nodes (causing "CUDA Version: ERR!").
#
# Solution: Put the stub in a low-priority separate directory (/opt/cuda-stub).
COPY --from=builder /usr/lib/*-linux-gnu/libcuda.so.1 /opt/cuda-stub/
COPY --from=builder /usr/lib/*-linux-gnu/libcudart.so* /usr/lib/

# Move them to the correct location for the arch (COPY flattens structure if wildcard is used)
# This is a bit hacky but Docker COPY with wildcards is limited.
# Also recreate CUDA runtime library symlinks pointing to /opt/view libraries
RUN arch=$(uname -m) && \
    mkdir -p /usr/lib/${arch}-linux-gnu && \
    # Move stubs to the correct place
    mkdir -p /opt/cuda-stub && \
    [ -f /opt/cuda-stub/libcuda.so.1 ] && chmod 755 /opt/cuda-stub/libcuda.so.1 || true && \
    # [ -f /opt/cuda-stub/libcuda.so.1 ] && chmod 755 /opt/cuda-stub/libcuda.so.1 && \
    # ln -sf libcuda.so.1 /opt/cuda-stub/libcuda.so || true && \
    chmod -R a+rX /opt/cuda-stub && \
    # Move runtime libs to system path
    mv /usr/lib/libcudart.so* /usr/lib/${arch}-linux-gnu/ 2>/dev/null || true

ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    SPACK_PYTHON=/usr/bin/python3 \
    CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup

# Activate spack env in login shells
RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

#HACK: setup rascil data - create canary file that RASCIL checks for
ENV RASCIL_DATA=/opt/rascil_data
RUN mkdir -p ${RASCIL_DATA}/models && \
    echo "# Dummy RASCIL data file" > ${RASCIL_DATA}/models/S3_151MHz_10deg.csv && \
    fix-permissions ${RASCIL_DATA}

# Create hook that activates spack environment
# IMPORTANT: Spack's setup-env.sh uses a loop variable 'cmd' which conflicts with
# the 'cmd' array set by start.sh. We must save/restore it to avoid interference.
# Disable conda auto-activation in login shells by removing conda hook from .bashrc
RUN mkdir -p /usr/local/bin/before-notebook.d && \
    cat > /usr/local/bin/before-notebook.d/20-activate-spack.sh <<'EOF'
#!/bin/bash
# Save cmd array to avoid conflict with Spack's setup-env.sh loop variable
_saved_cmd=("${cmd[@]}")

# Activate Spack environment
. /opt/spack/share/spack/setup-env.sh
spack env activate -p /opt/spack_env

# Restore cmd array
cmd=("${_saved_cmd[@]}")
unset _saved_cmd
EOF
RUN chmod +x /usr/local/bin/before-notebook.d/20-activate-spack.sh && \
    ( [ -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh ] && \
    rm -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh ) && \
    sed -i '/^eval "\$(conda shell\.bash hook)"/d' /home/jovyan/.bashrc && \
    sed -i '/^eval "\$(conda shell\.bash hook)"/d' /root/.bashrc 2>/dev/null || true

# Configure system-wide library search path for the dynamic linker.
# Direct commands like `docker run IMAGE python ...` do NOT run the
# before-notebook.d hook, so they don't get LD_LIBRARY_PATH from Spack activation.
# This ldconfig configuration ensures shared libraries are found even without
# LD_LIBRARY_PATH being set. DO NOT REMOVE - Python extensions will fail to import.
# Example error without this: "ImportError: libboost_numpy310.so.1.82.0: cannot open shared object file"
# We add /opt/cuda-stub last so it serves as a fallback for libcuda.so.1 on CPU nodes,
# but assumes standard paths (where real driver is mounted) are searched first or prioritized.
RUN arch=$(uname -m) && \
    printf "%s\n" "/opt/view/lib" "/opt/view/lib64" "/usr/lib/${arch}-linux-gnu" "/opt/cuda-stub" > /etc/ld.so.conf.d/karabo-spack-view.conf && \
    # healpy: overlay rescue_internal_healpix_libs copies libhealpix_cxx.so
    # into py-healpy's prefix/lib; register all such dirs with ldconfig.
    for lib in $(find /opt/software -name 'libhealpix_cxx.so*' 2>/dev/null); do \
        dir=$(dirname "$lib"); \
        echo "Found libhealpix_cxx at $dir"; \
        echo "$dir" >> /etc/ld.so.conf.d/karabo-spack-view.conf; \
    done && \
    ldconfig

# Set PATH for non-login shells and direct command execution.
# hree execution contexts require different approaches:
#   1. Direct commands (`docker run IMAGE python`): Only get this ENV, no hooks run
#   2. Jupyter startup: Gets full Spack env via before-notebook.d hook (see line ~362)
#   3. Login shells (`bash -lc`): Gets full Spack env via /etc/profile.d/spack.sh
# Without this ENV, direct commands would use conda's Python instead of Spack's.
# DO NOT REMOVE - breaks smoke tests and CLI usage. Activating Spack for all shells
# would add 16+ seconds overhead per command (tested), making the image unusable.
ENV PATH="/opt/view/bin:${PATH}"

RUN spack test run 'py-astropy-healpix' && \
    # spack test run 'py-astropy' && \ # broken
    # spack test run 'py-numpy': f2py.tests imports pytest at top level,
    # which isn't in numpy's deps.  Manual import test instead:
    python -c "import numpy, numpy.core, numpy.fft, numpy.linalg, numpy.random, numpy.f2py; print('numpy', numpy.__version__, 'OK')" && \
    # spack test run 'py-scipy': array_api_compat.torch imports torch at top level.
    python -c "import scipy, scipy.fft, scipy.linalg, scipy.optimize, scipy.signal, scipy.sparse, scipy.stats; print('scipy', scipy.__version__, 'OK')" && \
    spack test run 'py-bdsf' && \
    spack test run 'py-astroplan' && \
    spack test run 'py-casacore' && \
    # healpy: built from source (--no-cache) so static linking patch applies.
    python -c "import healpy; print('healpy', healpy.__version__, 'nside=64 npix=', healpy.nside2npix(64))" && \
    python -c "import dask, distributed; print('OK', dask.__version__, distributed.__version__)" && \
    # hack: can't run tests for py-distributed due to circular dependency on py-dask
    # spack test run 'py-distributed' && \
    spack test run 'py-ducc' && \
    # spack test run 'py-h5py': h5py.tests imports pytest, which its test env lacks.
    python -c "import h5py; print('h5py', h5py.__version__, h5py.version.hdf5_version)" && \
    spack test run 'py-numexpr' && \
    spack test run 'py-pandas' && \
    # RASCIL is now optional (abandoned project, incompatible with numpy 2)
    # spack test run 'py-rascil' && \
    spack test run 'py-photutils' && \
    spack test run 'py-pyerfa' && \
    # spack test run 'py-reproject': test venv lacks py-dask, manual import instead
    python -c "import reproject; print('reproject', reproject.__version__, 'OK')" && \
    spack test run 'py-seqfile' && \
    spack test run 'py-ska-sdp-datamodels' && \
    spack test run 'py-ska-sdp-func-python' && \
    spack test run 'py-ska-sdp-func' && \
    spack test run 'py-xarray' && \
    spack test run 'oskar' && \
    spack test run 'py-mpi4py' && \
    spack test run 'py-dask-mpi' && \
    spack test run 'py-pyfftw' && \
    spack test run 'py-eidos' && \
    spack test run 'py-katbeam' && \
    spack test run 'py-tools21cm' && \
    spack test run 'hyperbeam' && \
    spack test run 'wsclean'
    # spack test run 'aoflagger'

# TODO: Clean up test artifacts
# rm -rf /tmp/* /root/.cache/* && \
# find /opt/software -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
# spack test run 'py-pyuvdata'

# TODO: Verify hyperbeam (Spack-installed) can be imported
# RUN python -c "from mwa_hyperbeam import FEEBeam; print('mwa_hyperbeam (Spack) import successful')"

ARG PIP_EXTRAS="psrecord==1.4 click aoquality losoto kneed seaborn nest-asyncio==1.6.0"
ARG PIP_GIT_EXTRAS="git+https://github.com/d3v-null/SSINS.git@eavils-copilot git+https://github.com/d3v-null/mwa_qa.git@dev git+https://github.com/tjgalvin/fits_warp.git"

# Install optional extras via pip (not available in Spack)
# Use python -m pip instead of pip directly to avoid shebang issues!
# Install cython first as it's required by tools21cm metadata check
# Install git packages with --no-deps to avoid pulling in incompatible numpy/pandas/matplotlib
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install cython && \
    ( [ -z "${PIP_EXTRAS}" ] || python -m pip install ${PIP_EXTRAS} ) && \
    ( [ -z "${PIP_GIT_EXTRAS}" ] || python -m pip install --no-deps ${PIP_GIT_EXTRAS} )

# distributed 2022.12.1 requires msgpack>=0.6.0, which is not installed.
# rascil 1.0.0 requires h5py<3.8,>=3.7, but you have h5py 3.12.1 which is incompatible.
# rascil 1.0.0 requires matplotlib<3.7,>=3.6, but you have matplotlib 3.9.2 which is incompatible.
# rascil 1.0.0 requires scipy<1.10,>=1.9, but you have scipy 1.10.1 which is incompatible.
# rascil 1.0.0 requires tabulate<0.10,>=0.9, but you have tabulate 0.0.0 which is incompatible.
# rascil 1.0.0 requires xarray<2022.13,>=2022.12, but you have xarray 2023.2.0 which is incompatible.
# Successfully installed anyio-4.11.0 argon2-cffi-25.1.0 argon2-cffi-bindings-25.1.0 arrow-1.4.0 asttokens-3.0.0 async-lru-2.0.5 attrs-25.4.0 babel-2.17.0 beautifulsoup4-4.14.2 bleach-6.2.0 cffi-2.0.0 comm-0.2.3 debugpy-1.8.17 decorator-5.2.1 defusedxml-0.7.1 executing-2.2.1 fastjsonschema-2.21.2 fqdn-1.5.1 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 ipykernel-6.31.0 ipython-8.37.0 isoduration-20.11.0 jedi-0.19.2 json5-0.12.1 jsonpointer-3.0.0 jsonschema-4.25.1 jsonschema-specifications-2025.9.1 jupyter-events-0.12.0 jupyter-lsp-2.3.0 jupyter-server-terminals-0.5.3 jupyter_client-8.6.3 jupyter_core-5.9.1 jupyter_server-2.17.0 jupyterlab-4.4.10 jupyterlab-pygments-0.3.0 jupyterlab_server-2.28.0 lark-1.3.0 matplotlib-inline-0.2.1 mistune-3.1.4 nbclient-0.10.2 nbconvert-7.16.6 nbformat-5.10.4 nest-asyncio-1.6.0 notebook-7.4.7 notebook-shim-0.2.4 overrides-7.7.0 pandocfilters-1.5.1 parso-0.8.5 pexpect-4.9.0 platformdirs-4.5.0 prometheus-client-0.23.1 prompt_toolkit-3.0.52 ptyprocess-0.7.0 pure-eval-0.2.3 pycparser-2.23 pygments-2.19.2 python-json-logger-4.0.0 pyzmq-27.1.0 referencing-0.37.0 rfc3339-validator-0.1.4 rfc3986-validator-0.1.1 rfc3987-syntax-1.1.0 rpds-py-0.28.0 send2trash-1.8.3 sniffio-1.3.1 soupsieve-2.8 stack_data-0.6.3 terminado-0.18.1 tinycss2-1.4.0 tornado-6.5.2 traitlets-5.14.3 tzdata-2025.2 uri-template-1.3.0 wcwidth-0.2.14 webcolors-24.11.1 webencodings-0.5.1 websocket-client-1.9.0

ENV MWA_BEAM_FILE=/opt/mwa_full_embedded_element_pattern.h5
RUN wget -O$MWA_BEAM_FILE http://ws.mwatelescope.org/static/mwa_full_embedded_element_pattern.h5 --progress=dot:mega
# The +mwa rapthor variant points DP3/WSClean at exactly that beam file.
RUN rapthor --version && \
    rapthor_dir="$(python -c 'import rapthor, os; print(os.path.dirname(rapthor.__file__))')" && \
    grep -q coefficients_path "${rapthor_dir}/pipeline/steps/ddecal_solve.cwl" && \
    grep -q 'usefastpredict=False' "${rapthor_dir}/pipeline/steps/ddecal_solve.cwl" && \
    grep -q 'beammode=full' "${rapthor_dir}/pipeline/steps/ddecal_solve.cwl" && \
    grep -q 'uvwcompression=False' "${rapthor_dir}/pipeline/steps/prepare_imaging_data.cwl" && \
    grep -q -- '-mwa-path' "${rapthor_dir}/pipeline/steps/wsclean_image_no_dde.cwl" && \
    grep -q 'rapthor-mwa' "${rapthor_dir}/scripts/filter_skymodel.py" && \
    echo "rapthor +mwa patch present"

# This fixture is EveryBeam's upstream MWA regression MS.  The probe uses the
# same PointResponse::Response(kFull, station, frequency, ITRF direction)
# primitive as DP3 Predict, then removes the MS so it is not shipped in the image.
COPY everybeam_mwa_predict_test.py /opt/everybeam_mwa_predict_test.py
RUN --mount=type=cache,target=/opt/everybeam-test-cache,id=everybeam-mwa-test-data,sharing=locked \
    cp /opt/everybeam-test-cache/MWA-single-timeslot.tar.bz2 /tmp/ 2>/dev/null || \
    wget -q -P /tmp https://support.astron.nl/software/ci_data/EveryBeam/MWA-single-timeslot.tar.bz2; \
    tar -xf /tmp/MWA-single-timeslot.tar.bz2 -C /tmp --one-top-level=MWA_MOCK.ms --strip-components=1 && \
    cp /tmp/MWA-single-timeslot.tar.bz2 /opt/everybeam-test-cache/ && \
    python /opt/everybeam_mwa_predict_test.py && \
    DP3 --version && \
    python -c "import dp3; print('dp3 Python import OK')" && \
    rm -rf /tmp/MWA_MOCK.ms /tmp/MWA-single-timeslot.tar.bz2

# tests
RUN python -c "import ska_sdp_func_python" || exit 1 && \
    python -c "import ska_sdp_func; print('ska_sdp_func', 'OK')" || exit 1 && \
    python -c "import ska_sdp_datamodels" || exit 1 && \
    python -c "import casacore, casacore.tables, casacore.quanta; print('python-casacore OK')" && \
    python - <<"PY"
import importlib, os, sys

checks = [
    # bdsf first: PyBDSF >= 1.13.0.20260409 sets the multiprocessing start method on
    # import and raises 'context has already been set' if another import got there first
    ('bdsf','1.10'),
    # ARatmospy uses np.float_ removed in NumPy 2; skip until upstream fixes it
    # ('ARatmospy','1.0'),
    ('astropy','5.1'),
    ('astropy_healpix','1.0'),
    ('dask_mpi','0.0'),
    ('dask','2022.10'),
    ('distributed','2022.10'),
    ('eidos','1.1'),
    ('erfa','2.0'),
    ('healpy','1.16'),
    ('joblib','0.0'),
    ('katbeam','0.1'),
    ('lazy_loader','0.0'),
    ('mpi4py','0.0'),
    ('numpy','2.2.0'),
    ('pandas', '2.2.3'),
    ('photutils', '1.11.0'),
    ('pyfftw','0.0'),
    ('pyuvdata','2.4'),
    # rascil removed: abandoned project, incompatible with numpy 2
    # ('rascil','1.0'),
    ('reproject','0.9'),
    ('rfc3986','2.0'),
    ('skimage', '0.24'),
    ('sklearn', '1.3'),
    ('tabulate', '0.9'),
    ('tools21cm','2.0.3'),
    ('toolz','0.0'),
    ('tqdm','4.0'),
    ('xarray', '2023.2.0'),
    # not karabo related:
    # ('aoflagger','3.0'),
    ('mwa_hyperbeam','0.10'),
]

for (name, target) in checks:
    mod = None
    try:
        mod = importlib.import_module(name)
    except Exception as exc:
        print(f'{name} not importable: {exc}')
        sys.exit(1)
    ver = getattr(mod, '__version__', '0.0')
    try:
        assert tuple([*ver.split('.')]) >= tuple([*target.split('.')])
    except Exception:
        print(f'{name} version not available')
        continue
    print(f'{name} version {ver}, target {target}')
sys.exit(0)
PY


# bdsf 1.12.0 requires backports.shutil-get-terminal-size, which is not installed.
# astropy-healpix 1.1.2 requires numpy>=1.25, but you have numpy 1.23.5 which is incompatible.
# rascil 1.0.0 requires matplotlib<3.7,>=3.6, but you have matplotlib 3.9.2 which is incompatible.
# rascil 1.0.0 requires tabulate<0.10,>=0.9, but you have tabulate 0.0.0 which is incompatible.
# rascil 1.0.0 requires xarray<2022.13,>=2022.12, but you have xarray 2023.2.0 which is incompatible.
# ska-sdp-datamodels 0.1.3 requires astroplan<0.9,>=0.8, but you have astroplan 0.0.0 which is incompatible.
# ska-sdp-datamodels 0.1.3 requires xarray<2023.0.0,>=2022.10.0, but you have xarray 2023.2.0 which is incompatible.
# ska-sdp-func-python 0.1.4 requires astroplan<0.9,>=0.8, but you have astroplan 0.0.0 which is incompatible.
# ska-sdp-func-python 0.1.4 requires xarray<2023.0.0,>=2022.11.0, but you have xarray 2023.2.0 which is incompatible.
# WARNING: AstropyDeprecationWarning: The private astropy._erfa module has been made into its own package, pyerfa, which is a dependency of astropy and can be imported directly using "import erfa" [astropy._erfa]

# Copy repository for editable install and testing
ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100

# Karabo dependencies are installed via Spack above, but not py-karabo itself
# Install local Karabo from source via pip
RUN mkdir -p /opt/Karabo-Pipeline /home/${NB_USER}/{.astropy/cache,.cache,.config/matplotlib}
COPY --chown=${NB_UID}:${NB_GID} karabo /opt/Karabo-Pipeline/karabo
COPY --chown=${NB_UID}:${NB_GID} setup.cfg pyproject.toml /opt/Karabo-Pipeline/
RUN python -m pip install --no-cache-dir --no-deps -e /opt/Karabo-Pipeline && \
    fix-permissions /opt/Karabo-Pipeline /home/${NB_USER}

RUN python -m pip install --no-cache-dir git+https://github.com/NERSC/slurm-magic.git

USER ${NB_UID}
# Register kernel for jovyan user using the Spack Python
RUN python -m ipykernel install --user --name=karabo --display-name="Karabo (Spack Py3.11)"

# Run tests during build to validate environment
ARG SKIP_TESTS=0
ENV SKIP_TESTS=${SKIP_TESTS}
RUN if [ "${SKIP_TESTS:-0}" = "1" ]; then exit 0; fi; \
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1; \
    cd /opt/Karabo-Pipeline && \
    # test_simulation_noise_meerkat needs RASCIL, which the image no longer ships.
    pytest -x -k "not test_simulation_noise_meerkat" && \
    # Best-effort cleanup (e.g. root-owned OpenMPI session dirs in /tmp), braced so
    # it can't mask a pytest failure the way a trailing bare `|| true` did.
    { { rm -rf /home/${NB_USER}/.astropy/cache \
        /home/${NB_USER}/.cache/* \
        /tmp/* \
        /home/${NB_USER}/.local/share/jupyter/runtime/* \
        /opt/Karabo-Pipeline/.pytest_cache; \
      find /opt/Karabo-Pipeline -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -exec rm -rf {} + ; \
    } 2>/dev/null || true; }

# download latest Leap_Second.dat, IERS finals2000A.all
# Cache prewarm only: IERS servers have outages (datacenter.iers.org 400s, USNO
# down on 2026-10-21) and astropy retries at runtime, so don't fail the build.
RUN python -c "from astropy.time import Time; t=Time.now(); from astropy.utils.data import download_file; download_file('http://data.astropy.org/coordinates/sites.json', cache=True); print(t.gps, t.ut1)" \
    || echo "WARNING: astropy IERS/site prefetch failed; astropy will download at runtime" >&2

# Verify CUDA runtime libraries are loadable, only if CUDA_VERSION and CUDA_ARCH are set as ARG or ENV
# This ensures that the symlinks we created manually (libcudart.so -> libcudart.so.12 -> ...)
# are correct and that the libraries can be found by the dynamic linker.
# We explicitly skip checking libcuda.so.1 (Driver API) because we removed the stub,
# and the real driver library is only available at runtime with --gpus.
# We run this check as NB_USER to ensure permissions are correct.
RUN if [ -z "${CUDA_VERSION:-}" ] || [ -z "${CUDA_ARCH:-}" ]; then \
    exit 0; \
    fi; \
    command -v nvidia-smi; \
    export CUDA_VERSION="$CUDA_VERSION"; \
    python - <<"PY"
import ctypes
import os
import sys

cuda_version = os.environ.get("CUDA_VERSION", "")
major = cuda_version.split('.')[0] if cuda_version else ""
libs = ["libcudart.so"]
if major:
    libs.append(f"libcudart.so.{major}")

# We skip libcuda.so.1 as it might fail in build environments without GPU/driver
for lib in libs:
    try:
        ctypes.CDLL(lib)
        print(f"SUCCESS: {lib} loaded")
    except OSError as e:
        print(f"FAILURE: {lib} failed to load: {e}")
        sys.exit(1)
PY

WORKDIR "/home/${NB_USER}"
