required for building hyperbeam

```txt
#16 803.0 ==> No binary for hyperbeam-0.10.2-gu4mxo3hnfzmjsntodyf24yz5vogblmp found: installing from source
#16 804.2 ==> Fetching https://github.com/MWATelescope/mwa_hyperbeam/archive/refs/tags/v0.10.2.tar.gz
#16 804.2 ==> No patches needed for hyperbeam
#16 855.1 ==> hyperbeam: Executing phase: 'install'
#16 855.2 ==> Error: ProcessError: Command exited with status 101:
#16 855.2     '/usr/local/bin/cargo' 'build' '--locked' '--release' '--features=cuda'
#16 855.2 ==> Installing hyperbeam-0.10.2-gu4mxo3hnfzmjsntodyf24yz5vogblmp [198/258]
#16 855.2
#16 855.2 5 errors found in build log:
#16 855.2      208       Compiling erfa v0.2.1
#16 855.2      209       Compiling itertools v0.10.5
#16 855.2      210       Compiling git2 v0.18.3
#16 855.2      211       Compiling panic-message v0.3.0
#16 855.2      212       Compiling built v0.7.3
#16 855.2      213       Compiling marlu v0.16.1
#16 855.2   >> 214    error: linking with `cc` failed: exit status: 1
#16 855.2      215      |
#16 855.2      216      = note: LC_ALL="C" PATH="/opt/rustup/toolchains/1.81.0-aarch64-un
#16 855.2             known-linux-gnu/lib/rustlib/aarch64-unknown-linux-gnu/bin:/opt/rust
#16 855.2             up/toolchains/1.81.0-aarch64-unknown-linux-gnu/lib/rustlib/aarch64-
#16 855.2             unknown-linux-gnu/bin:/opt/rustup/toolchains/1.81.0-aarch64-unknown
#16 855.2             -linux-gnu/lib/rustlib/aarch64-unknown-linux-gnu/bin:/tmp/root/spac
#16 855.2             k-stage/spack-stage-hyperbeam-0.10.2-gu4mxo3hnfzmjsntodyf24yz5vogbl
#16 855.2             mp/spack-src/.cargo/bin:/opt/software/linux-aarch64/cmake-3.31.9-4b
#16 855.2             bprxpdlfql3avrtbexhwypcjfifxdm/bin:/opt/software/linux-aarch64/cuda
#16 855.2             -12.2.2-fg2fglutdoavip2p66d3iddqif6hxesi/bin:/opt/software/linux-aa
#16 855.2             rch64/hdf5-1.12.3-nzve7q3le5g3wynboav3qabkzivr5su3/bin:/opt/softwar
#16 855.2             e/linux-aarch64/patchelf-0.17.2-lwgcwxnx2pcpvaj7geld566q6ivnhtb7/bi
#16 855.2             n:/opt/software/linux-aarch64/py-maturin-1.6.0-xfgxu2kj47jwauadfi4a
#16 855.2             vnz2qkllospv/bin:/opt/software/linux-aarch64/py-numpy-1.23.5-u4ngis
#16 855.2             af4s67txtf3gb2c5frzwhzoa7j/bin:/opt/software/linux-aarch64/py-pip-2
#16 855.2             5.1.1-4zb6r5y6toptaorraji6yn2a5acnbmyu/bin:/opt/software/linux-aarc
#16 855.2             h64/gmake-4.4.1-72tbdzhgaki33gex7tdgncoqfihvhibc/bin:/opt/software/
 370 | >>>         spack config add "config:build_environment:prepend_path:LIBRARY_PATH:${STUBS_DIR}"; \
 371 | >>>         export LD_LIBRARY_PATH="${STUBS_DIR}:${LD_LIBRARY_PATH}"; \
 372 | >>>         export LIBRARY_PATH="${STUBS_DIR}:${LIBRARY_PATH}"; \
 373 | >>>     else \
 374 | >>>         echo "WARNING: CUDA stubs not found in ${CUDA_ROOT}"; \
 375 | >>>         exit 1; \
 376 | >>>     fi && \
 377 | >>>     # CUDA HACK: Link against stubs (libcuda.so.1) to allow building wsclean/idg without a GPU driver present in Docker
 378 | >>>     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --only dependencies --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error && \
 379 | >>>     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error && \
 380 | >>>     spack gc -y && \
 381 | >>>     spack env view regenerate && \
 382 | >>>     # If we're using an OCI buildcache, publish the buildcache index so *pulling*
 383 | >>>     # works. Without this, consumers see 404 for `index.spack` and can't discover
 384 | >>>     # binaries even though packages were pushed.
 385 | >>>     if [ -n "${SPACK_MIRROR_OCI}" ] && spack mirror list | awk '{print $1}' | grep -qx 'oci-push'; then \
 386 | >>>         spack buildcache update-index -k oci-push || spack buildcache update-index oci-push || true; \
 387 | >>>     fi && \
 388 | >>>     if [ "${SPACK_BUILDCACHE_LOCAL:-0}" != "0" ] && [ -n "${SPACK_BUILDCACHE_LOCAL:-}" ]; then \
 389 | >>>         spack buildcache update-index /opt/buildcache || true; \
 390 | >>>     fi && \
 391 | >>>     fix-permissions /opt/view /opt/spack_env /opt/software
 392 |
--------------------
ERROR: failed to build: failed to solve: process "/bin/bash -lc mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache};     arch=$(uname -m);     spack_target=\"${SPACK_TARGET}\";     if [ -z \"${spack_target}\" ]; then       case \"$arch\" in         x86_64) spack_target=x86_64_v2 ;;         aarch64) spack_target=aarch64 ;;         *) spack_target=\"$arch\" ;;       esac;     fi;     echo \"SPACK_TARGET=${spack_target} <- (uname -m)=$arch\";     spack config add \"config:install_tree:root:/opt/software\";     spack config add \"concretizer:unify:when_possible\";     spack config add \"concretizer:reuse:false\";     spack config add \"view:/opt/view\";     spack config add \"config:source_cache:/opt/spack-source-cache\";     spack config add \"config:misc_cache:/opt/spack-misc-cache\";     spack config add \"packages:all:target:[${spack_target}]\";     spack config add \"packages:cuda:version:[${CUDA_VERSION}]\";     spack config add \"config:build_jobs:4\";     if [ \"${SPACK_BUILDCACHE_LOCAL:-0}\" != \"0\" ] && [ -n \"${SPACK_BUILDCACHE_LOCAL:-}\" ]; then         spack mirror add --autopush --unsigned mycache file:///opt/buildcache;         spack buildcache update-index /opt/buildcache || true;     fi;     if [ -n \"${SPACK_MIRROR_OCI}\" ]; then         if [ -f /run/secrets/spack_oci_username ] && [ -f /run/secrets/spack_oci_password ]; then             SPACK_OCI_USERNAME=\"$(cat /run/secrets/spack_oci_username)\";             export SPACK_OCI_PASSWORD=\"$(cat /run/secrets/spack_oci_password)\";             spack mirror add --autopush --unsigned                 --oci-username \"${SPACK_OCI_USERNAME}\"                 --oci-password-variable SPACK_OCI_PASSWORD                 oci-push \"${SPACK_MIRROR_OCI}\";         else             spack mirror add --unsigned oci-cache \"${SPACK_MIRROR_OCI}\";         fi;     fi;     spack mirror add v1.1.0 https://binaries.spack.io/v1.1.0;     spack buildcache keys --install --trust || true;     spack add     'cfitsio@'$CFITSIO_VERSION     'boost@'$BOOST_VERSION'+python+numpy'     'py-astropy@'$ASTROPY_VERSION     'py-bdsf@'$BDSF_VERSION     'py-matplotlib@'$MATPLOTLIB_VERSION     'py-numpy@'$NUMPY_VERSION     'py-scipy@'$SCIPY_VERSION     'python@'$PYTHON_VERSION     'casacore@'$CASACORE_VERSION'+python'     'hdf5@'$HDF5_VERSION'+hl~mpi'     'py-maturin@1.6.0'     'py-pip'     'py-joblib'     'py-lazy-loader'     'py-dask@'$DASK_VERSION     'py-distributed@'$DISTRIBUTED_VERSION     'py-ducc@'$DUCC_VERSION     'py-h5py@'$H5PY_VERSION     'py-healpy@'$HEALPY_VERSION'+internal-healpix'     'py-pandas@'$PANDAS_VERSION     'py-photutils@'$PHOTUTILS_VERSION     'py-rascil@'$RASCIL_VERSION     'py-scikit-image@'$SKIMAGE_VERSION     'py-scikit-learn@'$SKLEARN_VERSION     'py-tqdm@'$TQDM_VERSION     'py-reproject@:0.13'     'py-ska-sdp-datamodels@'$SDP_DATAMODELS_VERSION     'py-ska-sdp-func-python@'$SDP_FUNC_PYTHON_VERSION     'py-tabulate@'$TABULATE_VERSION     'py-xarray@'$XARRAY_VERSION     'oskar@'$OSKAR_VERSION'+cuda+python~openmp cuda_arch=75,80,86'     'py-pyuvdata@'$PYUVDATA_VERSION'+casa'     'py-aratmospy@'$ARATMOSPY_VERSION     'py-eidos@'$EIDOS_VERSION     'py-katbeam@'$KATBEAM_VERSION     'wsclean@'$WSCLEAN_VERSION'~mpi+cuda~python'     'py-tools21cm@'$TOOLS21CM_VERSION     'py-jupyterlab-server@2.27:'     'py-jupyterlab@4'     'py-notebook@7'     'py-dask-mpi'     'py-mpi4py'     'py-packaging'     'py-requests'     'py-rfc3986'     'py-pytest@8'     'hyperbeam+cuda+python cuda_arch=75,80,86,90'     'hyperdrive+cuda cuda_arch=75,80,86,90'     &&     spack concretize --force &&     spack install --use-cache --no-check-signature --no-checksum --fail-fast --fresh cuda &&     CUDA_ROOT=$(spack location -i cuda) &&     STUBS_DIR=\"${CUDA_ROOT}/lib64/stubs\" &&     [ -d \"${STUBS_DIR}\" ] || STUBS_DIR=\"${CUDA_ROOT}/lib/stubs\" &&     if [ -d \"${STUBS_DIR}\" ]; then         echo \"Found CUDA stubs at ${STUBS_DIR}\";         ln -sf \"${STUBS_DIR}/libcuda.so\" \"${STUBS_DIR}/libcuda.so.1\";         ln -sf \"${STUBS_DIR}/libcuda.so\" \"/usr/lib/${arch}-linux-gnu/libcuda.so.1\";         spack config add \"config:build_environment:prepend_path:LD_LIBRARY_PATH:${STUBS_DIR}\";         spack config add \"config:build_environment:prepend_path:LIBRARY_PATH:${STUBS_DIR}\";         export LD_LIBRARY_PATH=\"${STUBS_DIR}:${LD_LIBRARY_PATH}\";         export LIBRARY_PATH=\"${STUBS_DIR}:${LIBRARY_PATH}\";     else         echo \"WARNING: CUDA stubs not found in ${CUDA_ROOT}\";         exit 1;     fi &&     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --only dependencies --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error &&     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error &&     spack gc -y &&     spack env view regenerate &&     if [ -n \"${SPACK_MIRROR_OCI}\" ] && spack mirror list | awk '{print $1}' | grep -qx 'oci-push'; then         spack buildcache update-index -k oci-push || spack buildcache update-index oci-push || true;     fi &&     if [ \"${SPACK_BUILDCACHE_LOCAL:-0}\" != \"0\" ] && [ -n \"${SPACK_BUILDCACHE_LOCAL:-}\" ]; then         spack buildcache update-index /opt/buildcache || true;     fi &&     fix-permissions /opt/view /opt/spack_env /opt/software" did not complete successfully: exit code: 1
Reference
```