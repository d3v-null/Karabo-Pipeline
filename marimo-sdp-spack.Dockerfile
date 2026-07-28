# Marimo image using the SDP-maintained Spack 1.1.1 base.
#
# Seed the reusable BuildKit caches with:
#   docker build --target cache-seed --build-arg SPACK_BUILDCACHE_LOCAL=1 \
#     -f marimo-sdp-spack.Dockerfile .
# Subsequent builds reuse those caches and the generated file mirror; they do
# not depend on a mutable, locally built base image.
FROM registry.gitlab.com/ska-telescope/sdp/ska-sdp-spack/ska-sdp-spack-ubuntu:2026.07.2 AS builder

USER root
SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive \
    SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    CARGO_HOME=/opt/rust/cargo \
    RUSTUP_HOME=/opt/rust/rustup \
    PATH=/opt/rust/cargo/bin:/opt/spack/bin:${PATH}

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    autoconf automake bison build-essential bzip2 libbz2-dev ca-certificates \
    cmake curl diffutils file findutils gfortran git libcurl4-openssl-dev \
    libgomp1 libltdl-dev libtool m4 nodejs npm patchelf perl pkg-config python3-yaml \
    rustc cargo time wget zstd && \
    rm -rf /var/lib/apt/lists/*

# py-cdshealpix's locked Cargo dependencies require Rust >=1.81.  Install the
# prebuilt toolchain once in this cacheable layer; Spack discovers it as an
# external package, so it is never rebuilt from source.
RUN set -o pipefail && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.81.0 --no-modify-path && \
    rustc --version && cargo --version
# git clone --depth=1 --single-branch --branch=2026.07.2 \
#   https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
#   rm -rf /opt/ska-sdp-spack/.git && \
RUN set -o pipefail && \
    test -d /opt/ska-sdp-spack/packages && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    if ! spack config get repos | grep -Fq /opt/ska-sdp-spack; then \
        spack repo add /opt/ska-sdp-spack; \
    fi

COPY --link spack-overlay /opt/karabo-spack
RUN set -o pipefail && \
    for package in /opt/karabo-spack/packages/*; do \
        case "$(basename "${package}")" in \
            dp3|everybeam|py-astropy-healpix|py-bdsf|py-cwltool|py-lsmtool|py-python-dateutil|py-rapthor|py-schema-salad|py-ska-sdp-ical|py-toil|wsclean) ;; \
            *) rm -rf "${package}" ;; \
        esac; \
    done && \
    test -f /opt/karabo-spack/packages/py-toil/kubernetes-batch-system.patch && \
    test -f /opt/karabo-spack/packages/py-cwltool/package.py && \
    test -f /opt/karabo-spack/packages/py-ska-sdp-ical/package.py && \
    test -f /opt/karabo-spack/packages/py-rapthor/kubernetes-batch-system.patch && \
    test -f /opt/karabo-spack/packages/py-rapthor/toil-runtime-options.patch && \
    test -f /opt/karabo-spack/packages/py-rapthor/streamflow-optional.patch && \
    test -f /opt/karabo-spack/packages/py-lsmtool/rapthor-facet-robustness.patch && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack repo add /opt/karabo-spack

ARG PYTHON_VERSION=3.11.11
ARG NUMPY_VERSION=2.3.5
ARG CFITSIO_VERSION=4.5.0
ARG PANDAS_VERSION=2.3.3
ARG XARRAY_VERSION=2025.7.1
ARG H5PY_VERSION=3.14.0
ARG HDF5_VERSION=1.14.6
ARG SCIPY_VERSION=1.17.1
ARG MATPLOTLIB_VERSION=3.9.4
ARG ASTROPY_VERSION=7.1.1
ARG CASACORE_VERSION=3.8.0
ARG PY_CASACORE_VERSION=3.7.1
ARG BOOST_VERSION=1.88.0
ARG REPROJECT_VERSION=0.14.1
ARG BDSF_VERSION=1.13.0.20260409
ARG AOFLAGGER_VERSION=3.6.0.dev1
ARG WSCLEAN_VERSION=3.6.20260109
ARG EVERYBEAM_VERSION=0.8.3
ARG DP3_VERSION=6.6
ARG RAPTHOR_VERSION=2.1.20260630
ARG SPACK_TARGET="x86_64_v3"
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

# The SDP image's Spack store remains intact.  Only the environment metadata
# and generated view are recreated, so a future SDP base store is reusable.
RUN <<EOF
rm -rf /opt/spack_env /opt/view /opt/._view
mkdir -p /opt/spack_env /opt/{software,view,._view,buildcache,spack-source-cache,spack-misc-cache}
cat > /opt/spack_env/spack.yaml <<YAML
spack:
  specs:
  - python@${PYTHON_VERSION}
  - py-pip
  - karabo.py-toil@9.3.0+cwl
  - karabo.py-rapthor@${RAPTHOR_VERSION}
  - py-ska-sdp-benchmark-monitor@0.1.0
  - py-ska-sdp-ical@main
  # Overlay roots must be freshly concretized when their recipes or patches
  # change; compatible dependencies remain reusable from SDP/buildcache specs.
  - karabo.everybeam@${EVERYBEAM_VERSION}+python
  - karabo.dp3
  - karabo.wsclean
  - karabo.py-bdsf@${BDSF_VERSION}
  - karabo.py-cwltool
  - ska-sdp-spack.py-losoto@2.6.0
  - karabo.py-lsmtool
  - karabo.py-python-dateutil@2.8.2
  - ska-sdp-spack.py-reproject@${REPROJECT_VERSION}
  - builtin.py-zarr
  concretizer:
    unify: when_possible
    reuse:
      roots: true
      exclude: [rust]
      from:
      - type: environment
        path: /opt/spack-environment
  config:
    install_tree:
      root: /opt/software
    source_cache: /opt/spack-source-cache
    misc_cache: /opt/spack-misc-cache
  packages:
    all:
      target: [x86_64_v2]
    rust:
      require: "@1.81.0:"
    casacore:
      variants: +data+python
      require: "@${CASACORE_VERSION}+python+data+dysco~hdf5~mpi~openmp"
    py-numpy:
      require: "@${NUMPY_VERSION}"
    py-scipy:
      require: "@${SCIPY_VERSION}"
    py-matplotlib:
      require: "@${MATPLOTLIB_VERSION}"
    py-h5py:
      require: "@${H5PY_VERSION}"
    py-pandas:
      require: "@${PANDAS_VERSION}"
    py-xarray:
      require: "@${XARRAY_VERSION}"
    py-bdsf:
      require: "@${BDSF_VERSION}"
    py-reproject:
      require: "@${REPROJECT_VERSION}"
    py-tables:
      require: "@3.10.2"
    py-numexpr:
      require: "@2.10.2:"
    py-losoto:
      require: "@2.6:"
    py-lsmtool:
      require: "@1.6.2:"
    py-astropy:
      require: "@${ASTROPY_VERSION}"
    dp3:
      require: "@${DP3_VERSION}+idg"
    idg:
      require: ~cuda
    everybeam:
      require: "@${EVERYBEAM_VERSION}+python"
    aoflagger:
      require: "@${AOFLAGGER_VERSION}"
    py-casacore:
      require: "@${PY_CASACORE_VERSION}"
    cfitsio:
      require: "@${CFITSIO_VERSION}+bzip2+fortran+utils"
    hdf5:
      require: "@${HDF5_VERSION}+hl~mpi+threadsafe"
    boost:
      require: "@${BOOST_VERSION}+test+python+numpy"
    wsclean:
      require: "@${WSCLEAN_VERSION}~mpi~cuda"
  view:
    default:
      root: /opt/view
YAML
EOF

RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache-2026.07.2,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=rapthor-sdp-spack-source-toil9-v4,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=rapthor-sdp-spack-misc-toil9-v4,sharing=locked \
    --mount=type=secret,id=spack_oci_username,required=false \
    --mount=type=secret,id=spack_oci_password,required=false \
    set -o pipefail && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate --without-view /opt/spack_env && \
    arch=$(uname -m) && spack_target=${SPACK_TARGET:-} && \
    if [ -z "${spack_target}" ]; then case "${arch}" in x86_64) spack_target=x86_64_v2 ;; aarch64) spack_target=aarch64 ;; *) spack_target=${arch} ;; esac; fi && \
    echo "SPACK_TARGET=${spack_target} <- (uname -m)=${arch}" && \
    spack compiler find && \
    spack external find autoconf automake bison bzip2 curl diffutils findutils git libtool m4 node-js perl pkgconf rust && \
    spack config add "packages:rust:buildable:false" && \
    spack config add "packages:all:target:[${spack_target}]" && \
    spack mirror add v1.1.1 https://binaries.spack.io/v1.1.1 && \
    if [ -n "${SPACK_BUILDCACHE_LOCAL}" ] && [ "${SPACK_BUILDCACHE_LOCAL}" != "0" ]; then \
        spack mirror add --autopush --unsigned local file:///opt/buildcache; \
    fi && \
    if [ -n "${SPACK_MIRROR_OCI}" ]; then \
        if [ -s /run/secrets/spack_oci_username ] && [ -s /run/secrets/spack_oci_password ]; then \
            SPACK_OCI_USERNAME="$(cat /run/secrets/spack_oci_username)" && \
            export SPACK_OCI_PASSWORD="$(cat /run/secrets/spack_oci_password)" && \
            spack mirror add --autopush --unsigned \
                --oci-username "${SPACK_OCI_USERNAME}" \
                --oci-password-variable SPACK_OCI_PASSWORD \
                oci-push "${SPACK_MIRROR_OCI}"; \
        else \
            spack mirror add --unsigned oci-cache "${SPACK_MIRROR_OCI}"; \
        fi; \
    fi && \
    spack buildcache keys --install --trust || true && \
    spack concretize --force --fresh-roots --reuse-deps && \
    python3 -c "import json,sys;d=json.load(open('/opt/spack_env/spack.lock'));\
t=['py-rapthor','py-numpy','py-scipy','py-matplotlib','py-astropy',\
   'py-casacore','casacore','py-h5py','py-pandas','py-xarray',\
   'py-bdsf','py-reproject','py-losoto','py-lsmtool',\
   'dp3','everybeam','aoflagger','wsclean','py-toil'];\
c={};[c.setdefault(s.get('name'),[]).append(0) for s in d.get('concrete_specs',{}).values()];\
e=[x for x in t if len(c.get(x,[]))>1];\
r=['py-cloudpickle','py-dask','py-fsspec','py-zarr'];\
m=[x for x in r if not c.get(x)];\
roots={s.get('spec','').split('@')[0].split('.')[-1] for s in d.get('roots',[])};\
x=[x for x in ['dp3','everybeam','py-bdsf','py-cwltool','py-losoto','py-lsmtool','py-python-dateutil','py-reproject','wsclean'] if x not in roots];\
print(f'Duplicate packages: {e}; missing runtime dependencies: {m}; missing overlay roots: {x}');\
sys.exit(1) if e or m or x else print('Concretized package graph OK')" && \
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    if spack mirror list | awk '{print $1}' | grep -qx oci-push; then \
        spack buildcache update-index -k oci-push || spack buildcache update-index oci-push; \
    fi && \
    spack gc -y && \
    # Static archives are only needed at link time; the shared libs
    # copied into the runtime image already satisfy everything at
    # runtime. Removing them trims several GB with no functional risk.
    find /opt/software -name '*.a' -delete && \
    spack env view regenerate && \
    /opt/view/bin/pip check && \
    /opt/view/bin/pip install --no-cache-dir --upgrade-strategy only-if-needed \
        jupyterlab notebook ipykernel packaging \
        'requests>=2.32' 'mistune<3.1' && \
    chmod -R a+rX /opt/view /opt/._view /opt/spack_env /opt/karabo-spack

RUN /opt/view/bin/pip check

# A first build of this target seeds the named BuildKit caches and local mirror.
FROM builder AS cache-seed

# ----------- Runtime image -----------
FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6

USER root
SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    build-essential \
    ca-certificates \
    curl \
    gfortran \
    git \
    libcap2-bin \
    libcurl4-openssl-dev \
    libgomp1 \
    linux-tools-generic \
    pciutils \
    time \
    wget \
    zstd

RUN perf_bin="" && \
    for candidate in /usr/lib/linux-tools/*/perf; do perf_bin="${candidate}"; done && \
    test -x "${perf_bin}" && \
    perf_bin="$(readlink -f "${perf_bin}")" && \
    setcap cap_perfmon,cap_ipc_lock=ep "${perf_bin}" && \
    ln -sf "${perf_bin}" /usr/local/bin/perf && \
    getcap "${perf_bin}"

COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /opt/._view /opt/._view
COPY --from=builder /opt/spack_env /opt/spack_env
COPY --from=builder /opt/spack /opt/spack
COPY --from=builder /opt/ska-sdp-spack /opt/ska-sdp-spack
COPY --from=builder /opt/karabo-spack /opt/karabo-spack

RUN chmod a+r \
    /opt/spack/etc/spack/repos.yaml \
    /opt/software/.spack-db/index.json

ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1

# Activate spack env in login shells
RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

# Create before-notebook hook to activate spack environment
RUN mkdir -p /usr/local/bin/before-notebook.d && \
    cat > /usr/local/bin/before-notebook.d/20-activate-spack.sh <<'EOF'
#!/bin/bash
_saved_cmd=("${cmd[@]}")
. /opt/spack/share/spack/setup-env.sh
spack env activate -p /opt/spack_env
cmd=("${_saved_cmd[@]}")
unset _saved_cmd
EOF
RUN chmod +x /usr/local/bin/before-notebook.d/20-activate-spack.sh && \
    ( [ -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh ] && \
    rm -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh ) && \
    sed -i '/^eval "\$(conda shell\.bash hook)"/d' /home/jovyan/.bashrc && \
    sed -i '/^eval "\$(conda shell\.bash hook)"/d' /root/.bashrc 2>/dev/null || true

# Configure ldconfig for spack libraries
RUN arch=$(uname -m) && \
    printf "%s\n" "/opt/view/lib" "/opt/view/lib64" "/usr/lib/${arch}-linux-gnu" > /etc/ld.so.conf.d/spack-view.conf && \
    ldconfig

# Set PATH for non-login shells
ENV PATH="/opt/view/bin:${PATH}"

# Kubernetes execution support is installed and patched by the py-toil and
# py-rapthor Spack overlay packages, so every Rapthor workload gets the same
# behavior without mutating installed site-packages at image build time.

# Basic tests
RUN python -c "import numpy; print('numpy', numpy.__version__, 'OK')" && \
    python -c "import scipy; print('scipy', scipy.__version__, 'OK')" && \
    python -c "import casacore, casacore.tables; print('python-casacore OK')" && \
    python -c "import kubernetes; print('kubernetes', kubernetes.__version__, 'OK')" && \
    python -c "import importlib.metadata as metadata; assert metadata.version('toil') == '9.3.0'; print('toil', metadata.version('toil'), 'OK')" && \
    python -c "import inspect, lsmtool.facet, toil; from toil.batchSystems import kubernetes as k8s; from rapthor.lib import cwlrunner, operation, parset; checks={'extra-hostpath': 'TOIL_KUBERNETES_EXTRA_HOSTPATH' in inspect.getsource(k8s), 'security-context-loader': 'open(file).read()' in inspect.getsource(k8s), 'skip-image-check': 'TOIL_SKIP_IMAGE_CHECK' in inspect.getsource(toil), 'batch-system-validator': 'kubernetes' in inspect.getsource(parset), 'kubernetes-options': '_add_kubernetes_options' in inspect.getsource(cwlrunner), 'max-cores': 'TOIL_MAX_CORES' in inspect.getsource(cwlrunner), 'workdir': 'TOIL_WORKDIR' in inspect.getsource(cwlrunner), 'single-machine-parallelism': '\"single_machine\", \"kubernetes\"' in inspect.getsource(operation), 'voronoi-fallback': 'voronoi fallback facet centers at bbox middle' in inspect.getsource(lsmtool.facet.voronoi), 'facet-reference-point': 'representative_point' in inspect.getsource(lsmtool.facet.Facet)}; print('Patch checks:', checks); assert all(checks.values()), [name for name, applied in checks.items() if not applied]" && \
    python -c "import benchmon; print('benchmon OK')" && \
    command -v benchmon-start && \
    command -v benchmon-stop && \
    command -v benchmon-visu && \
    command -v perf && \
    command -v lspci && \
    benchmon-run --help >/dev/null && \
    benchmon-visu --help >/dev/null && \
    (perf --version || test $? -eq 126) && \
    python -c "import everybeam, losoto; print('EveryBeam and LoSoTo imports OK')" && \
    python -c "import rapthor; print('rapthor OK')" && \
    rapthor --version && \
    pip check

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PYTHON_VERSION=3.11

RUN python -m pip install --no-cache-dir git+https://github.com/NERSC/slurm-magic.git

# KubeSpawner runs `jupyterhub-singleuser`; Marimo needs the CLI + lab extension.
# Install into the Spack view Python that already ships JupyterLab in this image.
ENV PATH=/opt/view/bin:${PATH}
RUN python3 -m pip install --no-cache-dir \
    "jupyterhub==4.1.6" \
    "marimo[sandbox]>=0.19.11" \
    "marimo-jupyter-extension>=0.1.4" \
 && ln -sf "$(command -v marimo)" /usr/local/bin/marimo \
 && ln -sf "$(command -v jupyterhub-singleuser)" /usr/local/bin/jupyterhub-singleuser \
 && python3 -c 'import jupyterhub; assert jupyterhub.__version__ == "4.1.6", jupyterhub.__version__' \
 && jupyterhub-singleuser --help >/dev/null \
 && marimo --version

RUN install -d -o ${NB_UID} -g ${NB_GID} /home/${NB_USER}/.astropy/cache

USER ${NB_UID}

RUN test -r /opt/spack/etc/spack/repos.yaml && \
    spack env activate -p /opt/spack_env

# Register kernel for jovyan user using the Spack Python
RUN python -m ipykernel install --user --name=rapthor --display-name="Rapthor (Spack Py${PYTHON_VERSION})"

# download latest Leap_Second.dat, IERS finals2000A.all
RUN python -c "from astropy.time import Time; t=Time.now(); print(t.gps, t.ut1)" || true

WORKDIR "/home/${NB_USER}"

# Ensure spack python's jupyter is used instead of conda's
# The before-notebook hook activates spack env which prepends /opt/view/bin to PATH
# but start-notebook.sh runs /opt/conda/bin/jupyter-lab directly.
# Fix by shadowing conda's jupyter commands with symlinks to spack's
USER root
RUN rm -f /opt/conda/bin/jupyter* && \
    ln -s /opt/view/bin/jupyter /opt/conda/bin/jupyter && \
    ln -s /opt/view/bin/jupyter-lab /opt/conda/bin/jupyter-lab && \
    ln -s /opt/view/bin/jupyter-notebook /opt/conda/bin/jupyter-notebook
USER ${NB_UID}
