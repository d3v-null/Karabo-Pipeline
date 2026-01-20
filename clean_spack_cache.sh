#!/bin/bash
set -euo pipefail

# Script to clean (delete) the Spack OCI buildcache stored in GHCR.
# Uses 'gh' CLI to delete the package versions.
#
# Usage: ./clean_spack_cache.sh [options] [package_name]
#
# Options:
#   --force             Skip confirmation prompt
#   --older-than DAYS   Delete versions older than DAYS (default: delete all)
#   --keep-last N       Keep the N most recent versions (default: 0, delete all)
#
# Defaults to 'sp5505-spack-buildcache' if package_name is not provided.
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
OLDER_THAN_DAYS=""
KEEP_LAST=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=1
            shift
            ;;
        --older-than)
            OLDER_THAN_DAYS="$2"
            shift 2
            ;;
        --keep-last)
            KEEP_LAST="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: ./clean_spack_cache.sh [--force] [--older-than DAYS] [--keep-last N] [package_name]"
            exit 1
            ;;
        *)
            if [ -z "$PACKAGE_NAME" ]; then
                PACKAGE_NAME="$1"
            else
                echo "Error: Package name already specified as '$PACKAGE_NAME', unexpected argument '$1'"
                exit 1
            fi
            shift
            ;;
    esac
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
    MSG="WARNING: This will delete versions of package '$USER_NAME/$PACKAGE_NAME'"

    if [ -n "$OLDER_THAN_DAYS" ]; then
        MSG="$MSG older than $OLDER_THAN_DAYS days"
    fi

    if [ -n "$KEEP_LAST" ]; then
        MSG="$MSG, keeping the last $KEEP_LAST versions"
    fi

    if [ -z "$OLDER_THAN_DAYS" ] && [ -z "$KEEP_LAST" ]; then
        MSG="$MSG (ALL VERSIONS)"
        echo -e "${YELLOW}$MSG.${NC}"
        echo "This effectively wipes the Spack buildcache."
    else
        echo -e "${YELLOW}$MSG.${NC}"
    fi

    echo "Are you sure? (type 'yes' to confirm)"
    read -r CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo "Fetching versions..."

# Build jq filter based on criteria
JQ_FILTER='.'

# Filter by age if requested
if [ -n "$OLDER_THAN_DAYS" ]; then
    # Calculate cutoff date in ISO8601 format
    if [[ "$OSTYPE" == "darwin"* ]]; then
        CUTOFF_DATE=$(date -v-${OLDER_THAN_DAYS}d -u +"%Y-%m-%dT%H:%M:%SZ")
    else
        CUTOFF_DATE=$(date -d "-${OLDER_THAN_DAYS} days" -u +"%Y-%m-%dT%H:%M:%SZ")
    fi
    echo "Filtering versions older than $CUTOFF_DATE..."
    JQ_FILTER="$JQ_FILTER | map(select(.created_at < \"$CUTOFF_DATE\"))"
fi

# Apply keep-last if requested (sort by created_at desc, then drop first N)
if [ -n "$KEEP_LAST" ]; then
    echo "Keeping last $KEEP_LAST versions..."
    # Sort by creation date descending, then skip the first N
    JQ_FILTER="$JQ_FILTER | sort_by(.created_at) | reverse | .[$KEEP_LAST:]"
fi

# Final projection to get IDs
JQ_FILTER="$JQ_FILTER | .[].id"

# Get version IDs with filtering
VERSION_IDS=$(gh api "users/$USER_NAME/packages/container/$PACKAGE_NAME/versions" --paginate --jq "$JQ_FILTER")

if [ -z "$VERSION_IDS" ]; then
    echo "No matching versions found for package $PACKAGE_NAME."
    exit 0
fi

COUNT=$(echo "$VERSION_IDS" | wc -l)
echo "Found $COUNT versions. Deleting in parallel (batch size 10)..."

# Export variables for subshells
export USER_NAME
export PACKAGE_NAME

# Use xargs to run in parallel
echo "$VERSION_IDS" | xargs -P 10 -I {} bash -c '
    id="{}"
    echo "Deleting version $id..."
    gh api -X DELETE "users/$USER_NAME/packages/container/$PACKAGE_NAME/versions/$id" >/dev/null 2>&1 || echo "Failed to delete $id"
'

echo -e "${GREEN}Cache cleaned!${NC}"
