#!/bin/bash
set -euo pipefail

# Script to clean (delete) the Spack OCI buildcache stored in GHCR.
# Uses 'gh' CLI to delete the package versions.
#
# Usage: ./clean_spack_cache.sh [package_name] [--force]
#
# Defaults to 'sp5505-spack-buildcache' if not provided.
#
# The CI pipeline uses a multi-layer caching strategy including Docker BuildKit,
# pip, system packages, and a remote Spack OCI buildcache stored in GHCR.
# This script specifically addresses the Spack buildcache, which can occasionally
# become "poisoned" with binaries built for incorrect architectures (e.g., AVX-512
# extensions on non-supporting runners), causing SIGILL errors. Deleting this
# cache forces a clean rebuild from source on the next run. See docs/ci-caching-strategy.md
# for full details.

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

FORCE=0
PACKAGE_NAME=""

# Parse arguments
for arg in "$@"; do
    if [ "$arg" == "--force" ]; then
        FORCE=1
    else
        PACKAGE_NAME="$arg"
    fi
done

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: 'gh' CLI is required but not found.${NC}"
    echo "Please install it and run 'gh auth login'."
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}Not authenticated with gh.${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${GREEN}=== Spack OCI Buildcache Cleaner ===${NC}"

USER_NAME=$(gh api user -q .login)
# Default from CI workflow
DEFAULT_PACKAGE="sp5505-spack-buildcache"

if [ -z "$PACKAGE_NAME" ]; then
    PACKAGE_NAME="$DEFAULT_PACKAGE"
    echo -e "No package specified, defaulting to CI cache: ${YELLOW}${PACKAGE_NAME}${NC}"
fi

echo "Target: $USER_NAME/$PACKAGE_NAME"

if [ "$FORCE" -ne 1 ]; then
    echo -e "${YELLOW}WARNING: This will delete ALL versions of package '$USER_NAME/$PACKAGE_NAME'.${NC}"
    echo "This effectively wipes the Spack buildcache."
    echo "Are you sure? (type 'yes' to confirm)"
    read -r CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo "Fetching versions..."
# Get all version IDs
VERSION_IDS=$(gh api "users/$USER_NAME/packages/container/$PACKAGE_NAME/versions" --paginate -q '.[].id')

if [ -z "$VERSION_IDS" ]; then
    echo "No versions found for package $PACKAGE_NAME."
    exit 0
fi

COUNT=$(echo "$VERSION_IDS" | wc -l)
echo "Found $COUNT versions. Deleting..."

for id in $VERSION_IDS; do
    echo "Deleting version $id..."
    # We use || true to continue if one fails (e.g. race condition)
    gh api -X DELETE "users/$USER_NAME/packages/container/$PACKAGE_NAME/versions/$id" || true
done

echo -e "${GREEN}Cache cleaned!${NC}"
