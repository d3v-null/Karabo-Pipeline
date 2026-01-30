#!/bin/bash
set -euo pipefail

# Single canonical build script for the Karabo sp5505 image.
# Uses sp5505.Dockerfile (no "optimized" variants).

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






