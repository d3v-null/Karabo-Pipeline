# syntax=docker/dockerfile:1.6
# run me:
# docker build -t d3vnull0/oskar:latest -f oskar.Dockerfile .
# docker run --rm -it d3vnull0/oskar:latest bash -lc ". /opt/spack/share/spack/setup-env.sh && spack env activate /opt/spack_env && oskar_sim_interferometer --help && python -c 'import oskar; print(oskar.__version__)'"
FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6

# Minimal OSKAR-only build for testing OSKAR installation and test suite
USER root
SHELL ["/bin/bash", "-lc"]

# Remove conda to avoid library conflicts
RUN rm -f /usr/local/bin/before-notebook.d/10activate-conda-env.sh || true; \
    rm -rf /opt/conda || true

# Essential system dependencies for OSKAR build
# NOTE: Avoid BuildKit cache mounts here; they have triggered Spack lock/cache issues in this environment.
RUN apt-get update && apt-get --no-install-recommends install -y \
        build-essential \
        ca-certificates \
        cmake \
        curl \
        file \
        gfortran \
        git \
        libcurl4-openssl-dev \
        patchelf \
        pkg-config \
        wget \
        zstd \
    ;

ENV DEBIAN_FRONTEND=noninteractive

# Install Spack and detect compilers (match sp5505.Dockerfile)
ENV SPACK_ROOT=/opt/spack \
    SPACK_DISABLE_LOCAL_CONFIG=1
RUN git clone --depth=1 --single-branch --branch=v1.1.0 https://github.com/spack/spack.git ${SPACK_ROOT} && \
    cd ${SPACK_ROOT} && \
    rm -rf .git && \
    # Spack v1.1.0 ships some dangling symlinks in docs assets which can cause
    # `fix-permissions` (from the Jupyter base image) to fail the build.
    find ${SPACK_ROOT}/lib/spack/docs -xtype l -delete || true && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env create --dir /opt/spack_env && \
    fix-permissions ${SPACK_ROOT} /opt/spack_env

RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    spack compiler find && \
    spack compiler list

# Add SKA SDP Spack repo for OSKAR and related packages (match sp5505.Dockerfile)
RUN git clone --depth=1 --single-branch --branch=2026.02.1 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
    rm -rf /opt/ska-sdp-spack/.git && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack -e /opt/spack_env repo add /opt/ska-sdp-spack

# Add our custom OSKAR package with test methods
COPY spack-overlay /opt/karabo-spack
RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack -e /opt/spack_env repo add /opt/karabo-spack && \
    # Debug: show repo order + available OSKAR versions so concretize failures are obvious in logs
    spack -e /opt/spack_env repo list && \
    spack -e /opt/spack_env versions oskar

# Version variables matching main Dockerfile
ARG OSKAR_VERSION=2.12.0
ARG NUMPY_VERSION=1.23.5
ARG HDF5_VERSION=1.12.3

# Create Spack environment and install minimal OSKAR dependencies
# NOTE: Avoid BuildKit cache mounts here; they have triggered Spack lock/cache issues in this environment.
RUN . ${SPACK_ROOT}/share/spack/setup-env.sh; \
    spack env activate /opt/spack_env; \
    mkdir -p /opt/{software,view,buildcache,spack-source-cache}; \
    spack config add "config:install_tree:root:/opt/software"; \
    spack config add "concretizer:unify:when_possible"; \
    spack config add "view:/opt/view"; \
    spack config add "config:source_cache:/opt/spack-source-cache"; \
    spack mirror add --autopush --unsigned mycache file:///opt/buildcache; \
    spack buildcache keys --install --trust || true; \
    # Install minimal dependencies for OSKAR
    spack add \
        'hdf5@'$HDF5_VERSION'+hl~mpi' \
        'oskar@'$OSKAR_VERSION'~cuda~openmp~mpi+opencl+casacore+python+hdf5' \
        'py-numpy@'$NUMPY_VERSION \
        'python@3.10' \
    && \
    spack concretize --force && \
    spack install --no-check-signature --no-checksum --fail-fast && \
    spack test run oskar && \
    spack test run casacore && \
    spack test run hdf5 && \
    spack test run py-numpy && \
    spack test run fftw

# Set up environment for runtime
ENV BASH_ENV=/opt/etc/spack_env \
    PYTHONNOUSERSITE=1 \
    CMAKE_PREFIX_PATH="/opt/view:${CMAKE_PREFIX_PATH}" \
    PKG_CONFIG_PATH="/opt/view/lib/pkgconfig:/opt/view/lib64/pkgconfig:${PKG_CONFIG_PATH}"

# Set up shell environment to use Spack view
RUN mkdir -p /opt/etc && \
    echo '. /opt/spack/share/spack/setup-env.sh' > /opt/etc/spack_env && \
    echo 'spack env activate /opt/spack_env' >> /opt/etc/spack_env && \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && spack env activate /opt/spack_env && spack env view regenerate

# Install OSKAR Python bindings and test them
RUN --mount=type=cache,target=/root/.cache/pip \
    . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    echo "Testing OSKAR import..." && \
    python -c "import oskar; print(f'OSKAR import successful, version: {getattr(oskar, \"__version__\", \"unknown\")}')"

# Final verification tests
RUN . ${SPACK_ROOT}/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    echo "=== Final OSKAR Verification ===" && \
    echo "Testing OSKAR executables:" && \
    which oskar_sim_interferometer && echo "✓ oskar_sim_interferometer found" && \
    which oskar_imager && echo "✓ oskar_imager found" && \
    echo "Testing OSKAR Python import:" && \
    python -c "import oskar; print('✓ OSKAR Python module imported successfully')" && \
    echo "=== OSKAR Installation Complete ==="

# Set default user back to jovyan
USER ${NB_UID}
WORKDIR /home/${NB_USER}

# Default command
CMD ["bash"]
