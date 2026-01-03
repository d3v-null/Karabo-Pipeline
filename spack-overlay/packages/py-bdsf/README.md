pybdsf package is required otherwise you get `metadata-generation-failed`

```txt
#16 2183.6 ==> Installing py-astropy-healpix-1.1.2-bshamsbsl3oqipsjzu73o6a3bt2zaqhf [270/291]
#16 2183.6 ==> No binary for py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh found: installing from source
#16 2184.3 ==> Fetching https://files.pythonhosted.org/packages/source/b/bdsf/bdsf-1.12.0.tar.gz
#16 2184.3 ==> Ran patch() for py-bdsf
#16 2185.0 ==> py-bdsf: Executing phase: 'install'
#16 2185.1 ==> Error: ProcessError: Command exited with status 1:
#16 2185.1     '/opt/software/linux-x86_64_v2/python-venv-1.0-jjycfb3xhwpvoikf57q3whenhpwgkx3k/bin/python3' '-m' 'pip' '-vvv' '--no-input' '--no-cache-dir' '--disable-pip-version-check' 'install' '--no-deps' '--ignore-installed' '--no-build-isolation' '--no-warn-script-location' '--no-index' '--prefix=/opt/software/linux-x86_64_v2/py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh' '.'
#16 2185.1 ==> Installing py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh [271/291]
#16 2185.2
#16 2185.2 1 error found in build log:
#16 2185.2      50      ╰─> See above for output.
#16 2185.2      51
#16 2185.2      52      note: This error originates from a subprocess, and is likely not a
#16 2185.2             problem with pip.
#16 2185.2      53      full command: /opt/software/linux-x86_64_v2/python-venv-1.0-jjycfb
#16 2185.2            3xhwpvoikf57q3whenhpwgkx3k/bin/python3 /opt/software/linux-x86_64_v2
#16 2185.2            /py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-
#16 2185.2            packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py prep
#16 2185.2            are_metadata_for_build_wheel /tmp/tmpcld22i4s
#16 2185.2      54      cwd: /tmp/root/spack-stage/spack-stage-py-bdsf-1.12.0-2pyuhqtyzl2d
#16 2185.2            t7dzi7ye5dwx3eynxvkh/spack-src
#16 2185.2      55      Preparing metadata (pyproject.toml): finished with status 'error'
#16 2185.2   >> 56    error: metadata-generation-failed
#16 2185.2      57
#16 2185.2      58    × Encountered error while generating package metadata.
#16 2185.2      59    ╰─> See above for output.
#16 2185.2      60
#16 2185.2      61    note: This is an issue with the package mentioned above, not pip.
#16 2185.2      62    hint: See above for details.
#16 2185.2
#16 2185.2 See build log for details:
#16 2185.2   /tmp/root/spack-stage/spack-stage-py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh/spack-build-out.txt
#16 2185.2
#16 2191.8 ==> Error: Terminating after first install failure: ProcessError: Command exited with status 1:
#16 2191.8     '/opt/software/linux-x86_64_v2/python-venv-1.0-jjycfb3xhwpvoikf57q3whenhpwgkx3k/bin/python3' '-m' 'pip' '-vvv' '--no-input' '--no-cache-dir' '--disable-pip-version-check' 'install' '--no-deps' '--ignore-installed' '--no-build-isolation' '--no-warn-script-location' '--no-index' '--prefix=/opt/software/linux-x86_64_v2/py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh' '.'
#16 2191.8 Full build log:
#16 2191.8 ==> py-bdsf: Executing phase: 'install'
#16 2191.8 ==> [2026-01-03-08:15:22.138105] '/opt/software/linux-x86_64_v2/python-venv-1.0-jjycfb3xhwpvoikf57q3whenhpwgkx3k/bin/python3' '-m' 'pip' '-vvv' '--no-input' '--no-cache-dir' '--disable-pip-version-check' 'install' '--no-deps' '--ignore-installed' '--no-build-isolation' '--no-warn-script-location' '--no-index' '--prefix=/opt/software/linux-x86_64_v2/py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh' '.'
#16 2191.8 Using pip 25.1.1 from /opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip (python 3.10)
#16 2191.8 Non-user install due to --prefix or --target option
#16 2191.8 Ignoring indexes: https://pypi.org/simple
#16 2191.8 Created temporary directory: /tmp/pip-build-tracker-3_wnodni
#16 2191.8 Initialized build tracking at /tmp/pip-build-tracker-3_wnodni
#16 2191.8 Created build tracker: /tmp/pip-build-tracker-3_wnodni
#16 2191.8 Entered build tracker: /tmp/pip-build-tracker-3_wnodni
#16 2191.8 Created temporary directory: /tmp/pip-install-kl_jj4_e
#16 2191.8 Created temporary directory: /tmp/pip-ephem-wheel-cache-1a__g35n
#16 2191.8 Processing /tmp/root/spack-stage/spack-stage-py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh/spack-src
#16 2191.8   Added file:///tmp/root/spack-stage/spack-stage-py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh/spack-src to build tracker '/tmp/pip-build-tracker-3_wnodni'
#16 2191.8   Created temporary directory: /tmp/pip-modern-metadata-976fvf9e
#16 2191.8   Preparing metadata (pyproject.toml): started
#16 2191.8   Running command Preparing metadata (pyproject.toml)
#16 2191.8   Traceback (most recent call last):
#16 2191.8     File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 389, in <module>
#16 2191.8       main()
#16 2191.8     File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 373, in main
#16 2191.8       json_out["return_val"] = hook(**hook_input["kwargs"])
#16 2191.8     File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 175, in prepare_metadata_for_build_wheel
#16 2191.8       return hook(metadata_directory, config_settings)
 > [stage-0 10/26] RUN --mount=type=cache,target=/opt/buildcache,id=spack-binary-cache,sharing=locked     --mount=type=cache,target=/opt/spack-source-cache,id=spack-source-cache,sharing=locked     --mount=type=cache,target=/opt/spack-misc-cache,id=spack-misc-cache,sharing=locked     --mount=type=secret,id=spack_oci_username,required=false     --mount=type=secret,id=spack_oci_password,required=false     mkdir -p /opt/{software,view,buildcache,spack-source-cache,spack-misc-cache};     arch=$(uname -m);     spack_target="x86_64_v2";     if [ -z "${spack_target}" ]; then       case "$arch" in         x86_64) spack_target=x86_64_v2 ;;         aarch64) spack_target=aarch64 ;;         *) spack_target="$arch" ;;       esac;     fi;     echo "SPACK_TARGET=${spack_target} <- (uname -m)=$arch";     spack config add "config:install_tree:root:/opt/software";     spack config add "concretizer:unify:when_possible";     spack config add "concretizer:reuse:false";     spack config add "view:/opt/view";     spack config add "config:source_cache:/opt/spack-source-cache";     spack config add "config:misc_cache:/opt/spack-misc-cache";     spack config add "packages:all:target:[${spack_target}]";     spack config add "packages:cuda:version:[12.2.2]";     spack config add "config:build_jobs:4";     if [ "0" != "0" ] && [ -n "" ]; then         spack mirror add --autopush --unsigned mycache file:///opt/buildcache;         spack buildcache update-index /opt/buildcache || true;     fi;     if [ -n "oci://ghcr.io/***/sp5505-spack-buildcache" ]; then         if [ -f /run/secrets/spack_oci_username ] && [ -f /run/secrets/spack_oci_password ]; then             SPACK_OCI_USERNAME="$(cat /run/secrets/spack_oci_username)";             export SPACK_OCI_PASSWORD="$(cat /run/secrets/spack_oci_password)";             spack mirror add --autopush --unsigned                 --oci-username "${SPACK_OCI_USERNAME}"                 --oci-password-variable SPACK_OCI_PASSWORD                 oci-push "oci://ghcr.io/***/sp5505-spack-buildcache";         else             spack mirror add --unsigned oci-cache "oci://ghcr.io/***/sp5505-spack-buildcache";         fi;     fi;     spack mirror add v1.1.0 https://binaries.spack.io/v1.1.0;     spack buildcache keys --install --trust || true;     spack add     'cfitsio@'4.3.1     'boost@'1.82.0'+python+numpy'     'py-astropy@'5.1.1     'py-bdsf@'1.12.0     'py-matplotlib@'3.6.3     'py-numpy@'1.23.5     'py-scipy@'1.9.3     'python@'3.10     'casacore@'3.5.0'+python'     'hdf5@'1.12.3'+hl~mpi'     'py-maturin@1.6.0'     'py-pip'     'py-joblib'     'py-lazy-loader'     'py-dask@'2022.12.1     'py-distributed@'2022.12.1     'py-ducc@'0.27     'py-h5py@'3.7     'py-healpy@'1.16.6'+internal-healpix'     'py-pandas@'1.5.3     'py-photutils@'1.11.0     'py-rascil@'1.0.0     'py-scikit-image@'0.24.0     'py-scikit-learn@'1.3.2     'py-tqdm@'4.66.3     'py-reproject@:0.13'     'py-ska-sdp-datamodels@'0.1.3     'py-ska-sdp-func-python@'0.1.4     'py-tabulate@'0.9.0     'py-xarray@'2023.2.0     'oskar@'2.8.3'+cuda+python~openmp cuda_arch=75,80,86'     'py-pyuvdata@'2.4.2'+casa'     'py-aratmospy@'1.0.0     'py-eidos@'1.1.0     'py-katbeam@'0.1.0     'wsclean@'3.4'~mpi+cuda~python'     'py-tools21cm@'2.3.8     'py-jupyterlab-server@2.27:'     'py-jupyterlab@4'     'py-notebook@7'     'py-dask-mpi'     'py-mpi4py'     'py-packaging'     'py-requests'     'py-rfc3986'     'py-pytest@8'     'hyperbeam+cuda+python cuda_arch=75,80,86,90'     'hyperdrive+cuda cuda_arch=75,80,86,90'     &&     spack concretize --force &&     spack install --use-cache --no-check-signature --no-checksum --fail-fast --fresh cuda &&     CUDA_ROOT=$(spack location -i cuda) &&     STUBS_DIR="${CUDA_ROOT}/lib64/stubs" &&     [ -d "${STUBS_DIR}" ] || STUBS_DIR="${CUDA_ROOT}/lib/stubs" &&     if [ -d "${STUBS_DIR}" ]; then         echo "Found CUDA stubs at ${STUBS_DIR}";         ln -sf "${STUBS_DIR}/libcuda.so" "${STUBS_DIR}/libcuda.so.1";         ln -sf "${STUBS_DIR}/libcuda.so" "/usr/lib/${arch}-linux-gnu/libcuda.so.1";         spack config add "config:build_environment:prepend_path:LD_LIBRARY_PATH:${STUBS_DIR}";         spack config add "config:build_environment:prepend_path:LIBRARY_PATH:${STUBS_DIR}";         export LD_LIBRARY_PATH="${STUBS_DIR}:${LD_LIBRARY_PATH}";         export LIBRARY_PATH="${STUBS_DIR}:${LIBRARY_PATH}";     else         echo "WARNING: CUDA stubs not found in ${CUDA_ROOT}";         exit 1;     fi &&     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --only dependencies --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error &&     ac_cv_lib_curl_curl_easy_init=no spack install --use-cache --no-check-signature --no-checksum --fail-fast --fresh --show-log-on-error &&     spack gc -y &&     spack env view regenerate &&     if [ -n "oci://ghcr.io/***/sp5505-spack-buildcache" ] && spack mirror list | awk '{print $1}' | grep -qx 'oci-push'; then         spack buildcache update-index -k oci-push || spack buildcache update-index oci-push || true;     fi &&     if [ "0" != "0" ] && [ -n "" ]; then         spack buildcache update-index /opt/buildcache || true;     fi &&     fix-permissions /opt/view /opt/spack_env /opt/software:
2191.8   File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_internal/distributions/sdist.py", line 69, in prepare_distribution_metadata
2191.8     self.req.prepare_metadata()
2191.8   File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_internal/req/req_install.py", line 575, in prepare_metadata
2191.8     self.metadata_directory = generate_metadata(
2191.8   File "/opt/software/linux-x86_64_v2/py-pip-25.1.1-lwxni2qy2xjombousouro6epjqqpdjkq/lib/python3.10/site-packages/pip/_internal/operations/build/metadata.py", line 36, in generate_metadata
2191.8     raise MetadataGenerationFailed(package_details=details) from error
2191.8 pip._internal.exceptions.MetadataGenerationFailed: metadata generation failed
2191.8 Removed file:///tmp/root/spack-stage/spack-stage-py-bdsf-1.12.0-2pyuhqtyzl2dt7dzi7ye5dwx3eynxvkh/spack-src from build tracker '/tmp/pip-build-tracker-3_wnodni'
2191.8 Removed build tracker: '/tmp/pip-build-tracker-3_wnodni'
2191.9 ==> Updating view at /opt/view
```