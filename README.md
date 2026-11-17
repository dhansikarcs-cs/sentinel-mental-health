# Sentinel

**Live:** https://sentinelpsytech.com &nbsp;·&nbsp; **API docs:** https://sentinelpsytech.com/docs &nbsp;·&nbsp; **Health:** https://sentinelpsytech.com/health

Sentinel is a mental-health support platform that pairs private journaling with an AI companion, real-time emotion scoring, and automatic crisis detection, all feeding a clinician triage and admin oversight layer that keeps sensitive AI work safe, auditable, and production-ready.

> **Stack:** FastAPI + SQLAlchemy (SQLite) · React 19 + TypeScript + Vite · PWA · Docker Compose + Caddy (automatic HTTPS), deployed on our own VPS. AI keys are left as blank environment variables; the offline rule-based fallback works without them.

> **Status:** 222 backend tests green · ruff lint/format clean · TypeScript + Vite build green · real Viaking R30 PRO wearable data only — no simulated physiology.

---

## Live links

| | |
|---|---|
| App | https://sentinelpsytech.com |
| Interactive API docs | https://sentinelpsytech.com/docs |
| OpenAPI schema | https://sentinelpsytech.com/openapi.json |
| Health check | https://sentinelpsytech.com/health |

An earlier hosted demo has been retired. The links above are the single, current deployment.

---

## What Sentinel does

- **Private journaling** with AI-assisted summaries — a warm companion tone for the patient, a structured clinical summary for the psychologist
- **Emotion scoring** — an in-repo 28-class GoEmotions classifier, with a deterministic rule fallback when AI is unavailable
- **Journal ↔ vitals comparison** — uses only stored journal text and genuinely measured wearable signals; reports `insufficient_data` instead of estimating
- **Automatic crisis detection** with deterministic escalation and an active-crisis WebSocket broadcast
- **Clinician workspace** — triage, clinical notes, bookings, follow-ups, session reports, export center
- **Admin oversight** — RBAC, hash-chained audit log, rate limiting, per-device ring tokens
- **Editable profile** — display name, clinic, occupation, password change with current-password verification

---

## Wearable data — real only

The wearable is a **Viaking R30 PRO** (Yucheng YCBT protocol over Web Bluetooth).

- This unit **does not retain stored history**. Readings are captured **live** from CRC-validated `06 01` frames, using only documented handshake and measurement start/stop opcodes. No DFU, reset, OTA, history deletes, or unknown writes; raw packets are preserved.
- Capture requires **Chrome/Edge over HTTPS**, a user gesture, the ring within ~10 m, and **an open browser tab**. A hosted server has no Bluetooth, and a service worker / PWA cannot keep a BLE link alive in the background.
- Only signals the ring actually measured are stored. Stress, sleep, SpO₂, HRV, temperature and blood pressure stay `NULL` (shown as dashes) when not measured. HRV is never derived from bpm, and no value is defaulted or invented.
- Every reading is written to an IndexedDB queue **before** the network call, so closing a tab cannot lose a captured reading. Unattended 24/7 capture would require a dedicated always-on gateway device near the ring.
- `hardware_lab/` contains **EXPERIMENTAL** protocol probes and raw packet captures. These measurements are unvalidated, are **not a clinical assessment**, and must not be used for clinical conclusions.

---

## Repository layout

```
backend/     FastAPI app: api/, core/, models/, schemas/, services/, ml/, events/, workers/, repositories/, tests/
frontend/    React 19 + Vite SPA: src/{api,components,hooks,pages,ring,stores}, public/, nginx.conf, Dockerfile
deploy/      Production Docker Compose, Caddyfile, bootstrap.sh, DEPLOY.md runbook
docs/        Design notes, research, and docs/sentinel-archive/ (17-file provenance-labeled archive)
scripts/     Ring API tests, ML training/eval, seeding
hardware_lab/  EXPERIMENTAL protocol work — outside the backend, excluded from CI and the clinical pipeline
```

---

## Local development

### Backend

```bash
cd backend
python -m venv venv
pip install -r requirements.txt
python -m pytest tests -q
uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm ci
npm run build
npm run dev
```

### Full stack

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

See `deploy/DEPLOY.md` for the full VPS runbook. Deployment secrets live only in `deploy/.env` (gitignored); no keys or tokens are committed to this repository.

---

## Testing

```bash
python -m ruff check backend/
python -m ruff format --check backend/
python -m pytest backend/tests -q          # 222 tests
cd frontend && npx tsc -b --pretty false && npm run build
```

The GitHub Actions workflow runs these same gates plus Docker image builds for both services.

---

## Demo accounts

Demo sign-in shortcuts are shown on the login screen of the live app. Credentials are intentionally not listed here.

---

## Documentation

- `deploy/DEPLOY.md` — production deployment, TLS, firewall, backup/rollback runbook
- `docs/sentinel-archive/` — 17-file project archive with `[REPO]` / `[GIT]` / `[SESSION]` / `[INFERRED]` / `[HISTORICAL]` / `[CONFLICT]` provenance labels. Historical and conflicting versions are kept, not silently rewritten.
- `SENTINEL_CODEBOOK.md` — per-file code explanation from the original prototype

---

## License

All Rights Reserved — see [LICENSE](LICENSE).
