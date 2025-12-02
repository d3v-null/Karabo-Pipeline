# syntax=docker/dockerfile:1.6
FROM quay.io/jupyter/minimal-notebook:notebook-7.2.2
# FROM spack/ubuntu-jammy:0.23.0

# Install Karabo via spack with conda environment structure
USER root

# Install system dependencies needed for spack
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && apt-get --no-install-recommends install -y \
    wget cmake libcfitsio-dev git build-essential python3-dev gfortran && \
    apt-get clean

ENV SPACK_ROOT=/opt/spack

# Setup Spack with compatible version, v0.23 is recommended in the readme for ska-sdp-spack
# comment out this step if spack is already installed
RUN git clone --depth=2 --branch=releases/v0.23 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    cd ${SPACK_ROOT} && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack compiler find

# Clone the custom Spack repository from GitLab
# can check for updates with git ls-remote https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git
RUN git clone --depth=2 --branch=2025.07.3 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
    cd /opt/ska-sdp-spack && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack repo add /opt/ska-sdp-spack

# Create Spack environment and install core dependencies
# these package names need to be in quotes!!
# TODO, later: spack mirror add mycache file:///opt/buildcache
RUN --mount=type=cache,target=/opt/buildcache,id=spack-cache,sharing=locked \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    mkdir -p /opt/{software,spack_env,view} && \
    spack env create --dir /opt/spack_env && \
    spack env activate /opt/spack_env && \
    spack config add "config:install_tree:root:/opt/software" && \
    spack config add "concretizer:unify:when_possible" && \
    for pkg in \
    'python@3.10' \
    'openblas@:0.3.27' \
    'mpich' \
    'boost+python+numpy' \
    'py-scipy@=1.9.3' \
    'py-pandas@=1.5.3' \
    'py-numpy@=1.23.5' \
    'py-matplotlib@=3.6.3' \
    'py-h5py@=3.7.0' \
    'py-pip@=22.1.2' \
    'py-setuptools@=59.4.0' \
    'py-wheel@=0.37.1' \
    'py-pybind11@=2.13.5' \
    'py-pytest' \
    ; do \
    echo "-> adding $pkg"; \
    spack add "$pkg" && \
    spack concretize --force || (echo "spack concretize failed for $pkg" && exit 1); \
    done && \
    spack install --no-check-signature --no-cache --fail-fast
    # above must be in quotes

# Install additional packages via pip in spack environment (with fallback)
RUN --mount=type=cache,target=/root/.cache/pip \
    (. ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    python -m pip install --no-build-isolation \
    ducc0 numexpr requests tqdm healpy \
    git+https://github.com/i4Ds/eidos.git@74ffe0552079486aef9b413efdf91756096e93e7 \
    git+https://github.com/ska-sa/katbeam.git@5ce6fcc35471168f4c4b84605cf601d57ced8d9e \
    dask_mpi rfc3986 mpi4py tools21cm extension_helpers \
    astropy cython setuptools_scm setuptools) || \
    echo "Spack pip install failed, will use conda fallback"

# Install OSKAR manually (with fallback)
RUN --mount=type=cache,target=/root/.cache/pip \
    (. ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    git clone 'https://github.com/OxfordSKA/OSKAR.git' /opt/oskar && \
    cd /opt/oskar/ && \
    git checkout '2.10.0' && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/opt/software -DCMAKE_BUILD_TYPE=Release .. && \
    make -j1 && \
    make install && \
    export OSKAR_INC_DIR=/opt/software/include && \
    export OSKAR_LIB_DIR=/opt/software/lib && \
    python -m pip install --no-build-isolation '/opt/oskar/python') || \
    echo "OSKAR installation failed, will use conda fallback"

# Now create conda-style karabo environment structure (for compatibility)
RUN --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=cache,target=/root/.cache/pip \
    conda install -y -n base conda-libmamba-solver && \
    conda config --set solver libmamba && \
    conda create -y -n karabo python=3.10 && \
    # Install karabo-pipeline using conda (fallback from spack)
    conda install -y -n karabo -c i4ds -c conda-forge -c "nvidia/label/cuda-11.7.1" karabo-pipeline pyuvdata || true && \
    # Ensure OSKAR can find CUDA runtime (if available)
    conda install -y -n karabo -c "nvidia/label/cuda-11.7.1" cuda-cudart=11.7.* 2>/dev/null || true && \
    # Create CUDA 10 env for OSKAR compatibility
    conda create -y -n cuda10 -c defaults cudatoolkit=10.2 2>/dev/null || true && \
    # Ensure jovyan can use environments created by root
    chown -R ${NB_UID}:${NB_GID} /opt/conda && \
    fix-permissions /opt/conda

# Setup library paths and symlinks
RUN printf "/opt/view/lib\n/opt/software/lib\n/opt/conda/envs/karabo/lib\n/opt/conda/envs/cuda10/lib\n/opt/conda/lib\n" > /etc/ld.so.conf.d/conda.conf && \
    ldconfig && \
    # Symlink CUDA libs if they exist
    bash -lc 'set -euo pipefail; for so in libcufft.so.10 libcudart.so.10 libcurand.so.10; do \
      for f in /opt/conda/envs/cuda10/lib/${so}*; do \
        if [ -e "$f" ]; then ln -sf "$f" /opt/conda/envs/karabo/lib/; fi; \
      done; \
    done' 2>/dev/null || true && \
    ldconfig && \
    fix-permissions /home/$NB_USER

# Workaround JupyterLab extension-manager crash
RUN conda run -n base python -m pip install --no-cache-dir "httpx<0.28"

# Set environment variables (with spack fallback)
ENV PATH="/opt/view/bin:/opt/software/bin:/opt/conda/envs/karabo/bin:${PATH}" \
    LD_LIBRARY_PATH="/opt/view/lib:/opt/software/lib:/opt/conda/envs/karabo/lib:/opt/conda/envs/cuda10/lib:/opt/conda/lib" \
    OSKAR_CUDA_LIB_PATH="/opt/conda/envs/cuda10/lib"

# Copy repository for testing
COPY --chown=${NB_UID}:${NB_GID} . /home/${NB_USER}/Karabo-Pipeline
RUN fix-permissions /home/${NB_USER}/Karabo-Pipeline

# Setup conda auto-activation for karabo environment
RUN echo "source /opt/conda/etc/profile.d/conda.sh && conda activate karabo" >> /home/${NB_USER}/.bashrc && \
    mkdir -p /opt/etc && \
    echo "source /opt/conda/etc/profile.d/conda.sh && conda activate karabo" > /opt/etc/conda_init_script && \
    chmod 644 /opt/etc/conda_init_script && \
    chown -R ${NB_UID}:${NB_GID} /opt/etc /home/${NB_USER}

ENV BASH_ENV=/opt/etc/conda_init_script

# Setup spack environment activation (with error handling)
RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" >> /etc/profile.d/spack.sh && \
    echo "spack env activate /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

# Switch to jovyan user
USER ${NB_UID}

# Ensure ipykernel and local package are installed in karabo env and register kernel
RUN conda run -n karabo python -m pip install --no-cache-dir ipykernel pytest -e /home/${NB_USER}/Karabo-Pipeline && \
    conda run -n karabo python -m ipykernel install --user --name=karabo --display-name="Karabo (Python 3.10)"

# Download test data
# RUN conda run -n karabo python /home/${NB_USER}/Karabo-Pipeline/download_test_data.py

# Run tests
RUN conda run -n karabo pytest -x --tb=short /home/${NB_USER}/Karabo-Pipeline

# Set working directory
WORKDIR "/home/${NB_USER}"
