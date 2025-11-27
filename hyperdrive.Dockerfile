# syntax=docker/dockerfile:1.6
# Minimal image to run mwa_hyperdrive
# Build:
#   docker build -t karabo-hyperdrive:latest -f hyperdrive.Dockerfile .

FROM quay.io/jupyter/minimal-notebook:notebook-7.2.2

USER root
SHELL ["/bin/bash", "-lc"]

# Remove conda to avoid interference
RUN rm -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh || true; \
    rm -rf /opt/conda || true

# System libs required by spack and hyperdrive runtime
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        file \
        gfortran \
        git \
        patchelf \
        pkg-config \
        wget \
        zstd \
    ;

# Install Rust
ARG RUST_VERSION=1.81.0
ENV CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain $RUST_VERSION --no-modify-path && \
    ln -sf /opt/cargo/bin/* /usr/local/bin/ && \
    rustc --version | grep -Fq "$RUST_VERSION"

ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    DEBIAN_FRONTEND=noninteractive

# Install Spack v0.23 and detect compilers
RUN git clone --depth=2 --branch=releases/v0.23 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack compiler find && \
    spack external find rust && \
    spack external find git && \
    spack external find pkgconf

# Copy spack overlay
COPY spack-overlay/repo.yaml /opt/karabo-spack/repo.yaml
COPY spack-overlay/packages/hyperdrive /opt/karabo-spack/packages/hyperdrive
RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && spack repo add /opt/karabo-spack

ARG NUMPY_VERSION=1.23.5
ARG PYTHON_VERSION=3.10
ARG MATPLOTLIB_VERSION=3.9.2

# Create Spack environment and install deps
ARG SPACK_TARGET=""

RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache,sharing=locked \
    . ${SPACK_ROOT}/share/spack/setup-env.sh; \
    mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache}; \
    spack env create --dir /opt/spack_env; \
    spack env activate /opt/spack_env; \
    arch=$(uname -m); \
    if [ -z "${SPACK_TARGET}" ]; then \
      case "$arch" in \
        x86_64) SPACK_TARGET=x86_64 ;; \
        aarch64) SPACK_TARGET=aarch64 ;; \
        *) SPACK_TARGET="$arch" ;; \
      esac; \
    fi; \
    echo "SPACK_TARGET=${SPACK_TARGET} <- (uname -m)=$arch"; \
    spack config add "config:install_tree:root:/opt/software"; \
    spack config add "concretizer:unify:when_possible"; \
    spack config add "concretizer:reuse:true"; \
    spack config add "view:/opt/view"; \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack config add "config:misc_cache:/opt/spack-misc-cache"; \
    spack config add "packages:all:target:[${SPACK_TARGET}]"; \
    spack mirror add --autopush --unsigned mycache file:///opt/buildcache; \
    spack buildcache keys --install --trust || true; \
    spack add \
        'py-matplotlib@'$MATPLOTLIB_VERSION \
        'py-numpy@'$NUMPY_VERSION \
        'py-pip@:25.2' \
        'python@'$PYTHON_VERSION \
        'hyperdrive' \
    && \
    spack concretize --force && \
    ac_cv_lib_curl_curl_easy_init=no spack install --no-check-signature --no-checksum --fail-fast --reuse --show-log-on-error && \
    spack gc -y && \
    spack env view regenerate && \
    fix-permissions /opt/view /opt/spack_env /opt/software /opt/view

# Make Spack view default in system paths and shells
RUN printf "/opt/view/lib\n/opt/view/lib64\n" > /etc/ld.so.conf.d/spack-view.conf && ldconfig && \
    echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh && \
    mkdir -p /opt/etc && \
    echo ". /etc/profile.d/spack.sh" > /opt/etc/spack_env && \
    chmod 644 /opt/etc/spack_env

ENV PATH="/opt/view/bin:${PATH}" \
    LD_LIBRARY_PATH="/opt/view/lib:/opt/view/lib64" \
    BASH_ENV=/opt/etc/spack_env \
    PYTHONNOUSERSITE=1 \
    CMAKE_PREFIX_PATH="/opt/view" \
    PKG_CONFIG_PATH="/opt/view/lib/pkgconfig:/opt/view/lib64/pkgconfig" \
    PYTHONPATH="/opt/view/lib/python${PYTHON_VERSION}/site-packages"

# Ensure start-notebook uses Spack jupyter first in PATH
RUN mkdir -p /usr/local/bin/before-notebook.d && \
    printf '#!/usr/bin/env bash\nPATH="/opt/view/bin:${HOME}/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\nexport PATH\nLD_LIBRARY_PATH="/opt/view/lib:/opt/view/lib64"\nexport LD_LIBRARY_PATH\nPYTHONPATH=/opt/view/lib/python${PYTHON_VERSION}/site-packages\nexport PYTHONPATH\n' > /usr/local/bin/before-notebook.d/00-prefer-spack.sh && \
    chmod +x /usr/local/bin/before-notebook.d/00-prefer-spack.sh && \
    # Remove conda and activation hook; we run Jupyter inside Spack Python
    rm -f /opt/conda /usr/local/bin/before-notebook.d/10activate-conda-env.sh || true

RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    spack test run 'py-matplotlib' && \
    spack test run 'py-numpy' && \
    spack test run 'hyperdrive'

RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    python - <<"PY"
import importlib, sys, os
print(f'PYTHONPATH: {sys.path}')
print(f'LD_LIBRARY_PATH: {os.environ.get("LD_LIBRARY_PATH")}')
print(f'PATH: {os.environ.get("PATH")}')
print(f'BASH_ENV: {os.environ.get("BASH_ENV")}')
print(f'PYTHONNOUSERSITE: {os.environ.get("PYTHONNOUSERSITE")}')
print(f'CMAKE_PREFIX_PATH: {os.environ.get("CMAKE_PREFIX_PATH")}')
print(f'PKG_CONFIG_PATH: {os.environ.get("PKG_CONFIG_PATH")}')
PY

# Quick verification at build time (non-zero power expected)
ENV MWA_BEAM_FILE=/opt/mwa_full_embedded_element_pattern.h5
RUN wget -O$MWA_BEAM_FILE http://ws.mwatelescope.org/static/mwa_full_embedded_element_pattern.h5

USER ${NB_UID}
WORKDIR /home/${NB_USER}
