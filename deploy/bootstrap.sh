#!/usr/bin/env bash
# Runs ON the VPS (Ubuntu 24.04 LTS), once, after the repo is copied to /opt/sentinel.
set -euo pipefail

APP=/opt/sentinel
cd "$APP/deploy"

# 1. Tooling + Docker (plain Ubuntu image from the OS picker has no Docker).
if ! command -v curl >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq curl
fi
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
docker compose version

# 2. One-time secret. Never regenerate afterwards (invalidates all logins).
if [ ! -f .env ]; then
  cp .env.example .env
  SECRET="$(openssl rand -hex 32)"
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${SECRET}|" .env
fi

# 3. Persist the verified local DB (demo accounts + 14 real ring rows, no fakes).
mkdir -p data
if [ ! -f data/sentinel.db ] && [ -f "$APP/backend/data/sentinel.db" ]; then
  cp "$APP/backend/data/sentinel.db" data/sentinel.db
fi
# backend container runs as uid 1001 (sentinel).
chown -R 1001:1001 data
chmod 600 .env

# 4. Host firewall. NOTE: the Hostinger panel firewall must ALSO allow
#    80/tcp and 443/tcp, otherwise Caddy cannot obtain the TLS certificate.
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

# 5. Build + start.
docker compose -f docker-compose.prod.yml up -d --build

echo "---- waiting for backend health (checked INSIDE the container) ----"
for i in $(seq 1 40); do
  if docker compose -f docker-compose.prod.yml exec -T sentinel-backend \
       python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" \
       >/dev/null 2>&1; then
    echo "backend healthy"
    break
  fi
  sleep 3
done

docker compose -f docker-compose.prod.yml ps
echo
echo "Caddy needs DNS A record -> this IP before it can issue the TLS cert."
echo "Tail TLS logs with: docker compose -f docker-compose.prod.yml logs -f caddy"
