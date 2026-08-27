# Rapthor pipeline runtime — no Jupyter, no conda, no TeX.
#
# This is the size-optimised sibling of rapthor-jupyter.Dockerfile. It exists
# because the SRCNet OKE demo (https://gist.github.com/d3v-null/953efe2cc776d0c65b0c3acbe394862e)
# pulls RAPTHOR_IMAGE once per CWL step onto every pilot, so image size is
# directly on the demo's critical path.
#
# ┌ Layer analysis of ghcr.io/d3v-null/rapthor-jupyter:sha-bcdf6ea-pass ──────┐
# │ 5679 MB on disk / 1.52 GB compressed. Where it went:                     │
# │   854 MB  /opt/conda .............. jupyter base image's conda           │
# │   548 MB  /opt/._view ............. the spack view, shipped TWICE (see   │
# │                                     "View duplication" below)            │
# │   461 MB  pip-installed into view . marimo(127) jupyterlab(26) uv(59)    │
# │                                     notebook debugpy babel jupyterhub    │
# │   453 MB  TeX Live + pandoc ....... /usr/share/texlive, /usr/bin/pandoc, │
# │                                     luatex — nbconvert PDF export        │
# │   280 MB  include/ ................ headers, build-time only            │
# │   179 MB  /home/jovyan/.spack ..... spack bootstrap cache                │
# │   133 MB  python stdlib test/ ..... CPython's own test suite            │
# │   130 MB  /usr/lib/gcc ............ compilers, build-time only          │
# │    96 MB  spack cmake ............. build-time only                      │
# │    77 MB  hdf5/bin ................ h5dump/h5repack/... never invoked    │
# │    79 MB  spack openmpi ........... nothing here links libmpi           │
# │    53 MB  spack font-util ......... X11 bitmap fonts                     │
# │    41 MB  spack py-cython ......... build-time only                      │
# └──────────────────────────────────────────────────────────────────────────┘
# Result: 1721 MB on disk / 521 MB compressed — 3.3x / 2.9x smaller.
#
# View duplication. In the builder /opt/view is a *symlink* into /opt/._view/<hash>.
# rapthor-jupyter.Dockerfile does `COPY --from=builder /opt/view /opt/view` AND
# `COPY --from=builder /opt/._view /opt/._view`; the first dereferences the
# symlink, so the whole view is materialised twice. Console-script shebangs
# point at /opt/._view/<hash>/bin/python3, so /opt/._view is the copy that must
# survive — here we copy only that and recreate /opt/view as a symlink.
#
# The Spack environment spec is deliberately IDENTICAL to the CPU-only
# rapthor-jupyter build, so every package is a binary hit against the shared
# buildcache at oci://ghcr.io/<owner>/rapthor-jupyter-spack-buildcache. Change
# a version pin here and you buy yourself a multi-hour from-source rebuild.
# Everything this image drops is dropped *after* `spack install`, by deleting
# files — never by changing what Spack builds.
#
# build: docker build . -f rapthor-lean.Dockerfile --tag rapthor-lean:latest
# run:   docker run --rm -it -v $PWD:$PWD -w $PWD -e OPENBLAS_NUM_THREADS=1 rapthor-lean:latest
#
# NOTE: as with rapthor-jupyter, DP3 and WSClean refuse to start unless
# OPENBLAS_NUM_THREADS=1 is set by the caller. That is unchanged here on
# purpose, so the demo's existing environment keeps its exact meaning.
#
# NOTE: the runtime image is built to run with no internet egress. Astropy's
# IERS Earth-orientation table is baked into its download cache at build time
# and pinned there; see "Offline Earth-orientation data" below. Only the build
# needs network.

FROM quay.io/jupyter/minimal-notebook:notebook-7.0.6 AS builder

USER root
SHELL ["/bin/bash", "-lc"]

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

# Version pins for numpy 2 compatibility.
# These MUST stay in lockstep with rapthor-jupyter.Dockerfile — see the header.
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
# 6.6.20260819 = DP3 f4403bae (v6.6-130); +fastpredict on x86, ~fastpredict on ARM.
ARG DP3_VERSION=6.6.20260819
ARG RAPTHOR_VERSION=2.1.20260630

ARG SPACK_TARGET=""
ARG SPACK_BUILDCACHE_LOCAL=""
ARG SPACK_MIRROR_OCI=""

# CPU-only: no CUDA branches at all. With CUDA_ARCH empty the rapthor-jupyter
# build concretises to exactly this spec, which is what keeps the shared
# buildcache warm for both images.
RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache-2026.07.2,sharing=locked \
    --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked \
    --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache-dp3-f4403bae,sharing=locked \
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
    # py-pandas +performance pulls py-numba → py-llvmlite → llvm (~12GB).
    # Numba is optional for pandas; ~performance matches swf8-jupyter and
    # keeps LLVM out of the install tree / runtime image.
    # FastPredict is x86-oriented (immintrin.h / xsimd neon). Keep it off on ARM.
    if [ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ]; then \
        FP_VARIANT="~fastpredict"; \
    else \
        FP_VARIANT="+fastpredict"; \
    fi; \
    DP3_REQUIRE="@${DP3_VERSION}+idg~cuda${FP_VARIANT}"; \
    IDG_REQUIRE="~cuda"; \
    WSCLEAN_REQUIRE="~mpi~cuda"; \
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
    ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --show-log-on-error && \
    spack gc -y && \
    # Static archives are only needed at link time; the shared libs
    # copied into the runtime image already satisfy everything at
    # runtime. Removing them trims several GB with no functional risk.
    find /opt/software -name '*.a' -delete && \
    # Belt-and-suspenders: llvm is build/link-only for llvmlite (statically
    # linked). Never ship the ~12GB prefix even if concretize misses it.
    rm -rf /opt/software/*/llvm-* && \
    spack env view regenerate && \
    fix-permissions /opt/view /opt/spack_env /opt/software

# ----------- Prune: strip everything the pipeline never opens at runtime -----
# Kept as its own layer so iterating on the prune never re-runs `spack install`.
# Builder layers are not shipped — only the final filesystem state is COPYed —
# so deleting here genuinely removes bytes from the runtime image.
#
# Every entry below was verified against the real image: imports, `rapthor
# --version`, `DP3 --version`, `wsclean --version`, `aoflagger --version`,
# benchmon CLIs, and the DP3 FastPredict smoke test all still pass.
RUN set -euo pipefail; \
    S=/opt/software/linux-*; \
    # --- prefixes that are build-time-only in practice ---------------------- \
    # cmake(96M) is only a build/link dep of everybeam plus a declared "run"
    # dep of py-scikit-build{,-core}, which are themselves build helpers.
    # py-cython(41M) is a declared run dep of py-tables that py-tables never
    # imports. font-util(53M) is X11 bitmap fonts behind fontconfig; matplotlib
    # ships its own DejaVu via freetype. graphviz(21M) is reachable only from
    # py-pydot and is already non-functional in rapthor-jupyter (its `dot` is
    # missing libltdl.so.7), so nothing can be relying on it.
    rm -rf $S/cmake-* $S/py-cython-* $S/font-util-* $S/graphviz-*; \
    # openmpi/pmix/prrte/openssh: nothing in the view links libmpi except
    # openmpi's own Fortran bindings and fftw's unused *_mpi variants. DP3,
    # WSClean and casacore are all built ~mpi.
    rm -rf $S/openmpi-* $S/pmix-* $S/prrte-* $S/openssh-*; \
    rm -f $S/fftw-*/lib/libfftw3*_mpi*; \
    # --- build metadata carried inside every prefix ------------------------- \
    find /opt/software -mindepth 2 -maxdepth 3 -type d \
        \( -name include -o -name aclocal -o -name man -o -name doc -o -name info \) \
        -prune -exec rm -rf {} +; \
    find /opt/software -mindepth 2 -type d \
        \( -name pkgconfig -o -name cmake \) -prune -exec rm -rf {} +; \
    # Spack's per-prefix build logs. spec.json stays — the DP3 fastpredict
    # assertion in CI reads it.
    find /opt/software -maxdepth 2 -name .spack -type d \
        -exec sh -c 'rm -rf "$1"/archived-files "$1"/spack-build-*' _ {} \; ; \
    # --- CPython's own baggage ---------------------------------------------- \
    rm -rf $S/python-3.12.*/lib/python3.12/{test,idlelib,tkinter,lib2to3,ensurepip}; \
    find $S/python-3.12.*/lib/python3.12 -maxdepth 1 -name 'config-3.12*' -exec rm -rf {} + || true; \
    # --- oversized bin/ and share/ that nothing invokes ---------------------- \
    # hdf5/bin is 77MB of h5dump/h5repack/h5diff; h5py and casacore use libhdf5
    # directly and never shell out. casacore/share is the measures tables and
    # MUST stay; everything listed here is locale data, docs or terminfo that
    # the Ubuntu base already provides.
    rm -rf $S/hdf5-*/bin; \
    for p in glib gettext util-linux-uuid wcslib ncurses elfutils sqlite readline gdbm libedit; do \
        rm -rf $S/$p-*/share; \
    done; \
    # Drop view symlinks left dangling by the deletions above.
    find /opt/._view -xtype l -delete; \
    find /opt/._view -type d -empty -delete || true; \
    chmod -R a+rX /opt/software /opt/._view; \
    du -sh /opt/software /opt/._view

# ----------- Runtime image -----------
# Plain Ubuntu 22.04: same glibc 2.35 as the builder base, minus conda,
# minus TeX Live, minus the notebook stack.
FROM ubuntu:22.04

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# The only system libraries the Spack binaries resolve outside /opt:
# libcurl4 (+ its gnutls/ldap/sasl/ssh/nghttp2/psl/brotli/idn2 chain) and
# libltdl7. pciutils + linux-tools are for benchmon's profiling collectors,
# which the demo's benchmon-collectors.yaml runs from this image.
#
# nodejs is NOT optional: cwltool evaluates CWL JavaScript expressions through
# a Node engine, and without one every rapthor operation dies with
# cwl_utils.errors.JavascriptException. Spack lists node-js as a run dep of
# py-cwltool but satisfies it as an *external* from the builder base's apt, so
# it never lands in /opt/software and must be provided here. The jupyter base
# this image replaced happened to supply it via /opt/conda/bin/node.
RUN apt-get update && apt-get --no-install-recommends install -y \
      ca-certificates \
      libcap2-bin \
      libcurl4 \
      libltdl7 \
      linux-tools-generic \
      nodejs \
      pciutils \
 && rm -rf /var/lib/apt/lists/*

RUN perf_bin="" && \
    for candidate in /usr/lib/linux-tools/*/perf; do perf_bin="${candidate}"; done && \
    test -x "${perf_bin}" && \
    perf_bin="$(readlink -f "${perf_bin}")" && \
    setcap cap_perfmon,cap_ipc_lock=ep "${perf_bin}" && \
    ln -sf "${perf_bin}" /usr/local/bin/perf && \
    getcap "${perf_bin}"

COPY --from=builder /opt/software /opt/software
# Only the real view store. /opt/view is recreated as a symlink below rather
# than COPYed, which would dereference it and duplicate ~500MB.
COPY --from=builder /opt/._view /opt/._view

RUN view_store="$(echo /opt/._view/*)" && \
    test -d "${view_store}/bin" && \
    ln -s "${view_store}" /opt/view && \
    printf '%s\n' /opt/view/lib /opt/view/lib64 > /etc/ld.so.conf.d/spack-view.conf && \
    ldconfig

# /opt/view is a venv (spack's python-venv), so PATH alone is enough — no
# PYTHONPATH, no LD_LIBRARY_PATH, no `spack env activate`, no /opt/spack.
# This matters: the demo's run-ical.sh calls `PYTHONPATH= python3 -c 'import
# rapthor'` with PYTHONPATH deliberately cleared.
ENV PATH="/opt/view/bin:${PATH}"

# HTCondor pilots run the image under apptainer as `nobody`, and Toil runs
# worker containers under the host uid; keep jovyan/1000 for drop-in parity
# with rapthor-jupyter and make sure arbitrary uids can read /opt.
ARG NB_USER=jovyan
ARG NB_UID=1000
ARG NB_GID=100
RUN groupadd -g ${NB_GID} -o users 2>/dev/null || true; \
    useradd -m -s /bin/bash -u ${NB_UID} -g ${NB_GID} ${NB_USER}

# ----------- Offline Earth-orientation data (astropy IERS) ------------------
# The demo cluster resolves DNS but has no HTTPS egress, so astropy's IERS
# auto-download does not fail fast: every process that touches a UTC->UT1
# conversion stalls for `remote_timeout` on datacenter.iers.org, again on the
# maia.usno.navy.mil mirror, and *still* ends up on the IERS-B table bundled
# with astropy, which stops about a year short of the wall clock:
#
#   IERSRangeError: (some) times are outside of range covered by IERS table.
#
# So the download is not merely slow, it is fatal. Fix: bake a real IERS-A
# table (finals2000A.all — measured EOPs plus ~1 year of predictions) into
# astropy's own download cache at build time and pin it with a config file, so
# `IERS_Auto.open()` is a cache hit that never opens a socket.
#
#   * XDG_CONFIG_HOME/XDG_CACHE_HOME rather than ~/.astropy, because $HOME is
#     not dependable here: HTCondor pilots run this image under apptainer as
#     `nobody` and Toil runs worker containers under the host uid. /opt is
#     readable by every uid, and the cache dir is 1777 so anything that still
#     wants to write a cache can. ~jovyan/.astropy is symlinked to the same
#     place to cover a pilot environment that clobbers XDG_*.
#   * auto_max_age is astropy's "re-download once the predictions are older
#     than N days" trigger — the one knob that would put the network back on
#     the critical path. 36500 days pins the baked table for the life of the
#     image; rebuild to refresh it (predictions run out ~1 year after build,
#     and the build asserts at least 90 days of headroom).
#   * allow_internet = False turns every *other* astropy download (sites.json,
#     ephemerides) from a 10s stall into an immediate, legible error.
#   * iers_degraded_accuracy = warn is the safety net: should the table ever be
#     missing or outrun, times fall back to IERS-B accuracy with a warning
#     rather than raising, so an aging image degrades instead of dying.
#   * MPLCONFIGDIR, because matplotlib keeps both its config and its font cache
#     under XDG_CONFIG_HOME; without it matplotlib falls back to a fresh temp
#     dir and rebuilds the font cache in every one of the pipeline's CWL steps.
#
# Unset XDG_CONFIG_HOME to get stock (network-using) astropy behaviour back.
#
# NOTE: the residual `IERSStaleWarning: leap-second file is expired` comes from
# the leap-second table compiled into ERFA and is cosmetic — no leap second has
# been introduced since 2017, and with auto_max_age pinned astropy accepts that
# table rather than trying to fetch a newer one. A current IERS Leap_Second.dat
# is baked in beside the EOP table regardless.
ENV XDG_CONFIG_HOME=/opt/xdg/config \
    XDG_CACHE_HOME=/opt/xdg/cache \
    MPLCONFIGDIR=/opt/xdg/cache/matplotlib

RUN install -d -m 0755 /opt/xdg/config/astropy /opt/xdg/cache/astropy/iers && \
    install -d -m 1777 /opt/xdg/cache/matplotlib && \
    printf '%s\n' \
      '# Baked by rapthor-lean.Dockerfile: this image runs without egress.' \
      '[utils.data]' \
      'allow_internet = False' \
      'remote_timeout = 3.0' \
      '' \
      '[utils.iers.iers]' \
      'auto_max_age = 36500.0' \
      'remote_timeout = 3.0' \
      'iers_degraded_accuracy = warn' \
      'system_leap_second_file = /opt/xdg/cache/astropy/iers/Leap_Second.dat' \
      > /opt/xdg/config/astropy/astropy.cfg

# The URLs come from astropy itself, so they stay in lockstep with the astropy
# version this image ships rather than drifting into a 404 on the next bump.
# This is the one step here that needs the *builder* to have network.
RUN python3 - <<'PY'
import shutil
import urllib.request

from astropy.utils.data import import_file_to_cache, is_url_in_cache
from astropy.utils.iers import IERS_A, IERS_A_URL, IERS_LEAP_SECOND_URL, LeapSeconds

IERS_DIR = "/opt/xdg/cache/astropy/iers"
eop, leap = f"{IERS_DIR}/finals2000A.all", f"{IERS_DIR}/Leap_Second.dat"

for url, dest in ((IERS_A_URL, eop), (IERS_LEAP_SECOND_URL, leap)):
    print(f"fetching {url} -> {dest}", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)

# Parse before trusting: a captive portal or an error page would otherwise be
# cached as gospel and only surface mid-pipeline.
table = IERS_A.open(eop)
LeapSeconds.from_iers_leap_seconds(leap)
print(f"IERS-A rows={len(table)} mjd={table['MJD'].min():.0f}..{table['MJD'].max():.0f}")

# Seeding astropy's URL-keyed download cache is what makes IERS_Auto.open() a
# no-network cache hit. Only the primary URL is seeded; the mirror is consulted
# solely when the primary is missing, and a second copy is 3.7MB for nothing.
import_file_to_cache(IERS_A_URL, eop)
assert is_url_in_cache(IERS_A_URL), IERS_A_URL
PY

# Prewarm the font cache, then hand /opt/xdg to every possible uid: read for the
# baked data, write for the caches, and ~jovyan/.astropy pointing at both.
RUN python3 -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.plot([0, 1]); plt.savefig('/dev/null', format='png')" && \
    test -n "$(ls /opt/xdg/cache/matplotlib/fontlist-*.json)" && \
    rm -rf /home/${NB_USER}/.astropy && \
    install -d -o ${NB_UID} -g ${NB_GID} /home/${NB_USER}/.astropy && \
    ln -s /opt/xdg/cache/astropy /home/${NB_USER}/.astropy/cache && \
    ln -s /opt/xdg/config/astropy /home/${NB_USER}/.astropy/config && \
    chmod -R a+rX /opt/xdg && \
    chmod 1777 /opt/xdg/cache /opt/xdg/cache/matplotlib && \
    du -sh /opt/xdg

# Offline proof, at build time: allow_internet=False from the config above means
# a cache miss cannot be papered over by the builder's own network. Runs as an
# unprivileged uid that owns nothing, which is how the pilots run it.
USER 61234
RUN HOME=/nonexistent python3 - <<'PY'
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import astropy.units as u
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord
    from astropy.time import Time, TimeDelta
    from astropy.utils import iers

    now = Time.now()
    print("ut1", now.ut1.iso)
    site = EarthLocation(lat=-26.825 * u.deg, lon=116.764 * u.deg, height=377 * u.m)
    altaz = SkyCoord(ra=180 * u.deg, dec=-30 * u.deg).transform_to(
        AltAz(obstime=now, location=site)
    )
    print("altaz", altaz.alt)
    table = iers.earth_orientation_table.get()
    messages = [f"{c.category.__name__}: {c.message}" for c in caught]

print("table", type(table).__name__, table.meta.get("data_url"))
for message in messages:
    print("warning:", message)

assert type(table).__name__ == "IERS_Auto", type(table)
offenders = [
    m for m in messages
    if "failed to download" in m or "using local IERS-B" in m or "degraded" in m
]
assert not offenders, offenders

# The predictions must still cover a demo window, or this image is born stale.
horizon = (now + TimeDelta(90, format="jd")).mjd
assert table["MJD"].max().value >= horizon, (table["MJD"].max(), horizon)
print("IERS-A covers now+90d, no downloads attempted")
PY
USER root

# Fail the build here rather than three hours into a demo.
RUN for m in numpy scipy pandas casacore.tables kubernetes toil cwltool \
             rapthor lsmtool losoto bdsf benchmon everybeam astropy \
             reproject tables numexpr h5py matplotlib; do \
        python3 -c "import ${m}" || exit 1; \
    done && \
    shopt -s nullglob && llvm_prefs=(/opt/software/*/llvm-*) && \
    test ${#llvm_prefs[@]} -eq 0 && \
    rapthor --version && \
    OPENBLAS_NUM_THREADS=1 DP3 --version && \
    OPENBLAS_NUM_THREADS=1 wsclean --version >/dev/null && \
    aoflagger --version && \
    toil-cwl-runner --version && \
    benchmon-run --help >/dev/null && \
    benchmon-visu --help >/dev/null && \
    command -v benchmon-start benchmon-stop dool perf lspci && \
    python3 -c "import inspect, lsmtool.facet, toil; from toil.batchSystems import kubernetes as k8s; from rapthor.lib import cwlrunner, operation, parset; checks={'extra-hostpath': 'TOIL_KUBERNETES_EXTRA_HOSTPATH' in inspect.getsource(k8s), 'security-context-loader': 'open(file).read()' in inspect.getsource(k8s), 'skip-image-check': 'TOIL_SKIP_IMAGE_CHECK' in inspect.getsource(toil), 'batch-system-validator': 'kubernetes' in inspect.getsource(parset), 'kubernetes-options': '_add_kubernetes_options' in inspect.getsource(cwlrunner), 'max-cores': 'TOIL_MAX_CORES' in inspect.getsource(cwlrunner), 'workdir': 'TOIL_WORKDIR' in inspect.getsource(cwlrunner), 'single-machine-parallelism': '\"single_machine\", \"kubernetes\"' in inspect.getsource(operation), 'voronoi-fallback': 'voronoi fallback facet centers at bbox middle' in inspect.getsource(lsmtool.facet.voronoi), 'facet-reference-point': 'representative_point' in inspect.getsource(lsmtool.facet.Facet)}; print('Patch checks:', checks); assert all(checks.values()), [name for name, applied in checks.items() if not applied]" && \
    python3 -c "import json,platform; from pathlib import Path; p=Path('/opt/view/bin/DP3').resolve().parents[1]/'.spack'/'spec.json'; nodes=json.loads(p.read_text()).get('spec',{}).get('nodes',[]); dp3=next(n for n in nodes if n.get('name')=='dp3'); fp=dp3.get('parameters',{}).get('fastpredict'); arm=platform.machine() in ('aarch64','arm64'); assert fp is (not arm), (fp, platform.machine()); print('DP3 FastPredict', 'disabled on ARM' if arm else 'enabled')"

# Tiny 3-antenna MS + 1 Jy point source; FastPredict must run and write vis.
# Skipped on ARM: FastPredict is not compiled there.
# Deliberately NOT /tmp: COPYing into /tmp rewrites the directory's mode and
# drops its sticky bit, leaving it root-only 755 instead of 1777. That breaks
# apt inside any downstream build ("Couldn't create temporary file
# /tmp/apt.conf.*") and every non-root process needing scratch -- which is each
# Toil/apptainer step running under an arbitrary host uid.
COPY --link docker/rapthor-lean/fastpredict_smoke.py /opt/smoke/fastpredict_smoke.py
RUN OPENBLAS_NUM_THREADS=1 python3 /opt/smoke/fastpredict_smoke.py && rm -rf /opt/smoke
# Belt and braces: assert the invariant rather than trusting it.
RUN test "$(stat -c '%a' /tmp)" = "1777" || { echo "/tmp is $(stat -c '%a' /tmp), expected 1777" >&2; exit 1; }

USER ${NB_UID}
WORKDIR "/home/${NB_USER}"
CMD ["/bin/bash"]
