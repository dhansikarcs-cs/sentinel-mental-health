#!/bin/sh
# ── Sentinel — Azure App Service startup script ─────────────────────────
# Works for BOTH deploy styles:
#
#   1. App Service CODE deploy (GitHub Actions zip deploy, no Docker):
#        app lives in /home/site/wwwroot; Oryx builds a venv in antenv/
#        Startup command:  bash /home/site/wwwroot/azure-startup.sh
#
#   2. Container deploy (Dockerfile.azure):
#        app lives in /app — invoked automatically by the image CMD.
#
# What it does:
#   1. Detects the app layout and activates the virtual environment
#      (Oryx `antenv` on code deploys).
#   2. Ensures the SQLite database lives on the PERSISTENT /home mount
#      (plain container storage is wiped on restart/scale — /home survives).
#   3. Runs the demo seeder EXACTLY once (guarded by a marker file), so
#      demo accounts exist on first boot but data is never wiped on restart.
#   4. Starts uvicorn on the port App Service expects (WEBSITES_PORT → PORT
#      → 8000; the Python built-in runtime listens on 8000).
#
# Required App Service settings: JWT_SECRET, ENCRYPTION_PASSPHRASE,
# ENCRYPTION_SALT, ENCRYPTION_REQUIRED=true, COOKIE_SECURE=true.
# Optional: SEED_DEMO=true (default) to create the demo clinic accounts.

set -e

# ── 0. Detect layout + interpreter ──────────────────────────────────────
if [ -d /home/site/wwwroot/app ]; then
    APP_DIR="/home/site/wwwroot"        # App Service code deploy (Oryx)
elif [ -d /app/app ]; then
    APP_DIR="/app"                      # container deploy
else
    APP_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
cd "$APP_DIR"

# Code deploys: Oryx creates the virtualenv at $APP_DIR/antenv — activate it
# so `python` resolves to the venv interpreter with our dependencies.
if [ -f "$APP_DIR/antenv/bin/activate" ]; then
    . "$APP_DIR/antenv/bin/activate"
    echo "startup: activated Oryx virtualenv at $APP_DIR/antenv"
fi

PY=python
command -v python >/dev/null 2>&1 || PY=python3

PORT_TO_USE="${WEBSITES_PORT:-${PORT:-8000}}"
export PORT="${PORT_TO_USE}"

# ── 1. Persist the SQLite database on /home ─────────────────────────────
if [ -z "${DATABASE_URL:-}" ] && [ -d /home ]; then
    DB_DIR="/home/data"
    mkdir -p "$DB_DIR" 2>/dev/null || true
    if touch "$DB_DIR/.write-test" 2>/dev/null; then
        rm -f "$DB_DIR/.write-test"
        export DATABASE_URL="sqlite:////home/data/sentinel.db"
        echo "startup: using persistent SQLite at $DB_DIR/sentinel.db"
    else
        echo "startup: /home not writable — falling back to local storage"
    fi
fi

# ── 2. One-time demo seed (never wipes existing data) ───────────────────
if [ "${SEED_DEMO:-true}" = "true" ]; then
    MARKER=""
    case "${DATABASE_URL:-}" in
        sqlite:////home/*)
            # /home is shared across restarts AND scale-out instances —
            # the marker makes multi-instance startups race-safe.
            MARKER="/home/data/.demo-seeded"
            ;;
        sqlite:///*)
            # SQLite next to the app: /app/data (container volume) or
            # $APP_DIR/data (code deploy). Use a marker if writable.
            if touch "$APP_DIR/data/.marker-test" 2>/dev/null; then
                rm -f "$APP_DIR/data/.marker-test"
                MARKER="$APP_DIR/data/.demo-seeded"
            fi
            ;;
    esac

    if [ -n "$MARKER" ]; then
        if [ ! -f "$MARKER" ]; then
            echo "startup: seeding demo clinic data (one-time)…"
            # Run from the app dir so relative imports and data paths resolve.
            "$PY" seed_clinic.py && echo "startup: seed OK"
            touch "$MARKER"
        else
            echo "startup: demo data already seeded — skipping"
        fi
    else
        echo "startup: SEED_DEMO set but no writable marker location — skipping seed"
    fi
fi

# ── 3. Launch ────────────────────────────────────────────────────────────
echo "startup: launching uvicorn on 0.0.0.0:${PORT_TO_USE}"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT_TO_USE"
