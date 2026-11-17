# 04 — SYSTEM ARCHITECTURE

*Architecture constitution, layers, containers, data flow, networking, storage, deployment
topologies. Actual implementations, proposed designs and abandoned approaches are separated.*

---

## 1. Architecture constitution `[REPO]`

From `docs/ARCHITECTURE.md` (introduced by commit `36dd277`, 2026-08-03):

> "every file has exactly one home, and every value has exactly one owner (Constitution #6). A change that needs the same value in two places is a bug in the architecture, not an opportunity."

Known numbered constitution items referenced across the codebase: **#5** (transport: "device keeps
its own copy until ACK"), **#6** (single owner/single home), **#8** (consultation-first central
workflow). A separate "transport constitution" was introduced by `a824327` (2026-08-04, design
only). The full enumerated list is not present in the accessible docs. `[UNKNOWN]`

**Layering:** `api → services → repositories → models`; cross-cutting `core` (config, health,
logging, middleware), `ml` (crisis_policy, risk_engine, emotion_classifier, model_registry),
`events` (pub/sub + append-only event store / audit log), `workers` (ai_worker, notification).
"Requests flow top-down; a route handler never touches a model directly." `[REPO]`

---

## 2. Implemented system architecture (FastAPI + React) `[REPO]`

```
[ Wearable / ring ]
   ├── BLE GATT (bleak, Windows or browser Web Bluetooth)
   ├── Vendor cloud API (Oura / Ultrahuman / Jport)
   └── (historically) SimulatedRing  ← REMOVED in Nov 2026
        │
        ▼
  RingSource adapter → canonical SensorData
        │
        ▼
  POST /api/ring/data  (X-Device-Serial + X-Device-Token  OR  patient JWT)
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ nginx / Caddy reverse proxy  (TLS termination)            │
  │   /api/*  → backend   |   everything else → SPA          │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  FastAPI backend (Python 3.11, uvicorn, ~120 routes / 29 router modules)
    ├── core: config, database, security, rbac, rate limiting, request-id,
    │         structured errors, security headers, encrypted_fields, leader, ws_pubsub
    ├── api: auth, patients, psychologists, journal, mood, crisis, ring,
    │        discrepancy, agents, triage, timeline, bookings, followups, ws, ...
    ├── ml: emotion_classifier (TF-IDF+LogReg), risk_engine, crisis_policy, model_registry
    ├── services: ai_service (3-tier), patient_context, plain_insights, timeline_service,
    │             audit, notification, websocket_manager, search, event store
    ├── repositories & models (SQLAlchemy)
    └── workers: ai_worker, reminder_worker, celebrations_worker, runner
        │
        ▼
  SQLite (WAL, single node)  OR  PostgreSQL 17 (multi-worker)
        │
        ▼
  React 19 + TypeScript + Vite SPA (PWA: manifest, sw.js, icons)
```

**Frontend state:** custom pub/sub auth store (`frontend/src/stores/auth.ts`, ~50 lines) instead
of Redux/Zustand; tokens in `sessionStorage` (per-tab sessions); BASE `/api` in
`frontend/src/api/client.ts`; durable outbox (`api/outbox.ts`) and ring queue
(`ring/ringQueue.ts`, IndexedDB `sentinel-ring-queue`). `[REPO][SESSION]`

---

## 3. Data flow (verified) `[REPO]`

From `docs/research/PHASE1_REPO_AUDIT.md` §3:

- **Journal:** text → `ai_service.summarize_journal()` → emotion_classifier (TF-IDF + OneVsRest
  LogReg, deterministic/local) → `risk_engine.assess_risk_with_explainability()` (keyword +
  emotion blend, score 1–10) → optional LLM summary (Ollama local / Groq gated) with echo guard +
  JSON parse → persisted; risk → notification / auto-trigger via `ai_worker`.
- **Ring:** `POST /ring/data` → validated → `RingSensorLog` + mirrored `SensorReading`.
- **Discrepancy:** `POST /discrepancy/check` → rules compare text sentiment vs biometric stress;
  `POST /discrepancy/check-patient` (Nov 2026) → server reads real stored journal + real
  wearable rows, no client-supplied numbers. `[SESSION]`
- **Central clinical workflow:** Consultation → `GET /patients/{username}/overview` (composes ~11
  sections in one call) → AI assistance (proposed only) → Decision
  (`PUT /psychologists/notes/{id}/approve`) → Documentation (`ClinicalNote` with provenance) →
  Follow-up (`FollowupTask`). `[REPO]`
- **AI provenance chain (4 steps):** prompt version (e.g. `clinical_journal_summary/v1`) →
  provider + latency + ok log fields → model version + confidence + explanation → clinician
  approval (`approved_by`/`approved_at`). `[REPO]`

---

## 4. Three-tier AI pipeline `[REPO]`

| Tier | Provider | Notes |
|---|---|---|
| 1 | **Local Ollama**, custom `sentinel` model (`scripts/Modelfile`, "7.2B", ~8 GB RAM) | Zero data leaves clinic; serialized behind `threading.Lock` + 500 ms gap; 20 s timeout; cold ~15 s, 200–500 ms/journal |
| 2 | **Groq Cloud** `llama-3.1-8b-instant` | Opt-in only (`ALLOW_CLOUD_AI=false`); credentials via env vars; raw journal text could transit a third party — a documented privacy concern |
| 3 | **Deterministic keyword-frequency rule engine** | Always returns a structured assessment; truncate text to 200 chars as "summary"; ~50 ms; "errs on the side of including more information (truncation) rather than fabricating (hallucination)" |

Prompt mandates classifying any indication of suicidal ideation, self-harm, or imminent danger
as high risk regardless of context. Dual-mode output: warm companion-voice patient summary +
structured **OAP** clinical summary. Degradation is explicit: `AiSourceBadge` shows
"⚠ RULE-SCORED — MODEL OFFLINE". `[REPO]`

---

## 5. Deterministic engines (the safety core) `[REPO]`

**Discrepancy engine** (`app/api/discrepancy.py:_detect`) — rule-based, zero ML:
- Sentiment: 32 positive / 60 negative terms (55 single + 5 multi-word), negation detector
  (31 prefixes, 3-word window), 3 idiomatic intensifiers. Older `TECHNICAL_DESIGN.md` states
  18/22/26 with a 4-word window — a documented constant evolution. `[CONFLICT]`
- Biometric: high stress `BPM ≥ 110 AND HRV ≤ 25`; low stress `BPM ≤ 80 AND HRV ≥ 55`;
  moderate between.
- Truth table flags exactly 3 of 9 combinations: **positive+high, negative+low, neutral+high**.
  `negative+moderate` deliberately NOT flagged (an older benchmark's local copy had an extra
  rule — flaw F1). ~0.1 ms per profile.
- "**False positives are acceptable in a triage system. False negatives are not.**"

**Crisis engine** — three-stage deterministic state machine, thread-based countdown at **20×
time compression** (60 s → 3 s); Stage 2 trusted-contact SMTP email with signed ACK link at
30 sim-s, Stage 3 helpline at 60 sim-s; halt via 5 ms poll; per-patient `CrisisState` rows
(shipped `f75600b`). Keyword tiers 10/7/4, min score 5, auto-trigger `score ≥ 8`.
`trigger_cooldown_seconds = 3600`. `[REPO]`

---

## 6. Storage `[REPO]`

- **SQLite WAL** default (`sqlite:///./data/sentinel.db`), persistent named volume /
  bind mount; ~4 MB idle; atomic transactions, FK enforcement, B-tree indexes.
- **PostgreSQL 17** for multi-worker: `psycopg2-binary`, Alembic migrations
  (`a059d07dd9b6 → 4ff25c97017e → d0e1c7a9b2f3 → 9f3e2a1b7c4d`), idempotent cross-DB via
  SQLAlchemy `inspect`; verified against a real PG 17 cluster. Compose `scaled` profile pins
  `postgres:16-alpine`. `[CONFLICT — minor]`
- **Encryption at rest:** `EncryptedText` TypeDecorator (Fernet AES-128-CBC + HMAC-SHA256) on
  22 patient-identifiable fields across 11 model classes; key from PBKDF2-HMAC-SHA256 (600,000
  iterations, ≈173 ms) → HKDF-Expand under labels `sentinel-fernet-key-v1` /
  `sentinel-hmac-key-v1`; fail-closed (`EncryptionNotReadyError`) when required but no key.
  Physiological numerics / risk scores / 28 emotion floats remain plaintext **by design** so
  range queries work; DB-file-level encryption is a stated prerequisite before real pilot data.
- **Audit:** SHA-256 hash-chained `AuditLog` (`prev_hash`).
- **Backups:** `scripts/backup_db.py` — consistent snapshot → Fernet → optional S3 AWS4 PUT;
  `backup_wal()` copies `.db`/`-wal` on connection.
- **Event store** append/replay; **token blacklist** (DB-backed across workers).

---

## 7. Networking / deployment topologies `[REPO][SESSION]`

**A. Local dev (in use during work):** backend uvicorn `127.0.0.1:8000`, frontend Vite
`127.0.0.1:5173` with `/api` proxy. `[SESSION]`

**B. Original `docker-compose.yml`:** `sentinel-backend` (build `./backend`, expose 8000,
SQLite, `sentinel_data:/app/data`), `sentinel-frontend` (build `./frontend`, `5173:5173`);
`scaled` profile with Postgres + 4-worker backend + dedicated scheduler. Frontend had **no**
`PORT`/`BACKEND_URL` env vars — a real deployment blocker (nginx template needs both). `[REPO]`

**C. Render blueprint (`render.yaml`):** 2 web services + worker + Postgres; `PORT` default
10000; `BACKEND_URL` points at the public backend URL; health checks; free-tier cold starts
(45–60 s backend timeouts) observed — mitigated with UptimeRobot keep-warm and durable client
queue. `[REPO][SESSION]`

**D. Production single-VPS (`deploy/`, live 2026-11-16):** `[SESSION][REPO]`
```
Internet → Caddy (80/443, auto-HTTPS, Let's Encrypt)
   ├── /api/* , /health* , /v1/* , WebSocket upgrades → sentinel-backend:8000
   └── everything else                               → sentinel-frontend:10000 (nginx)
backend: PORT=8000, SQLite bind mount ./data:/app/data, uid 1001
frontend: PORT=10000, BACKEND_URL=http://sentinel-backend:8000/api
internal Docker bridge network; only Caddy publishes ports
```
Host: Ubuntu 24.04.5 LTS, Docker Compose v5.7.1, 3.8 GiB RAM / 46 GiB free, key-only SSH,
managed firewall (Accept TCP 22/80/443 + default drop). `deploy/bootstrap.sh` installs Docker
if missing, generates a one-time `JWT_SECRET`, seeds the verified DB, `up -d --build`.
Production env: `ENCRYPTION_REQUIRED=false` (pilot uses plaintext journals), `RUN_WORKERS=false`,
`RATE_LIMIT_BACKEND=memory`, `WS_PUBSUB=off`, `COOKIE_SECURE=true`, CORS/ack-link → real domain.

---

## 8. Multi-worker scaling (implemented) `[REPO]`

- Shared rate limiting via `rate_limit_counters` fixed-window upsert (`RATE_LIMIT_BACKEND=db`).
- Exactly one scheduler via PostgreSQL advisory lock (`SCHEDULER_LOCK_KEY=749493`, 10 s
  heartbeat), failover verified by killing leader.
- Cross-worker WebSocket fan-out **without Redis** via PG `LISTEN/NOTIFY` channel
  `sentinel_ws` (`WS_PUBSUB=auto|pg|off`); SQLite stays local single-process.
- DB-backed JWT blacklist; API processes `RUN_WORKERS=false`; `docker compose --profile scaled
  up -d`.

---

## 9. Security architecture `[REPO]`

Argon2id passwords (time_cost 3, memory 65536, parallelism 4) with transparent legacy-bcrypt
re-hash; HS256 JWT 8 h (no refresh tokens — OPEN); HttpOnly `access_token` cookie
(`samesite=lax`, `max_age=28800`) + `sessionStorage` fallback; 5-failure/15-min lockout;
`_owns_or_psych()` IDOR guard; `hmac.compare_digest()`; DOMPurify (`ALLOWED_TAGS=[]`);
`RateLimiterMiddleware` 100 req/min/IP; internal Docker network; global exception handlers
(sanitized 500s); CSP/HSTS/nosniff; non-root `USER sentinel` (UID/GID 1001); per-device ring
tokens SHA-256 hashed at rest, constant-time compare, revocable; HMAC-signed trustee links.

---

## 10. Proposed / abandoned architectures (separated)

- **Secure Transport Layer (STL / `transport.md`)** — E2EE + PFS, clinic pull + ACK,
  dead-letter, zero-metadata routing. **Design only; never implemented.** `concerns.md` #35/#36;
  Transport readiness 2/10. `[REPO][UNVERIFIED]`
- **JSON file storage** — original Streamlit prototype; rejected for atomicity/concurrency/
  indexing. `[REPO][HISTORICAL]`
- **Streamlit monolith** — superseded; archived under `archive/`. `[REPO][HISTORICAL]`
- **Redis / Celery for crisis scheduling** — rejected. `[REPO]`
- **Next.js / Web Components / Redux / Context / Zustand** — rejected (see `07`). `[REPO]`
- **Custom ring hardware (PCB)** — abandoned Feb 2026; see `08`. `[REPO]`
- **Cloudflare Tunnel laptop-as-server interim pilot** — `docs/hosting-plan.md` §0; "This
  proves the product; it is not the production deployment." `[REPO]`
- **AWS India Lightsail + CloudFront** — analysed as "most defensible global + UPI" but **not
  adopted**; the founder rejected AWS. `[SESSION][HISTORICAL]`

---

## 11. Confidence / gaps `[UNKNOWN]`

- Full enumerated architecture constitution text is referenced but not present in accessible
  docs. `[UNKNOWN]`
- The exact number of API routes is given as "≈120 valid routes across 29 API router modules"
  in the paper; the code tree lists 29 `backend/app/api/*.py` modules (including `__init__.py`).
  `[INFERRED]`
- Whether the final live VPS region is Malaysia/Indonesia (recommended for India + NZ audience)
  or Boston (shown in the panel earlier) is not recorded. `[UNKNOWN][CONFLICT]`
