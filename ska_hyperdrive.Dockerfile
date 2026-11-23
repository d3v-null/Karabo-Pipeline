# hyperdrive (+CUDA, +EveryBeam for SKA-Low beams) from Alec Thomson's fork,
# on ska-sdp-spack + the karabo overlay's ska-hyperdrive package.
# docker build -f ska_hyperdrive.Dockerfile -t ska-hyperdrive .

ARG PYTHON_VERSION=3.11
ARG CUDA_VERSION=12.2.2
# T4/RTX2000, A100, RTX3000, L40, GH200.
ARG CUDA_ARCH="75,80,86,89,90"
ARG BASE_IMAGE=quay.io/jupyter/minimal-notebook:notebook-7.0.6

FROM ${BASE_IMAGE} AS builder

USER root
SHELL ["/bin/bash", "-lc"]

ARG CUDA_VERSION
ARG CUDA_ARCH
ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    autoconf \
    automake \
    build-essential \
    bison \
    bzip2 \
    ca-certificates \
    cmake \
    curl \
    diffutils \
    file \
    findutils \
    gfortran \
    git \
    libbz2-dev \
    libcurl4-openssl-dev \
    libltdl-dev \
    libtool \
    m4 \
    patchelf \
    perl \
    pkg-config \
    python3-yaml \
    zstd

# Rust from rustup, not spack (spack's rust build is very slow). The fork needs >= 1.88.
ARG RUST_VERSION=1.93.0
ENV CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup
RUN set -o pipefail && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain $RUST_VERSION --no-modify-path && \
    ln -sf /opt/cargo/bin/* /usr/local/bin/ && \
    rustc --version | grep -Fq "$RUST_VERSION"

# Spack v1.2.2 + builtin packages tag that ska-sdp-spack 2026.10.x targets.
# Keep conda off PATH: spack 1.2 needs os.O_PATH, which conda's python lacks.
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1 \
    SPACK_PYTHON=/usr/bin/python3
RUN git clone --depth=1 --single-branch --branch=v1.2.2 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    rm -rf ${SPACK_ROOT}/.git && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack repo set --scope site --destination /opt/spack-packages builtin && \
    spack repo update --scope site --tag v2026.06.0 builtin && \
    spack env create --dir /opt/spack_env --with-view /opt/view && \
    echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

RUN spack compiler find && \
    spack external find autoconf automake bzip2 git libtool m4 perl pkgconf rust

# ska-sdp-spack 2026.10.4 release commit (MR 446; switch to the tag once cut).
ARG SDP_SPACK_REF=7bc44cf1e1f4bec316b018a3e27db28b693d8d59
RUN git init -q /opt/ska-sdp-spack && \
    git -C /opt/ska-sdp-spack fetch -q --depth=1 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git "${SDP_SPACK_REF}" && \
    git -C /opt/ska-sdp-spack checkout -q FETCH_HEAD && \
    rm -rf /opt/ska-sdp-spack/.git && \
    spack repo add /opt/ska-sdp-spack
COPY spack-overlay /opt/karabo-spack
RUN spack repo add /opt/karabo-spack

ARG HYPERDRIVE_VERSION=0.11.0.20261120
# x86_64_v2: v3 segfaults in CI. Override for arm64 or newer CPUs.
ARG SPACK_TARGET=""

RUN --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    set -euo pipefail; \
    spack_target="${SPACK_TARGET}"; \
    if [ -z "${spack_target}" ]; then \
      case "$(uname -m)" in x86_64) spack_target=x86_64_v2 ;; *) spack_target="$(uname -m)" ;; esac; \
    fi; \
    spack config add "config:install_tree:root:/opt/software"; \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack config add "packages:all:target:[${spack_target}]"; \
    spack mirror add v1.2.2 https://binaries.spack.io/v1.2.2; \
    spack buildcache keys --install --trust || true; \
    spack add \
        "python@${PYTHON_VERSION}" \
        "py-pip" \
        "cuda@${CUDA_VERSION}" \
        "ska-hyperdrive@${HYPERDRIVE_VERSION}+cuda+everybeam cuda_arch=${CUDA_ARCH}" \
        "everybeam~python"; \
    spack concretize --force; \
    arch="$(uname -m)"; \
    # Install CUDA first and expose its driver-API stub (libcuda) to the linker,
    # so from-source CUDA code links. The real driver is injected at runtime on GPU hosts.
    spack install --use-cache --no-check-signature --fail-fast --show-log-on-error cuda; \
    CUDA_ROOT="$(spack location -i cuda)"; \
    if [ -d "${CUDA_ROOT}/lib64/stubs" ]; then LIB_DIR="${CUDA_ROOT}/lib64"; \
    else LIB_DIR="${CUDA_ROOT}/lib"; fi; \
    mkdir -p "/usr/lib/${arch}-linux-gnu"; \
    ln -sf "${LIB_DIR}/stubs/libcuda.so" "${LIB_DIR}/stubs/libcuda.so.1"; \
    ln -sf "${LIB_DIR}/stubs/libcuda.so" "/usr/lib/${arch}-linux-gnu/libcuda.so.1"; \
    for lib in "${LIB_DIR}"/libcudart.so*; do ln -sf "${lib}" "/usr/lib/${arch}-linux-gnu/$(basename "${lib}")"; done; \
    spack install --use-cache --no-check-signature --fail-fast --show-log-on-error; \
    spack gc -y; \
    # Static archives and build-only bits: not needed at runtime.
    find /opt/software -name '*.a' -delete; \
    spack env view regenerate; \
    CUDA_ROOT=$(spack location -i cuda); \
    rm -rf "${CUDA_ROOT}"/nsight-* "${CUDA_ROOT}"/libnvvp "${CUDA_ROOT}"/extras \
           "${CUDA_ROOT}"/compute-sanitizer "${CUDA_ROOT}"/gds* "${CUDA_ROOT}"/tools; \
    S=$(echo /opt/software/linux-*); \
    rm -rf $S/cmake-*; \
    find /opt/software /opt/view -xtype l -delete; \
    # libcuda stub, so hyperdrive starts on CPU-only hosts (real driver wins on GPU hosts).
    mkdir -p /opt/cuda-stub; \
    cp -L "$(ls -d ${CUDA_ROOT}/lib64/stubs ${CUDA_ROOT}/lib/stubs 2>/dev/null | head -1)/libcuda.so" /opt/cuda-stub/libcuda.so.1

# Jupyter server, JupyterHub single-user server and kernel all run from the
# spack python, not the base image's conda. jupyterhub matches the base image's
# 4.0.2 so the single-user server stays compatible with the same hub.
ARG JUPYTERHUB_VERSION=4.0.2
RUN /opt/view/bin/python -m pip install --no-cache-dir \
        "jupyterhub==${JUPYTERHUB_VERSION}" "jupyterlab>=4,<5" "notebook>=7,<8" ipykernel && \
    /opt/view/bin/python -c "import jupyterhub, jupyterlab, notebook, ipykernel; print('jupyter OK')"

FROM ${BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-lc"]

ARG PYTHON_VERSION

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    ca-certificates \
    libgomp1

COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /opt/cuda-stub /opt/cuda-stub

# Direct `docker run IMAGE hyperdrive` gets no spack activation, so use ldconfig.
# /opt/cuda-stub goes last: a fallback for libcuda.so.1 that must not mask the
# driver the NVIDIA runtime injects.
RUN arch=$(uname -m) && \
    printf "%s\n" /opt/view/lib /opt/view/lib64 "/usr/lib/${arch}-linux-gnu" /opt/cuda-stub \
        > /etc/ld.so.conf.d/spack-view.conf && \
    ldconfig

ENV PATH="/opt/view/bin:${PATH}"

# hyperdrive must actually link EveryBeam, or the SKA-Low beams aren't there.
RUN hyperdrive --version && \
    ! ldd "$(command -v hyperdrive)" | grep 'not found' && \
    ldd "$(command -v hyperdrive)" | grep -q libeverybeam

# Keep conda from shadowing /opt/view in the notebook start-up hook and shells.
RUN rm -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh && \
    sed -i '/^eval "\$(conda shell\.bash hook)"/d' /home/${NB_USER}/.bashrc /root/.bashrc 2>/dev/null || true

USER ${NB_UID}
RUN python -m ipykernel install --user --name=ska-hyperdrive --display-name="SKA hyperdrive (Spack Py${PYTHON_VERSION})" && \
    jupyter kernelspec list && \
    test "$(command -v jupyterhub-singleuser)" = /opt/view/bin/jupyterhub-singleuser && \
    jupyterhub-singleuser --version
