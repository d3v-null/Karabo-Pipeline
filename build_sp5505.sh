#!/bin/bash
set -euo pipefail

# Single canonical build script for the Karabo sp5505 image.
# Uses sp5505.Dockerfile (no "optimized" variants).
# WARNING: This script already redirects output to build_karabo-pipeline_sp5505.log.
# DO NOT wrap with additional redirection (e.g. > logfile or 2>&1).
# Just run: nohup ./build_sp5505.sh &

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Karabo Pipeline Docker Build (sp5505) ===${NC}"
echo ""

# Build arguments
IMAGE_NAME=${IMAGE_NAME:-"karabo-pipeline:sp5505"}
SKIP_TESTS=${SKIP_TESTS:-0}
SPACK_BUILDCACHE_LOCAL=${SPACK_BUILDCACHE_LOCAL:-1}
CUDA_ARCH=${CUDA_ARCH:-"75,80,86,89,90"}
DOCKERFILE=${DOCKERFILE:-"sp5505.Dockerfile"}

echo "Configuration:"
echo "  Image name: $IMAGE_NAME"
echo "  Dockerfile: $DOCKERFILE"
echo "  Skip tests: $SKIP_TESTS"
echo "  CUDA Arch:  $CUDA_ARCH"
echo "  SPACK Buildcache Local:  $SPACK_BUILDCACHE_LOCAL"
[ -n "${SPACK_TARGET:-}" ] && echo "SPACK_TARGET=\"${SPACK_TARGET}\""
[ -n "${SPACK_MIRROR_OCI:-}" ] && echo "SPACK_MIRROR_OCI=\"${SPACK_MIRROR_OCI}\""
echo ""

echo -e "${GREEN}Starting build...${NC}"
echo ""

# Ensure we capture logs to a file (and still show output).
# Use IMAGE_NAME to derive the log file name so custom builds don't overwrite each other.
LOG_BASENAME=$(echo "${IMAGE_NAME}" | sed -e 's#[/:]#_#g' -e 's#[^A-Za-z0-9_.-]#_#g')
LOG_FILE="build_${LOG_BASENAME}.log"
echo "  Log file: ${LOG_FILE}"
echo ""

docker build \
  --progress=plain \
  --build-arg SKIP_TESTS="${SKIP_TESTS}" \
  --build-arg SPACK_BUILDCACHE_LOCAL="${SPACK_BUILDCACHE_LOCAL}" \
  --build-arg CUDA_ARCH="${CUDA_ARCH}" \
  $([ -n "${SPACK_TARGET:-}" ] && echo "--build-arg SPACK_TARGET=\"${SPACK_TARGET}\"") \
  $([ -n "${SPACK_MIRROR_OCI:-}" ] && echo "--build-arg SPACK_MIRROR_OCI=\"${SPACK_MIRROR_OCI}\"") \
  -t "${IMAGE_NAME}" \
  -f "${DOCKERFILE}" \
  . 2>&1 | tee "${LOG_FILE}"

BUILD_EXIT=${PIPESTATUS[0]}
if [ "${BUILD_EXIT}" -ne 0 ]; then
  echo -e "\a${RED}BUILD FAILED (exit ${BUILD_EXIT})${NC}" >&2
  tmux display-message -d 0 "BUILD FAILED (exit ${BUILD_EXIT}) - check ${LOG_FILE}" 2>/dev/null || true
  exit "${BUILD_EXIT}"
fi
echo -e "\a${GREEN}BUILD SUCCEEDED${NC}"
tmux display-message -d 5000 "BUILD SUCCEEDED - ${IMAGE_NAME}" 2>/dev/null || true






