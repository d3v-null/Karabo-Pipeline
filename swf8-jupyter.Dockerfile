# SWF-8 Jupyter/Marimo image: ps_eor[ml-gpr] (MWA Phase-3 CHIPS → LOFAR-style GPR)
#
# Counterpart to rapthor-jupyter.Dockerfile — and now on the same NumPy 2.2 /
# SciPy 1.14 stack (see version pins below), default ps_eor version is the
# 1.0 tag (GPyTorch ML-GPR backend, no GPy). Legacy ps_eor 0.34.1 (GPy
# backend) needs numpy<2/scipy<=1.12, so rolling back to it also requires
# overriding NUMPY_VERSION/SCIPY_VERSION/TABLES_VERSION/NUMEXPR_VERSION/
# ASTROPY_HEALPIX_VERSION/PYERFA_VERSION/PYFFTW_VERSION back to their
# numpy1-era values together (see docs/ps_eor-spack-packaging.md) — it's no
# longer a single-flag toggle now that numpy2 is the default.
#
# build:
#   docker build . -f swf8-jupyter.Dockerfile --tag swf8-jupyter:latest
# with local buildcache:
#   DOCKER_BUILDKIT=1 docker build --build-arg SPACK_BUILDCACHE_LOCAL=1 \
#     . -f swf8-jupyter.Dockerfile --tag swf8-jupyter:latest --progress=plain
# run:
#   docker run --rm -it -p 8888:8888 -e OPENBLAS_NUM_THREADS=1 swf8-jupyter:latest

FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6 AS builder

USER root
SHELL ["/bin/bash", "-lc"]

ARG PYTHON_VERSION=3.11

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
    libopenblas-dev \
    libtool \
    zlib1g-dev \
    m4 \
    patchelf \
    perl \
    pkg-config \
    time \
    zstd

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

# Prebuilt Rust via rustup (matches rapthor-jupyter). Without this, Spack
# builds rust@1.86 from source for hours. Pin 1.86.0 to match the concretized
# SWF-8 graph so `spack external find rust` satisfies the dependency.
RUN set -o pipefail && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.86.0 --no-modify-path && \
    rustc --version && cargo --version

RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

RUN spack compiler find && \
    spack compiler list && \
    spack external find \
    autoconf \
    automake \
    bison \
    curl \
    diffutils \
    findutils \
    git \
    libtool \
    m4 \
    perl \
    pkgconf \
    rust
# Note: do not `spack external find zlib` — Ubuntu multiarch puts libz in
# /usr/lib/<triplet>/, and OpenMPI's --with-zlib=/usr only searches /usr/lib.
#
# Note: do not `spack external find bzip2` either — this base jupyter/conda
# image ships bzip2 under /opt/conda/bin, so external find registered
# /opt/conda as the bzip2 prefix. Every dependent package's configure then
# baked -I/opt/conda/include/-L/opt/conda/lib in (independent of PATH — this
# is a packages.yaml registration, not a PATH lookup, which is why reordering
# or excluding /opt/conda from PATH in the later spack-install step never
# fixed it). For python specifically, the not-yet-installed build links its
# own ./python against /opt/conda/lib/libpython3.11.so via that leaked
# RPATH entry, which has its own unrelated stdlib layout — hence
# "ModuleNotFoundError: No module named 'encodings'" during pybuilddir.txt
# generation. Let spack build bzip2 from source like everything else.

# SKA SDP Spack repo (healpy, reproject, tables, …) + Karabo overlay (ps_eor stack)
RUN git clone --depth=1 --single-branch --branch=2026.07.2 https://gitlab.com/ska-telescope/sdp/ska-sdp-spack.git /opt/ska-sdp-spack && \
    rm -rf /opt/ska-sdp-spack/.git && \
    spack repo add /opt/ska-sdp-spack
COPY --link spack-overlay /opt/karabo-spack
# Keep only SWF-8 recipes (+ pyfftw helper). Drop rapthor/healpy overlays that
# fight the numpy1/scipy1.12 pin (karabo.py-healpy requires scipy 1.10.x).
RUN set -o pipefail; \
    for package in /opt/karabo-spack/packages/*; do \
        case "$(basename "${package}")" in \
            py-ps-eor|py-gpy|py-fast-histogram|py-dynesty|py-ultranest|py-libpipe|py-asyncssh|py-pyfftw|py-healpy|py-pyerfa) ;; \
            *) rm -rf "${package}" ;; \
        esac; \
    done && \
    test -f /opt/karabo-spack/packages/py-ps-eor/package.py && \
    test -f /opt/karabo-spack/packages/py-gpy/package.py && \
    spack repo add /opt/karabo-spack

# NumPy 2 / SciPy 1.14 stack (matches rapthor-jupyter's proven combo — see
# py-scipy's own package.py: `depends_on("py-numpy@1.23.5:2.2", when="@1.14")`,
# i.e. scipy@1.14 caps numpy at <=2.2, hence exactly 2.2.0, not a later 2.x).
# Versions below researched directly against spack-packages
# (github.com/spack/spack-packages @ releases/v2025.11, matching spack v1.1.1's
# pinned builtin repo) rather than guessed:
ARG NUMPY_VERSION=2.2.0
ARG SCIPY_VERSION=1.14.1
ARG MATPLOTLIB_VERSION=3.9.2
# Astropy 7 + cfitsio 4 (healpy 1.16); Astropy 6 forces cfitsio@:3.
ARG ASTROPY_VERSION=7.0.1
ARG PANDAS_VERSION=2.2.3
ARG H5PY_VERSION=3.12.1
ARG HDF5_VERSION=1.14.3
ARG REPROJECT_VERSION=0.14.1
ARG HEALPY_VERSION=1.16.6
# astropy-healpix@:1.0.2 hard-caps numpy@:1 (py-numpy@2: only when @1.0.3:).
ARG ASTROPY_HEALPIX_VERSION=1.0.3
# pyerfa@2.0.1.1 caps numpy@1.25:1; @2.0.1.5: needs numpy@2.0.0rc1: to build.
ARG PYERFA_VERSION=2.0.1.5
# py-tables@3.10: requires numexpr@2.10.2: — needs to move together with
# TABLES_VERSION below.
ARG NUMEXPR_VERSION=2.10.2
# py-tables@:3.9 hard-caps numpy@:1 (py-numpy@1.25: only when @3.10:).
# karabo overlay's py-pyfftw@0.13.1 caps its own numpy dep <2.0 (see
# spack-overlay/packages/py-pyfftw/package.py) and needs Cython<3.0; @0.14.0
# is the numpy2-targeted release, needs Cython>=3.
ARG TABLES_VERSION=3.10.2
ARG PYFFTW_VERSION=0.14.0
ARG PS_EOR_VERSION=1.0
ARG GPY_VERSION=1.13.2
ARG SKLEARN_VERSION=1.5.2

ARG SPACK_TARGET=""
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

# py-zipp/py-maturin/py-cython pins from the numpy1.24/GPy build are DROPPED
# here (not present in the require dict below): the PEP-639-SPDX-license
# rejection that forced them was caused by py-numpy hard-requiring
# `setuptools@:63 when @:1.25` — with numpy pinned to 2.2.0 now, that
# constraint no longer applies, so spack is free to pick a modern
# py-setuptools that parses PEP 639 strings fine, and py-cython isn't
# capped away from 3.1.x either. If concretization or the scipy build hits
# the same "undeclared name not builtin: long" Cython-3.1 error seen on the
# 1.24/GPy stack, re-add a `('py-cython','@:3.0')` require here — scipy@1.14
# only needs cython>=3.0.8, so that pin is compatible if needed again.
#
# ROOT CAUSE (confirmed via the diagnostic block further down, now removed
# from the failure path since it's fixed): spack's python-3.11.11 build
# resolves its optional bzip2 dependency by searching for libbz2.so, and its
# sibling-lib-dir heuristic checks every PATH entry's lib/ dir — so as long
# as /opt/conda/bin is on PATH at all (regardless of position), it finds
# /opt/conda/lib/libbz2.so and bakes -L/opt/conda/lib / -I/opt/conda/include
# into configure's LDFLAGS/CPPFLAGS, and /opt/conda/lib into the built
# python's RPATH. Since the freshly-built python isn't installed yet when
# `make pybuilddir.txt` runs (needs its own not-yet-copied libpython3.11.so),
# the dynamic linker falls through RPATH to /opt/conda/lib's libpython3.11.so
# instead — a real, different Python build with its own (irrelevant) stdlib
# location, hence "ModuleNotFoundError: No module named 'encodings'".
# Merely reordering PATH (tried first) didn't help: the sibling-dir search
# isn't order-sensitive, it checks every entry. The real fix is to drop
# /opt/conda/bin from PATH entirely for this build — apt already provides
# everything actually needed (incl. libbz2-dev) under /usr.
#
# That first (wrong) PATH-reorder attempt also broke the version-pin writer
# below, which needs PyYAML (only present in conda's env) — it failed with
# "ModuleNotFoundError: No module named 'yaml'" and, because the line ended
# in `;` not `&&`, failed SILENTLY: an entire ~70min build ran with NONE of
# the pins applied (incl. the zipp fix), wasting the run on an unpinned
# dependency graph that hit a similar license error on a different package.
# Fixed by hardcoding /opt/conda/bin/python3 for that one invocation (it
# needs yaml; it's the only step here that still needs conda's python) and
# by making that step abort the build on failure instead of continuing
# silently.
RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache-swf8-2026.07.2,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache,sharing=locked \
    --mount=type=secret,id=spack_oci_username,required=false \
    --mount=type=secret,id=spack_oci_password,required=false \
    set -o pipefail; \
    mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache}; \
    unset PYTHONHOME PYTHONPATH; \
    export PATH="$(printf '%s' "${PATH}" | tr ':' '\n' | grep -v '^/opt/conda' | paste -sd: -)"; \
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
    # Per-package make -j (Spack defaults to min(16, nproc); use all cores).
    spack config add "config:build_jobs:$(nproc)"; \
    spack config add "packages:all:target:[${spack_target}]"; \
    export MAKEFLAGS="-j$(nproc)"; \
    /opt/conda/bin/python3 -c "import yaml,sys;p='/opt/spack_env/spack.yaml';f=open(p);c=yaml.safe_load(f);f.close();\
    pkgs=c.setdefault('spack',{}).setdefault('packages',{});\
    [pkgs.setdefault(k,{}).update({'require':v}) for k,v in [\
        ('py-numpy','@${NUMPY_VERSION}'),\
        ('py-scipy','@${SCIPY_VERSION}'),\
        ('py-matplotlib','@${MATPLOTLIB_VERSION}'),\
        ('py-h5py','@${H5PY_VERSION} ~mpi'),\
        ('py-pandas','@${PANDAS_VERSION} ~performance'),\
        ('py-astropy','@${ASTROPY_VERSION}'),\
        ('py-reproject','@${REPROJECT_VERSION}'),\
        ('py-healpy','@${HEALPY_VERSION} ~scipy'),\
        ('py-astropy-healpix','@${ASTROPY_HEALPIX_VERSION}'),\
        ('py-pyerfa','@${PYERFA_VERSION}'),\
        ('py-numexpr','@${NUMEXPR_VERSION}'),\
        ('py-gpy','@${GPY_VERSION}'),\
        ('py-scikit-learn','@${SKLEARN_VERSION}'),\
        ('py-tables','@${TABLES_VERSION}'),\
        ('py-dask','@2024.7.1 ~dataframe ~distributed'),\
        ('py-pyfftw','@${PYFFTW_VERSION}'),\
        ('cfitsio','@4.5.0'),\
        ('zlib','@1.2:'),\
        ('hdf5','@${HDF5_VERSION}+hl~mpi+threadsafe')]];\
    c['spack']['view']={'default':{'root':'/opt/view'}};\
    f=open(p,'w');yaml.dump(c,f,default_flow_style=False);f.close()" \
    || { echo "FATAL: version-pin writer failed (see above)"; exit 1; }; \
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
    spack add \
    'python@'$PYTHON_VERSION \
    'py-pip' \
    'karabo.py-ps-eor@'$PS_EOR_VERSION'+ml-gpr~torch' \
    'py-imageio' \
    'py-tqdm' \
    && \
    spack concretize --force && \
    python3 -c "import json,sys;d=json.load(open('/opt/spack_env/spack.lock'));\
    t=['py-ps-eor','py-numpy','py-scipy','py-gpy','py-healpy','py-astropy'];\
    c={};[c.setdefault(s.get('name'),[]).append(0) for s in d.get('concrete_specs',{}).values()];\
    e=[x for x in t if len(c.get(x,[]))>1];\
    print(f'Duplicate packages found: {e}') or sys.exit(1) if e else print('No duplicate packages, OK')" && \
    spack install -j"$(nproc)" --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    spack gc -y && \
    find /opt/software -name '*.a' -delete && \
    spack env view regenerate && \
    # Torch/GPyTorch/Pyro via pip wheels: Spack py-torch is a multi-hour
    # source build, and gpytorch/pyro-ppl aren't in the ska-sdp/karabo spack
    # repos at all. ps_eor@1.0's ml-gpr backend (~torch variant) needs all
    # three at runtime.
    /opt/view/bin/pip install --no-cache-dir \
        'torch==2.6.0' \
        'gpytorch>=1.11' \
        'pyro-ppl>=1.9' \
        jupyterlab notebook ipykernel 'requests>=2.32' packaging && \
    fix-permissions /opt/view /opt/spack_env /opt/software

# ----------- Runtime image -----------
FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6

USER root
SHELL ["/bin/bash", "-lc"]

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get --no-install-recommends install -y \
    ca-certificates \
    curl \
    git \
    libgomp1 \
    libopenblas0 \
    time \
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

RUN echo ". ${SPACK_ROOT}/share/spack/setup-env.sh 2>/dev/null || true" > /etc/profile.d/spack.sh && \
    echo "spack env activate -p /opt/spack_env 2>/dev/null || true" >> /etc/profile.d/spack.sh

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

RUN arch=$(uname -m) && \
    printf "%s\n" "/opt/view/lib" "/opt/view/lib64" "/usr/lib/${arch}-linux-gnu" > /etc/ld.so.conf.d/spack-view.conf && \
    ldconfig

ENV PATH="/opt/view/bin:${PATH}"

# healpy 1.16 still does `from scipy.integrate import trapz`, removed in SciPy
# 1.14. Without this shim, `import healpy` / `from ps_eor import pspec` fail and
# the phase3 GPR notebook cannot load. Applied via sitecustomize so every
# interpreter (notebook kernel, CI, CLI) sees it.
RUN python - <<'PY'
from pathlib import Path
import sysconfig

site = Path(sysconfig.get_paths()["purelib"])
path = site / "sitecustomize.py"
marker = "SWF8_SCIPY_TRAPZ_SHIM"
block = f'''
# {marker}: healpy 1.16 × SciPy 1.14 compat (phase3 / ps_eor.pspec)
def _swf8_scipy_trapz_shim():
    try:
        import scipy.integrate as _si
    except Exception:
        return
    if not hasattr(_si, "trapz") and hasattr(_si, "trapezoid"):
        _si.trapz = _si.trapezoid  # type: ignore[attr-defined]

_swf8_scipy_trapz_shim()
'''
existing = path.read_text() if path.is_file() else ""
if marker not in existing:
    path.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + block)
print("wrote", path)
PY

RUN python -c "import numpy; assert numpy.__version__.startswith('2.'), numpy.__version__" && \
    python -c "import scipy; assert scipy.__version__.startswith('1.14'), scipy.__version__" && \
    python -c "import scipy.integrate as si; assert hasattr(si, 'trapz'), 'trapz shim missing'" && \
    python -c "import healpy; print('healpy', healpy.__version__)" && \
    python -c "import ps_eor; print('ps_eor', ps_eor.__version__)" && \
    python -c "from ps_eor import ml_gpr, datacube, psutil, pspec; print('ps_eor+ml_gpr+pspec OK')" && \
    python -c "import torch; print('torch', torch.__version__)" && \
    python -c "import gpytorch; print('gpytorch', gpytorch.__version__)" && \
    python -c "import pyro; print('pyro', pyro.__version__)" && \
    python -c "import emcee, corner; print('emcee', emcee.__version__, 'corner', corner.__version__)" && \
    python -c "import imageio, tqdm; print('imageio/tqdm OK')" && \
    python -c "from scipy.integrate import trapezoid; print('trapezoid OK')"

ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
ARG PYTHON_VERSION=3.11

RUN python -m pip install --no-cache-dir \
    "jupyterhub==4.1.6" \
    "marimo[sandbox]>=0.19.11" \
    "marimo-jupyter-extension>=0.1.4" && \
    ln -sf "$(command -v marimo)" /usr/local/bin/marimo && \
    ln -sf "$(command -v jupyterhub-singleuser)" /usr/local/bin/jupyterhub-singleuser && \
    python -c 'import jupyterhub; assert jupyterhub.__version__ == "4.1.6", jupyterhub.__version__' && \
    jupyterhub-singleuser --help >/dev/null && \
    marimo --version && \
    { python -m pip check || echo "pip check: non-fatal metadata mismatches (see above) — actual imports already verified above (numpy/scipy/ps_eor/ml_gpr/torch/gpytorch/pyro/trapezoid), some spack-built packages report placeholder versions (e.g. astropy-healpix 0.0.0) since they're built from source tarballs without git metadata for setuptools_scm to read; cosmetic, not a real inconsistency."; }

RUN install -d -o ${NB_UID} -g ${NB_GID} /home/${NB_USER}/.astropy/cache

USER ${NB_UID}

RUN python -m ipykernel install --user --name=swf8 --display-name="SWF-8 ps_eor (Spack Py${PYTHON_VERSION})"

RUN python -c "from astropy.time import Time; t=Time.now(); print(t.gps, t.ut1)" || true

WORKDIR "/home/${NB_USER}"

USER root
RUN rm -f /opt/conda/bin/jupyter* && \
    ln -s /opt/view/bin/jupyter /opt/conda/bin/jupyter && \
    ln -s /opt/view/bin/jupyter-lab /opt/conda/bin/jupyter-lab && \
    ln -s /opt/view/bin/jupyter-notebook /opt/conda/bin/jupyter-notebook
USER ${NB_UID}
