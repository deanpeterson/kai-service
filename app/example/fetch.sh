#!/usr/bin/env bash

#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# Usage examples
#   ./fetch.sh                            # → clone Coolstore into ./coolstore
#   ./fetch.sh https://github.com/foo/bar # → clone bar  into ./bar
#   ./fetch.sh https://github.com/foo/bar my-app   # → clone into ./my-app
# ──────────────────────────────────────────────────────────────

DEFAULT_URL="https://github.com/konveyor-ecosystem/coolstore.git"

GIT_URL=${1:-$DEFAULT_URL}                         # 1st arg or default
TARGET_DIR=${2:-$(basename "${GIT_URL%.git}")}     # 2nd arg or repo name

echo "Cloning ${GIT_URL}  →  ${TARGET_DIR}"
git clone --depth 1 "${GIT_URL}" "${TARGET_DIR}"

