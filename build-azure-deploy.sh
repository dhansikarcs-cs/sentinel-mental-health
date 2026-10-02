#!/bin/sh
# ── Sentinel — build the folder you right-click deploy from VS Code ─────
#
#   sh build-azure-deploy.sh
#
# Produces ./azure-deploy/ containing everything the web app needs:
#   backend Python source + requirements.txt, the built frontend
#   (frontend/dist), .deployment (enables the Oryx remote build) and
#   azure-startup.sh.
#
# Then in VS Code:
#   Azure panel → App Service → right-click your **Python 3.12** web app
#   → "Deploy to Web App…" → pick the azure-deploy folder.
#
# .vscode/settings.json already points the deploy button at this folder
# (appService.deploySubpath = "azure-deploy"), so re-running this script +
# hitting Deploy is the whole workflow.

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
STAGE="$ROOT/azure-deploy"

# ── 1. Build the frontend ────────────────────────────────────────────────
echo "==> Building frontend (npm ci + vite build)…"
cd "$ROOT/frontend"
npm ci --no-audit --no-fund
npm run build

# ── 2. Stage backend + static frontend + Azure files ────────────────────
echo "==> Staging $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE"

rsync -a \
    --exclude 'venv/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude 'data/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude '.mypy_cache/' \
    --exclude '.ruff_cache/' \
    --exclude 'node_modules/' \
    "$ROOT/backend/" "$STAGE/"

mkdir -p "$STAGE/frontend"
cp -R "$ROOT/frontend/dist" "$STAGE/frontend/dist"
cp "$ROOT/.deployment" "$ROOT/azure-startup.sh" "$STAGE/"

echo ""
echo "✓ Staged $(find "$STAGE" -type f | wc -l | tr -d ' ') files in azure-deploy/"
echo "Next: VS Code → Azure panel → App Service → right-click your"
echo "Python 3.12 web app → \"Deploy to Web App…\" → azure-deploy folder."
