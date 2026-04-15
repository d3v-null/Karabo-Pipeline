# Minimal Jupyter notebook with Rapthor pipeline
# Based on quay.io/jupyter/minimal-notebook with Spack-installed rapthor dependencies
# build: docker build . -f rapthor-jupyter.Dockerfile --tag rapthor-jupyter:latest
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
    patchelf \
    perl \
    pkg-config \
    time \
    wget \
    zstd

# Install Spack and detect compilers
ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1
RUN git clone --depth=1 --single-branch --branch=v1.1.0 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    cd ${SPACK_ROOT} && \
    rm -rf .git && \
    find ${SPACK_ROOT}/lib/spack/docs -xtype l -delete || true && \
    . share/spack/setup-env.sh && \
    spack env create --dir /opt/spack_env && \
    fix-permissions ${SPACK_ROOT} /opt/spack_env

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
    perl \
    pkgconf

# Add SKA SDP Spack repo and Karabo overlay for rapthor
RUN git clone --depth=1 --single-branch --branch=2026.02.5 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
    rm -rf /opt/ska-sdp-spack/.git && \
    spack repo add /opt/ska-sdp-spack
COPY spack-overlay /opt/karabo-spack
RUN spack repo add /opt/karabo-spack

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
ARG BDSF_VERSION=1.13.0.20251010
ARG AOFLAGGER_VERSION=3.4.0
ARG WSCLEAN_VERSION=3.6.20260109
ARG EVERYBEAM_VERSION=0.8.0.20251125
ARG DP3_VERSION=6.5.1.20260109
ARG RAPTHOR_VERSION=2.1.20260216

ARG SPACK_TARGET=""
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache,sharing=locked \
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
    spack config add "config:install_tree:root:/opt/software"; \
    spack config add "concretizer:unify:when_possible"; \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack config add "config:misc_cache:/opt/spack-misc-cache"; \
    spack config add "packages:casacore:variants: +data+python"; \
    spack config add "packages:all:target:[${spack_target}]"; \
    python3 -c "import yaml,sys;p='/opt/spack_env/spack.yaml';f=open(p);c=yaml.safe_load(f);f.close();\
    pkgs=c.setdefault('spack',{}).setdefault('packages',{});\
    [pkgs.setdefault(k,{}).update({'require':v}) for k,v in [\
        ('py-numpy','@${NUMPY_VERSION}'),\
        ('py-scipy','@${SCIPY_VERSION}'),\
        ('py-matplotlib','@${MATPLOTLIB_VERSION}'),\
        ('py-h5py','@${H5PY_VERSION}'),\
        ('py-pandas','@${PANDAS_VERSION}'),\
        ('py-xarray','@${XARRAY_VERSION}'),\
        ('py-bdsf','@${BDSF_VERSION}'),\
        ('py-reproject','@${REPROJECT_VERSION}'),\
        ('py-tables','@3.9.2'),\
        ('py-numexpr','@2.10.2:'),\
        ('py-losoto','@2.6:'),\
        ('py-lsmtool','@1.6.2:'),\
        ('py-astropy','@${ASTROPY_VERSION}'),\
        ('dp3','@${DP3_VERSION}+idg'),\
        ('idg','~cuda'),\
        ('everybeam','@${EVERYBEAM_VERSION}+python'),\
        ('aoflagger','@${AOFLAGGER_VERSION}'),\
        ('casacore','@${CASACORE_VERSION}+python+data+dysco~hdf5~mpi~openmp'),\
        ('py-casacore','@${CASACORE_VERSION}'),\
        ('cfitsio','@${CFITSIO_VERSION}+bzip2+fortran+utils'),\
        ('hdf5','@${HDF5_VERSION}+hl~mpi+threadsafe'),\
        ('boost','@${BOOST_VERSION}+test+python+numpy'),\
        ('wsclean','~mpi~cuda')]];\
    c['spack']['view']={'default':{'root':'/opt/view'}};\
    f=open(p,'w');yaml.dump(c,f,default_flow_style=False);f.close()"; \
    if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
        spack mirror add --autopush --unsigned mycache file:///opt/buildcache; \
        spack buildcache update-index /opt/buildcache || true; \
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
    spack mirror add v1.1.0 https://binaries.spack.io/v1.1.0; \
    spack buildcache keys --install --trust || true; \
    spack add \
    'python@'$PYTHON_VERSION \
    'py-pip' \
    'py-rapthor@'$RAPTHOR_VERSION \
    'py-ska-sdp-ical@main' \
    && \
    spack concretize --force && \
    python3 -c "import json,sys;d=json.load(open('/opt/spack_env/spack.lock'));\
    t=['py-rapthor','py-numpy','py-scipy','py-matplotlib','py-astropy',\
       'py-casacore','casacore','py-h5py','py-pandas','py-xarray',\
       'py-bdsf','py-reproject','py-losoto','py-lsmtool',\
       'dp3','everybeam','aoflagger','wsclean','py-toil'];\
    c={};[c.setdefault(s.get('name'),[]).append(0) for s in d.get('concrete_specs',{}).values()];\
    e=[x for x in t if len(c.get(x,[]))>1];\
    print(f'Duplicate packages found: {e}') or sys.exit(1) if e else print('No duplicate packages, OK')" && \
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    spack gc -y && \
    spack env view regenerate && \
    /opt/view/bin/pip install jupyterlab notebook ipykernel 'requests>=2.32' packaging && \
    if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
        spack buildcache update-index /opt/buildcache || true; \
    fi && \
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
    libcurl4-openssl-dev \
    libgomp1 \
    time \
    wget \
    zstd

COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /opt/._view /opt/._view
COPY --from=builder /opt/spack_env /opt/spack_env
COPY --from=builder /opt/spack /opt/spack
COPY --from=builder /opt/ska-sdp-spack /opt/ska-sdp-spack
COPY --from=builder /opt/karabo-spack /opt/karabo-spack

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

# Basic tests
RUN python -c "import numpy; print('numpy', numpy.__version__, 'OK')" && \
    python -c "import scipy; print('scipy', scipy.__version__, 'OK')" && \
    python -c "import casacore, casacore.tables; print('python-casacore OK')" && \
    python -c "import rapthor; print('rapthor OK')" && \
    rapthor --version

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PYTHON_VERSION=3.12

RUN python -m pip install git+https://github.com/NERSC/slurm-magic.git

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
