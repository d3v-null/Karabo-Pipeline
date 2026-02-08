#!/usr/bin/env bash
set -euo pipefail

# Build OSKAR image and always log output to a file you can tail.
# Usage:
#   ./scripts/docker-build-oskar.sh [tag]
# Example:
#   ./scripts/docker-build-oskar.sh 2.12.0

TAG="${1:-2.12.0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/build-logs"
mkdir -p "${LOG_DIR}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${LOG_DIR}/oskar-build-${TAG}-${TS}.log"

echo "[docker-build-oskar] Starting build at ${TS} UTC"
echo "[docker-build-oskar] Log: ${LOG_FILE}"
echo "[docker-build-oskar] Tail with: tail -f ${LOG_FILE}"

# --progress=plain ensures we actually get useful output in the log
set -o pipefail
(
  cd "${ROOT_DIR}"
  docker build --progress=plain -t "d3vnull0/oskar:${TAG}" -f oskar.Dockerfile .
) 2>&1 | tee "${LOG_FILE}"
