#!/usr/bin/env bash
# reset_coolstore.sh ─ wipe & refetch the Coolstore sample and re‑init git

set -euo pipefail

APP_DIR="coolstore"    # must match SAMPLE_APP_DIR / root_path
FETCH_SCRIPT="fetch.sh"

echo "🗑  Removing previous $APP_DIR ..."
rm -rf "$APP_DIR"

echo "⬇️  Fetching fresh Coolstore sample ..."
bash "$FETCH_SCRIPT"

echo "🔧  Re‑initialising Git repository ..."
cd "$APP_DIR"
git init -q
git add . >/dev/null
git commit -q -m "baseline before Kai analysis"

echo "✅  Coolstore reset complete."
