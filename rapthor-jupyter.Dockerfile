# Minimal Jupyter notebook with Rapthor pipeline
# Based on quay.io/jupyter/minimal-notebook with Spack-installed rapthor dependencies
# build: docker build . -f rapthor-jupyter.Dockerfile --tag rapthor-jupyter:latest
# with local buildcache:
# DOCKER_BUILDKIT=1 docker build --build-arg SPACK_BUILDCACHE_LOCAL=1 \
#   . -f rapthor-jupyter.Dockerfile --tag rapthor-jupyter:latest \
#   --progress=plain
# The first build compiles and publishes packages to the named BuildKit cache;
# later builds consume that local mirror. The cache is BuildKit-managed, not a
# host directory.
#
# Optional DP3/IDG/WSClean CUDA (OFF by default). Leave CUDA_ARCH empty for CPU-only.
# GPU build example:
# DOCKER_BUILDKIT=1 docker build -f rapthor-jupyter.Dockerfile \
#   --build-arg CUDA_ARCH=75,80,86,89,90 --build-arg CUDA_VERSION=12.2.2 \
#   --tag rapthor-jupyter:cuda --progress=plain .
# Runtime: docker run --gpus all ... and ddecal.usegpu=true (diagonal+directioniterative).
#
# run: docker run --rm -it -v $PWD:$PWD -w $PWD -e OPENBLAS_NUM_THREADS=1 -p 8888:8888 rapthor-jupyter:latest

FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6 AS builder

USER root
SHELL ["/bin/bash", "-lc"]

# Re-declare ARG to make it available in this stage
ARG PYTHON_VERSION=3.12

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
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
    nodejs \
    npm \
    patchelf \
    perl \
    pkg-config \
    rustc \
    cargo \
    time \
    wget \
    zstd

# Install Spack and detect compilers
ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    CARGO_HOME=/opt/rust/cargo \
    RUSTUP_HOME=/opt/rust/rustup \
    PATH=/opt/rust/cargo/bin:${PATH}
RUN git clone --depth=1 --single-branch --branch=v1.1.1 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    cd ${SPACK_ROOT} && \
    rm -rf .git && \
    find ${SPACK_ROOT}/lib/spack/docs -xtype l -delete || true && \
    . share/spack/setup-env.sh && \
    spack env create --dir /opt/spack_env && \
    fix-permissions ${SPACK_ROOT} /opt/spack_env

# py-cdshealpix's locked Cargo dependencies require Rust >=1.81.  Install the
# prebuilt toolchain once in this cacheable layer; Spack discovers it as an
# external package, so it is never rebuilt from source.
RUN set -o pipefail && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.81.0 --no-modify-path && \
    rustc --version && cargo --version

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
    libtool \
    m4 \
    node-js \
    perl \
    pkgconf \
    rust

# Add SKA SDP Spack repo and Karabo overlay for rapthor
RUN git clone --depth=1 --single-branch --branch=2026.07.2 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
    rm -rf /opt/ska-sdp-spack/.git && \
    spack repo add /opt/ska-sdp-spack
COPY --link spack-overlay /opt/karabo-spack
RUN test -f /opt/karabo-spack/packages/py-toil/kubernetes-batch-system.patch && \
    test -f /opt/karabo-spack/packages/py-cwltool/package.py && \
    test -f /opt/karabo-spack/packages/py-ska-sdp-ical/package.py && \
    test -f /opt/karabo-spack/packages/py-rapthor/kubernetes-batch-system.patch && \
    test -f /opt/karabo-spack/packages/py-rapthor/toil-runtime-options.patch && \
    test -f /opt/karabo-spack/packages/py-lsmtool/rapthor-facet-robustness.patch && \
    test -f /opt/karabo-spack/packages/dp3/cuda-solverbase-api.patch && \
    spack repo add /opt/karabo-spack

# Version pins for numpy 2 compatibility
ARG NUMPY_VERSION=2.2.0
ARG CFITSIO_VERSION=4.6.3
ARG PANDAS_VERSION=2.2.3
ARG XARRAY_VERSION=2024.10.0
ARG H5PY_VERSION=3.12.1
ARG HDF5_VERSION=1.14.3
ARG SCIPY_VERSION=1.14.1
ARG MATPLOTLIB_VERSION=3.9.2
ARG ASTROPY_VERSION=6.1.0
ARG CASACORE_VERSION=3.7.1
ARG BOOST_VERSION=1.88.0
ARG REPROJECT_VERSION=0.14.1
ARG BDSF_VERSION=1.13.0.20260409
ARG AOFLAGGER_VERSION=3.4.0
ARG WSCLEAN_VERSION=3.6.20260109
ARG EVERYBEAM_VERSION=0.8.3
ARG DP3_VERSION=6.6
ARG RAPTHOR_VERSION=2.1.20260630
# Empty CUDA_ARCH => CPU-only (default). Non-empty enables DP3/IDG/WSClean CUDA.
ARG CUDA_ARCH=""
ARG CUDA_VERSION=12.2.2

ARG SPACK_TARGET=""
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache-2026.07.2,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache-dp3cuda2,sharing=locked \
    --mount=type=secret,id=spack_oci_username,required=false \
    --mount=type=secret,id=spack_oci_password,required=false \
    mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache}; \
    arch=$(uname -m); \
    spack_target="${SPACK_TARGET}"; \
    if [ -z "${spack_target}" ]; then \
      case "$arch" in \
        x86_64) spack_target=x86_64_v2 ;; \
        aarch64) spack_target=aarch64 ;; \
        *) spack_target="$arch" ;; \
      esac; \
    fi; \
    echo "SPACK_TARGET=${spack_target} <- (uname -m)=$arch"; \
    echo "CUDA_ARCH=${CUDA_ARCH:-<empty/cpu-only>} CUDA_VERSION=${CUDA_VERSION}"; \
    spack config add "config:install_tree:root:/opt/software"; \
    spack config add "concretizer:unify:when_possible"; \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack config add "config:misc_cache:/opt/spack-misc-cache"; \
    spack config add "packages:casacore:variants: +data+python"; \
    spack config add "packages:all:target:[${spack_target}]"; \
    # py-pandas +performance pulls py-numba → py-llvmlite → llvm (~12GB).
    # Numba is optional for pandas; ~performance matches swf8-jupyter and
    # keeps LLVM out of the install tree / runtime image.
    if [ -n "${CUDA_ARCH}" ]; then \
        DP3_REQUIRE="@${DP3_VERSION}+idg+cuda cuda_arch=${CUDA_ARCH}"; \
        IDG_REQUIRE="+cuda"; \
        WSCLEAN_REQUIRE="~mpi+cuda"; \
    else \
        DP3_REQUIRE="@${DP3_VERSION}+idg~cuda"; \
        IDG_REQUIRE="~cuda"; \
        WSCLEAN_REQUIRE="~mpi~cuda"; \
    fi; \
    python3 -c "import yaml,sys;p='/opt/spack_env/spack.yaml';f=open(p);c=yaml.safe_load(f);f.close();\
    pkgs=c.setdefault('spack',{}).setdefault('packages',{});\
    [pkgs.setdefault(k,{}).update({'require':v}) for k,v in [\
        ('py-numpy','@${NUMPY_VERSION}'),\
        ('py-scipy','@${SCIPY_VERSION}'),\
        ('py-matplotlib','@${MATPLOTLIB_VERSION}'),\
        ('py-h5py','@${H5PY_VERSION}'),\
        ('py-pandas','@${PANDAS_VERSION} ~performance'),\
        ('py-xarray','@${XARRAY_VERSION}'),\
        ('py-bdsf','@${BDSF_VERSION}'),\
        ('py-reproject','@${REPROJECT_VERSION}'),\
        ('py-tables','@3.9.2'),\
        ('py-numexpr','@2.10.2:'),\
        ('py-losoto','@2.6:'),\
        ('py-lsmtool','@1.6.2:'),\
        ('py-astropy','@${ASTROPY_VERSION}'),\
        ('rust','@1.81.0:'),\
        ('dp3',sys.argv[1]),\
        ('idg',sys.argv[2]),\
        ('everybeam','@${EVERYBEAM_VERSION}+python'),\
        ('aoflagger','@${AOFLAGGER_VERSION}'),\
        ('casacore','@${CASACORE_VERSION}+python+data+dysco~hdf5~mpi~openmp'),\
        ('py-casacore','@${CASACORE_VERSION}'),\
        ('cfitsio','@${CFITSIO_VERSION}+bzip2+fortran+utils'),\
        ('hdf5','@${HDF5_VERSION}+hl~mpi+threadsafe'),\
        ('boost','@${BOOST_VERSION}+test+python+numpy'),\
        ('wsclean',sys.argv[3])]];\
    c['spack']['view']={'default':{'root':'/opt/view'}};\
    f=open(p,'w');yaml.dump(c,f,default_flow_style=False);f.close()" \
      "${DP3_REQUIRE}" "${IDG_REQUIRE}" "${WSCLEAN_REQUIRE}"; \
    if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
        spack mirror add --autopush --unsigned mycache file:///opt/buildcache; \
    fi; \
    if [ -n "${SPACK_MIRROR_OCI}" ]; then \
        if [ -f /run/secrets/spack_oci_username ] && [ -f /run/secrets/spack_oci_password ]; then \
            SPACK_OCI_USERNAME="$(cat /run/secrets/spack_oci_username)"; \
            export SPACK_OCI_PASSWORD="$(cat /run/secrets/spack_oci_password)"; \
            spack mirror add --autopush --unsigned \
                --oci-username "${SPACK_OCI_USERNAME}" \
                --oci-password-variable SPACK_OCI_PASSWORD \
                oci-push "${SPACK_MIRROR_OCI}"; \
        else \
            spack mirror add --unsigned oci-cache "${SPACK_MIRROR_OCI}"; \
        fi; \
    fi; \
    spack mirror add v1.1.1 https://binaries.spack.io/v1.1.1; \
    spack buildcache keys --install --trust || true; \
    if [ -n "${CUDA_ARCH}" ]; then \
        spack add "cuda@${CUDA_VERSION}"; \
    fi; \
    spack add \
    'python@'$PYTHON_VERSION \
    'py-pip' \
    'karabo.py-rapthor@'$RAPTHOR_VERSION \
    'py-ska-sdp-benchmark-monitor@0.1.0' \
    'py-ska-sdp-ical@main' \
    && \
    rm -f /opt/spack_env/spack.lock && \
    spack concretize --force && \
    python3 -c "import json,sys;d=json.load(open('/opt/spack_env/spack.lock'));\
    t=['py-rapthor','py-numpy','py-scipy','py-matplotlib','py-astropy',\
       'py-casacore','casacore','py-h5py','py-pandas','py-xarray',\
       'py-bdsf','py-reproject','py-losoto','py-lsmtool',\
       'dp3','everybeam','aoflagger','wsclean','py-toil'];\
    names={s.get('name') for s in d.get('concrete_specs',{}).values()};\
    c={};[c.setdefault(s.get('name'),[]).append(0) for s in d.get('concrete_specs',{}).values()];\
    e=[x for x in t if len(c.get(x,[]))>1];\
    bloated=sorted(names & {'llvm','py-llvmlite','py-numba'});\
    print(f'Duplicate packages found: {e}') or sys.exit(1) if e else print('No duplicate packages, OK');\
    print(f'LLVM stack present (should be empty): {bloated}') or sys.exit(1) if bloated else print('No LLVM/numba stack, OK')" && \
    if [ -n "${CUDA_ARCH}" ]; then \
        # Install CUDA first and expose driver stubs so DP3/IDG/WSClean can link
        # without a GPU present in the build environment.
        spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error cuda && \
        CUDA_ROOT=$(spack location -i cuda) && \
        if [ -d "${CUDA_ROOT}/lib64/stubs" ]; then \
            LIB_DIR="${CUDA_ROOT}/lib64"; \
        elif [ -d "${CUDA_ROOT}/lib/stubs" ]; then \
            LIB_DIR="${CUDA_ROOT}/lib"; \
        else \
            echo "ERROR: CUDA stubs directory not found in ${CUDA_ROOT}" >&2; \
            exit 1; \
        fi && \
        echo "Found CUDA stubs at ${LIB_DIR}/stubs" && \
        mkdir -p "/usr/lib/${arch}-linux-gnu" && \
        ln -sf "${LIB_DIR}/stubs/libcuda.so" "${LIB_DIR}/stubs/libcuda.so.1" && \
        ln -sf "${LIB_DIR}/stubs/libcuda.so" "/usr/lib/${arch}-linux-gnu/libcuda.so.1" && \
        for lib in "${LIB_DIR}"/libcudart.so*; do \
            ln -sf "${lib}" "/usr/lib/${arch}-linux-gnu/$(basename "${lib}")"; \
        done; \
    fi && \
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    spack gc -y && \
    # Static archives are only needed at link time; the shared libs
    # copied into the runtime image already satisfy everything at
    # runtime. Removing them trims several GB with no functional risk.
    find /opt/software -name '*.a' -delete && \
    # Belt-and-suspenders: llvm is build/link-only for llvmlite (statically
    # linked). Never ship the ~12GB prefix even if concretize misses it.
    rm -rf /opt/software/*/llvm-* && \
    if [ -n "${CUDA_ARCH}" ]; then \
        CUDA_ROOT=$(spack location -i cuda) && \
        rm -rf "${CUDA_ROOT}"/nsight-compute-* "${CUDA_ROOT}"/nsight-systems-* \
               "${CUDA_ROOT}"/libnvvp "${CUDA_ROOT}"/extras \
               "${CUDA_ROOT}"/nsightee_plugins "${CUDA_ROOT}"/compute-sanitizer; \
        mkdir -p /opt/cuda-export && \
        cp -a /usr/lib/${arch}-linux-gnu/libcuda.so.1 /opt/cuda-export/ && \
        cp -a /usr/lib/${arch}-linux-gnu/libcudart.so* /opt/cuda-export/ || true; \
    else \
        mkdir -p /opt/cuda-export && touch /opt/cuda-export/.cpu-only; \
    fi && \
    spack env view regenerate && \
    /opt/view/bin/pip install --no-cache-dir jupyterlab notebook ipykernel 'requests>=2.32' packaging && \
    fix-permissions /opt/view /opt/spack_env /opt/software

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
# Always present: either real CUDA libs or a .cpu-only marker (avoids COPY wildcard failure).
COPY --from=builder /opt/cuda-export/ /opt/cuda-export/

ARG CUDA_ARCH=""
ARG CUDA_VERSION=12.2.2

RUN arch=$(uname -m) && \
    mkdir -p /usr/lib/${arch}-linux-gnu /opt/cuda-stub && \
    if [ ! -f /opt/cuda-export/.cpu-only ]; then \
        cp -a /opt/cuda-export/libcuda.so.1 /opt/cuda-stub/ && \
        chmod 755 /opt/cuda-stub/libcuda.so.1 && \
        chmod -R a+rX /opt/cuda-stub && \
        cp -a /opt/cuda-export/libcudart.so* /usr/lib/${arch}-linux-gnu/; \
    fi

ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1
# Propagate CUDA build identity into the runtime image (empty => CPU-only).
ENV CUDA_ARCH=${CUDA_ARCH} \
    CUDA_VERSION=${CUDA_VERSION}

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
    printf "%s\n" "/opt/view/lib" "/opt/view/lib64" "/usr/lib/${arch}-linux-gnu" "/opt/cuda-stub" \
      > /etc/ld.so.conf.d/spack-view.conf && \
    ldconfig

# Set PATH for non-login shells
ENV PATH="/opt/view/bin:${PATH}"

# Kubernetes execution support is installed and patched by the py-toil and
# py-rapthor Spack overlay packages, so every Rapthor workload gets the same
# behavior without mutating installed site-packages at image build time.

# Basic tests
RUN shopt -s nullglob && llvm_prefs=(/opt/software/*/llvm-*) && \
    test ${#llvm_prefs[@]} -eq 0 && \
    python -c "import numpy; print('numpy', numpy.__version__, 'OK')" && \
    python -c "import scipy; print('scipy', scipy.__version__, 'OK')" && \
    python -c "import pandas; print('pandas', pandas.__version__, 'OK')" && \
    python -c "import casacore, casacore.tables; print('python-casacore OK')" && \
    python -c "import kubernetes; print('kubernetes', kubernetes.__version__, 'OK')" && \
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
    python -c "import rapthor; print('rapthor OK')" && \
    rapthor --version && \
    DP3 --version && \
    if [ -n "${CUDA_ARCH}" ]; then \
      python -c "import ctypes,os,sys; major=os.environ.get('CUDA_VERSION','').split('.')[0]; libs=['libcudart.so']+([f'libcudart.so.{major}'] if major else []);\
[ctypes.CDLL(lib) or print(f'SUCCESS: {lib} loaded') for lib in libs]; print('DP3 CUDA runtime libs OK')"; \
    fi

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PYTHON_VERSION=3.12

RUN python -m pip install --no-cache-dir git+https://github.com/NERSC/slurm-magic.git

# KubeSpawner runs `jupyterhub-singleuser`; install Marimo and its JupyterLab
# extension into the Spack Python environment that provides JupyterLab.
RUN python -m pip install --no-cache-dir \
    "jupyterhub==4.1.6" \
    "marimo[sandbox]>=0.19.11" \
    "marimo-jupyter-extension>=0.1.4" \
    "progressbar" \
    "backports.shutil_get_terminal_size" \
    "requests>=2.32,<=2.32.5" && \
    ln -sf "$(command -v marimo)" /usr/local/bin/marimo && \
    ln -sf "$(command -v jupyterhub-singleuser)" /usr/local/bin/jupyterhub-singleuser && \
    python -c 'import jupyterhub; assert jupyterhub.__version__ == "4.1.6", jupyterhub.__version__' && \
    jupyterhub-singleuser --help >/dev/null && \
    marimo --version && \
    python -c "import everybeam" && \
    python -m pip check 2>&1 | tee /tmp/pip-check.txt; \
    if grep -E 'requires |has requirement' /tmp/pip-check.txt | grep -v everybeam; then \
      echo "pip check failed (excluding Spack-provided everybeam)" >&2; exit 1; \
    fi

RUN install -d -o ${NB_UID} -g ${NB_GID} /home/${NB_USER}/.astropy/cache

USER ${NB_UID}

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
