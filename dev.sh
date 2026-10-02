#!/usr/bin/env bash
# Sentinel local launcher — starts API (default port 8000) + web app (port 5173).
# Usage:  ./dev.sh            (foreground; Ctrl+C stops both)
#         API_PORT=8001 ./dev.sh   (custom API port, e.g. when 8000 is taken)
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8000}"
# If the port is already in use (another project, a stale server…), walk up.
for i in $(seq 1 10); do
  if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN > /dev/null 2>&1; then
    echo "! Port $API_PORT is in use — trying $((API_PORT + 1))"
    API_PORT=$((API_PORT + 1))
  else
    break
  fi
done

if [ ! -d backend/venv ]; then
  echo "→ Creating backend venv (first run)…"
  python3 -m venv backend/venv
  backend/venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  echo "→ Installing frontend deps (first run)…"
  (cd frontend && npm install)
fi
if [ ! -f .env ]; then
  echo "✗ Missing .env — copy .env.example and set ENCRYPTION_PASSPHRASE first."
  exit 1
fi

echo "→ Seeding clinic demo data (admin + 30 clients)…"
(cd backend && set -a; source ../.env; set +a; ./venv/bin/python seed_clinic.py)

echo "→ Starting API on :$API_PORT…"
(cd backend && set -a; source ../.env; set +a; exec ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT") &
API_PID=$!

echo "→ Starting web app on :5173…"
(cd frontend && VITE_API_TARGET="http://localhost:$API_PORT" exec npm run dev) &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null; exit 0' INT TERM

# Wait for the API to come up
for i in $(seq 1 30); do
  if curl -sf -m 2 "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  Sentinel is running"
echo ""
echo "  Web app:   http://localhost:5173"
echo "  API:       http://localhost:$API_PORT/health"
echo ""
echo "  Logins:"
echo "    admin  / password123   (clinic oversight)"
echo "    cel    / 1234          (psychologist · 10 clients)"
echo "    marcus / 4321          (psychologist · 10 clients)"
echo "    maya_k / sentinel123   (sample teen client)"
echo ""
echo "  Ctrl+C stops both servers."
echo "════════════════════════════════════════════════════"
echo ""

wait
