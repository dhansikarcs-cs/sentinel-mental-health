# Sentinel — single-VPS deployment runbook

Domain: `sentinelpsytech.com` (GoDaddy, UPI). Host: Hostinger India VPS KVM 1,
UPI, monthly billing.

## LIVE DEPLOY (2026-11-16) — current state
- VPS IP: **189.31.34.138**, Ubuntu 24.04.5 LTS, Docker Compose v5.7.1,
  3.8 GiB RAM / 46 GiB free. SSH key `deploy/keys/sentinel_deploy` (key-only).
- Stack deployed at `/opt/sentinel` via `bootstrap.sh`; all 3 containers Up,
  backend healthy. Verified: /health 200, logins 200, unauth 401, SPA 200,
  /api proxy 401, ring-button string in bundle, 14 real ring rows.
- Hostinger managed panel firewall: while OFF all ports are open (22/80/443
  reachable because Caddy listens). If the managed firewall is activated, its
  default policy is **DROP ALL**, so these ACCEPT rules must exist FIRST or SSH
  is locked out:
  | Action | Protocol | Port | Source |
  |---|---|---|---|
  | Accept | SSH / TCP | 22 | Anywhere |
  | Accept | HTTP / TCP | 80 | Anywhere |
  | Accept | HTTPS / TCP | 443 | Anywhere |
  Do NOT expose internal Docker ports (8000, 10000, 2019). Add SSH rule first,
  then toggle the group ON (takes ~2-5 min). `ufw` is inactive; the panel
  firewall is the effective one.
- Password SSH disabled via `/etc/ssh/sshd_config.d/00-sentinel.conf`
  (`PasswordAuthentication no`, `PermitRootLogin prohibit-password`). Key-only
  login re-verified after reload.
- **DONE (2026-11-16):** GoDaddy DNS single `A @` record edited from `Parked`
  to `189.31.34.138`; `www` CNAME kept. Hostinger managed firewall group
  `sentinel-web` activated with Accept TCP 22/80/443 Anywhere + default drop.

## TLS note (important if redeploying)
Caddy had attempted the cert repeatedly while DNS still pointed at GoDaddy's
parking IPs, and had fallen back to **Let's Encrypt STAGING** (untrusted cert)
with a 10-minute retry backoff. After DNS was fixed, the fix was:
`stop caddy` -> remove `/data/caddy/certificates` + `/data/caddy/acme` inside
the caddy_data volume -> `up -d caddy`. It then obtained a **production**
certificate via tls-alpn-01 in seconds. Do not skip this reset after a long
failed-attempt history, or the site may serve an untrusted staging certificate.

## FINAL LIVE VERIFICATION (all green, 2026-11-16)
From outside, over real HTTPS with certificate validation:
```
GET  /health                      -> 200
POST /api/auth/login alaya/4321   -> 200
POST /api/auth/login cel/1234     -> 200
GET  /api/patients/me/wellness    -> bpm 81, spo2 98.0, hrv 41, temp 35.86,
                                     stress None, sleep None   (no fakes)
POST /api/discrepancy/check-patient (patient + psych) -> 200, real bpm/hrv
     patient comparing someone else -> 404 (RBAC)
     unauth /api/patients/me/wellness -> 401
GET  /  and /trustee              -> 200 SPA
bundle contains: "Ring not connected", "Wearable Ring",
                 "Bluetooth unavailable", "Journal ↔ Vitals Comparison"
```
Certificate issued by production `acme-v02.api.letsencrypt.org`; auto-renewal
is handled by Caddy (no cron needed).

## UPDATE (2026-11-16): empty vitals state, last-sync nudge, psych vitals space
Problem: with 0 ring rows, `/patients/me/wellness` returned `ring: null` and
`Dashboard.tsx` hid the ENTIRE Wearable Vitals card — so a new patient saw blank
space instead of dashes. That was real data absence (no fabrication), but bad UX.

Changes (local `sentinel3` + redeployed live):
- `_ring_vitals(db, username)` helper in `backend/app/api/patients.py`: latest
  genuinely measured value PER signal + `last_synced`, `sync_due` (>24h or no
  rows), `reading_count`. Used by both `/patients/me/wellness` and the new
  `GET /patients/{username}/vitals`.
- `/patients/{username}/vitals` RBAC: self OR the patient's ASSIGNED
  psychologist (verified: Dhansika->Sankari 200, Dhansika->alaya 403,
  cel->Sankari 403). Never invents values; empty patient -> ring=null.
- New shared `frontend/src/components/RingVitalsCard.tsx` — ALWAYS renders the
  vitals space with dashes + "No readings yet / connect your ring" + relative
  "Last synced" + "Sync due today". Used by patient Dashboard and, per patient,
  psychologist triage.
- Layout side panel: patient gets a last-sync line + reading count; psychologist
  gets a "Patient ring status" list (name, synced/no vitals, last sync, due).
  Both refresh every 60s.

Verified live: Sankari ring=None/last_synced=None/sync_due true/count 0;
alaya bpm 81/count 14; RBAC 200/403 as above; deployed bundle contains
"No readings yet", "Last synced", "Sync due today", "Patient ring status".
ruff clean, 222 pytest pass, tsc 0, vite build 0.

Remaining: all changes are still local/uncommitted in `sentinel3`. The old
Render deployment (`sentinel-mental-health` repo) is untouched; do not push
this repo to the wrong origin. Ring data still arrives from the patient's own
browser via Web Bluetooth over HTTPS once a day — the server has no BLE radio.
A PWA/service worker CANNOT keep BLE alive in the background (browser limit);
the ring stores its own history and the IndexedDB queue survives tab closes.

Region: audience is mostly **India + New Zealand**, so choose the Asian
midpoint **Malaysia** (or Indonesia if Malaysia is not offered) at setup —
NOT Boston. Hostinger's VPS region is **fixed after initial setup**, so this is
the one irreversible choice. Static assets can later be cached near both
audiences via the free CDN (Hostinger CDN has a Sydney PoP, closest to NZ).

## What YOU do (panel only)
1. Dev tools → **VPS** → **Set up VPS**.
2. Plan: **KVM 1** (1 vCPU / 4 GB RAM / 50 GB NVMe) — enough for the whole
   stack; KVM 2/4/8 are unnecessary and "upgrade anytime" makes this risk-free.
   Billing: **shortest term available (1 month)**. The advertised ₹599/mo is
   the 24-month price (~₹14,376 due today, renews ₹999/mo); monthly is higher
   (~₹1,000–1,650) but correct for a one-month pilot. A 30-day money-back
   guarantee exists as a fallback. Ignore the bundled "free domain" — the
   `.com` is already owned at GoDaddy.
3. Location: **Malaysia** (or **Indonesia** if Malaysia isn't listed) — the
   midpoint for India + New Zealand audiences. NOT USA/Boston, NOT India.
   VPS region is fixed after setup, so pick this carefully.
   OS: **Ubuntu 24.04 LTS** (plain — the OS picker has no "with Docker" option;
   `bootstrap.sh` installs Docker via get.docker.com). Skip 26.10 (interim,
   short support), 26.04 LTS (too new), 22.04 LTS (older). Do NOT pick Alpine
   (musl breaks numpy/cryptography wheels) or the RHEL-family / Kali / Arch
   images. The host OS only runs Docker; the app is fully containerised.
4. Pay: **UPI**. Additional features: enable **Docker manager** only (free GUI
   for container status). Skip **Monarx malware scanner** (extra agent, false
   positives) and **Daily auto-backups** (paid; free weekly backups are included
   and the SQLite DB is one file).
5. GoDaddy DNS → add **A record**: `@` → VPS IP, TTL 600. (Optional: CNAME `www` → `@`.)
6. VPS dashboard → **SSH keys** → add this public key (generated locally,
   private half stays on the laptop and is gitignored):
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEzD4gX5qme2jioXDZpjK+l/VYQ+gvNSAL0zU39syq7y sentinel-deploy
   ```
7. Send me: **VPS IP** only. I connect with
   `ssh -i deploy/keys/sentinel_deploy root@<IP>` — no password needed.
   The root password was shared in chat, so treat it as exposed: disabling
   password SSH is the FIRST hardening step after connecting.

Private key: `deploy/keys/sentinel_deploy` (never commit; already in .gitignore).

Note: Hostinger's terms require the account holder to be 18+; a parent/guardian
or co-founder should be the account holder. No KYC/PAN/Aadhaar upload needed.

## What I do (from your laptop, via ssh/scp — both already installed)
```powershell
$KEY = "C:\Users\dhans\Desktop\sentinel3\deploy\keys\sentinel_deploy"
$IP  = "<VPS_IP>"

# 1. Copy the repo (excluding venv/node_modules/.git/secrets/db temps) to the VPS
cd C:\Users\dhans\Desktop\sentinel3
tar --exclude=backend/venv --exclude=backend/data --exclude=frontend/node_modules `
    --exclude=frontend/dist --exclude=.git --exclude='*.db' --exclude='*.db-wal' `
    --exclude='*.db-shm' --exclude='*.log' --exclude=__pycache__ `
    --exclude=.pytest_cache --exclude=.ruff_cache `
    --exclude=deploy/keys --exclude=deploy/.env --exclude=deploy/data `
    -czf sentinel.tgz backend frontend deploy
scp -i $KEY sentinel.tgz "root@${IP}:/opt/"

# Copy ONLY the verified real DB (backend/data/ also holds pytest junk locally).
scp -i $KEY backend/data/sentinel.db "root@${IP}:/opt/sentinel_sentinel.db"

# 2. Unpack + bootstrap on the box
ssh -i $KEY "root@${IP}" "mkdir -p /opt/sentinel && tar -xzf /opt/sentinel.tgz -C /opt/sentinel && mkdir -p /opt/sentinel/backend/data && mv /opt/sentinel_sentinel.db /opt/sentinel/backend/data/sentinel.db && bash /opt/sentinel/deploy/bootstrap.sh"
```
`bootstrap.sh` installs Docker if needed, generates a one-time `JWT_SECRET`,
seeds the verified local DB, opens 80/443, and runs `docker compose up -d --build`.

## Files
- `docker-compose.prod.yml` — backend (PORT 8000, SQLite volume, prod env) +
  frontend (PORT 10000, BACKEND_URL with `/api`) + Caddy (80/443, auto-HTTPS).
- `Caddyfile` — routes `/api/*`, `/health*`, `/v1/*`, WebSockets to backend;
  everything else to frontend nginx. Caddy preserves the `/api` prefix, so
  FastAPI's `APIRouter(prefix="/api")` works unchanged.
- `.env.example` → `.env` on the box. AI keys are blank so the co-founder can
  fill `GROQ_API_KEY` / `ALLOW_CLOUD_AI` later without touching any config.
- `bootstrap.sh` — one-time server setup.

## Production env decisions (already applied)
- `ENCRYPTION_REQUIRED=false` for the pilot: the migrated local DB contains
  plaintext journals. For real patient data, use a FRESH DB + a fixed
  `ENCRYPTION_PASSPHRASE` + a fixed `SENTINEL_ENCRYPTION_SALT`; the salt must
  never change or old journals become permanently unreadable.
- `RUN_WORKERS=false`, `RATE_LIMIT_BACKEND=memory`, `WS_PUBSUB=off` — correct for
  a single-process SQLite box; no separate scheduler/Postgres needed.
- `COOKIE_SECURE=true`, `CORS_ORIGINS`/`SENTINEL_ACK_LINK` → the real domain.
- SQLite with a persistent bind mount is fine for one patient / one month.

## Post-deploy hardening (I do this)
After the initial password login, add an SSH key and disable password auth:
- `~/.ssh/authorized_keys` gets my key; `PasswordAuthentication no`,
  `PermitRootLogin prohibit-password` in `/etc/ssh/sshd_config`; `systemctl reload ssh`.
- Keep `ufw` limited to 22/80/443. Caddy manages TLS renewal automatically.

## DNS / TLS ordering (important)
Caddy can only issue the Let's Encrypt certificate AFTER the A record resolves
to the VPS IP. Set the GoDaddy A record first, then run bootstrap. Caddy retries
cert issuance automatically, so a late DNS change just needs a few minutes.

**Hostinger panel firewall:** open **80/tcp and 443/tcp** there too (SSH 22 is
usually already open). The panel firewall is separate from `ufw`; `bootstrap.sh`
only touches `ufw` if it is already active. Without 80/443 open at the panel,
Caddy cannot complete the HTTP-01 challenge.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Site loads but `/api/*` 404 | Caddy `@backend` matcher must include `/api/*`; check `Caddyfile` |
| Login 401 after restart | `JWT_SECRET` was regenerated. Keep `deploy/.env` stable |
| Journals show `[ACCESS DENIED / DATA CORRUPTED]` | Encryption passphrase or salt changed. Restore both from `.env`, or keep `ENCRYPTION_REQUIRED=false` |
| TLS stays pending | DNS A record not pointing at IP, or panel firewall blocking 80/443 |
| `/health` OK but SPA blank | `docker compose logs sentinel-frontend`; nginx template needs `PORT` + `BACKEND_URL` |
| Backend OOM on first build | 4 GB is enough; build `--build` sequentially if needed: `docker compose build sentinel-backend && docker compose build sentinel-frontend` |

Inspect: `docker compose -f deploy/docker-compose.prod.yml logs -f --tail=100`

## Verify after deploy
```
https://sentinelpsytech.com/health          -> 200
https://sentinelpsytech.com/                -> SPA
login alaya / 4321  -> Dashboard, ring button + vitals + comparison
login cel / 1234    -> triage + comparison
```
Ring data still comes from the patient's own browser (Web Bluetooth) over HTTPS
once a day; the server has no BLE radio. No value is invented.

## Important
All changes are local/uncommitted in `sentinel3`. The live Render app deploys
from the separate `sentinel-mental-health` repo — do not push this repo to the
wrong origin. Revert `backend/app/ml/model_registry.json` if dirty before commits.
