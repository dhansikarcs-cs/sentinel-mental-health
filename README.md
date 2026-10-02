# Sentinel — On-Premises Psychophysiological Triage Node

**Continuous mental health infrastructure connecting patients and clinicians through real-time monitoring, AI-powered journal analysis, crisis escalation, and structured follow-up management.**

> **Stack:** FastAPI + SQLAlchemy (SQLite/PostgreSQL) · React 19 + TypeScript + Vite · Ollama/Groq AI · PWA · Docker Compose · Nginx
> **Status:** Hardware M0 complete (ring SDK + device binding) · Emergent Ventures funded · OEM ring (Jport) in procurement

---

## What Sentinel Does

- **Continuous biometric ingestion** from smart rings (HR, HRV, stress) via a pluggable adapter SDK (`BLE` gateway, vendor cloud, or deterministic simulator)
- **Journal analysis** with AI summaries — a warm companion tone for the patient, a structured OAP clinical summary for the psychologist
- **Discrepancy engine** — rule-based, zero-ML classifier flagging mismatches between subjective journal text and objective physiology
- **Crisis engine** — deterministic escalation (patient → psychologist → trusted contact → helpline) with an active-crisis WebSocket broadcast
- **Clinical workspace** — triage, clinical notes, bookings, follow-up grading, export center
- **Security** — HttpOnly JWT + per-device ring tokens (SHA-256 at rest, constant-time compare), field-level encryption (Fernet), hash-chained audit log, rate limiting

---

## Architecture

```
OEM ring ─┬─ BLE gateway (bleak) ─┐
          ├─ vendor cloud SDK ────┤→ RingSource adapters → SensorData → POST /ring/data
          └─ simulated (dev/test) ┘                                    │
                                                     get_ring_identity (device token)
                                                                      ↓
Frontend (PWA) ── Nginx ── FastAPI API ── SQLite/PostgreSQL
                       │        └─ Ollama (local) → Groq (cloud) → rule fallback
                       └─ WebSocket (crisis broadcast)
```

```
sentinel3/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point, middleware, routers
│   │   ├── api/                       # Routers: auth, journal, crisis, ring, triage, ...
│   │   ├── core/                      # Config, DB, security, rate limiting, dependencies
│   │   ├── models/                    # SQLAlchemy models (users, journal, ring_device, ...)
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── services/                  # audit, websocket, search
│   │   │   └── ring/                  # RingSource SDK: base, simulated, ble_gatt, vendor_api
│   │   ├── ml/                        # emotion_classifier, risk_engine, model_registry
│   │   ├── events/                    # Event subscribers (audit trail, event store)
│   │   ├── workers/                   # AI background worker
│   │   └── repositories/              # Data-access layer
│   ├── benchmarks/                    # IRIS-style benchmark suite
│   ├── alembic/                       # DB migrations
│   └── requirements*.txt
├── frontend/                          # React 19 + TypeScript + Vite + Tailwind (PWA)
│   └── src/{api,components,lib,pages,stores}
├── scripts/                           # ring_bridge, sim_ring, test_ring_api, seeding, ML training
├── docs/                              # Design, decisions, judge Q&A, hardware roadmap
├── docker-compose.yml
└── README.md
```

---

## Hardware Ingestion (M0)

| Component | What it does |
|-----------|--------------|
| `POST /ring/pair` | Binds a device serial to the patient, issues a one-time device token |
| `POST /ring/unpair` | Revokes a device; re-pairing issues a fresh token |
| `POST /ring/data` | Authenticated push (device token or patient JWT) → canonical `SensorData` |
| `GET /ring/devices` | Device state for patient or psychologist |
| `RingSource` SDK | `SimulatedRing` (deterministic per-user/hour), `VendorAPIRingSource` (cloud SDK), `BLEGATTRingSource` (bleak, HRM 0x2A37 + battery 0x180F) |
| `scripts/ring_bridge.py` | Polls any adapter and pushes through the authenticated path |
| `scripts/sim_ring.py` | Streams simulated device-token data (`--once` for a single push) |

Tokens are stored as SHA-256 hashes, compared with `hmac.compare_digest`, and honored per-request. See `docs/ROADMAP_HARDWARE.md` for the M1–M3 plan.

---

## Quick Start — Run It Locally

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.11** (3.10–3.12 ok — avoid 3.13+) | ML deps (scikit-learn/numpy) are pinned & tested on 3.11 |
| Node.js | 18+ (20 recommended) | frontend build + dev server |
| npm | ships with Node | |

### 0. One-time setup

```bash
# 1) Backend virtualenv (make sure it's Python 3.11!)
cd backend
python3.11 -m venv venv          # Windows: python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
# pip install -r requirements-bridge.txt   # only needed for the BLE ring bridge
# ⚠️ If your project lives in a cloud-synced folder (iCloud Drive/Downloads,
# OneDrive), prefer a venv OUTSIDE it:  python3.11 -m venv --copies ~/.venvs/sentinel

# 2) Backend env file — backend/.env (dev values are fine locally; see .env.example at repo root)
cat > .env <<'EOF'
JWT_SECRET=dev-local-put-any-long-random-string-here
ENCRYPTION_PASSPHRASE=dev-local-passphrase
ENCRYPTION_SALT=9d38a7c1e5b204f6a1d3c8e7b9f20a54
ENCRYPTION_REQUIRED=true
DATABASE_URL=sqlite:///./data/sentinel.db
DEBUG=true
EOF

# 3) Frontend dependencies
cd ../frontend
npm install
```

> The app **refuses to boot** with the default JWT secret (unless `DEBUG=true`) —
> the `.env` above satisfies both. `.env` is git-ignored; never commit real secrets.

### 1. Seed demo data (once)

```bash
cd backend
python seed_clinic.py      # 30 teen clients, 12 months of history
                           # ⚠️ WIPES existing local data (also clears login lockouts)
# or: python seed_demo.py  # smaller demo dataset
```

### 2. Run the app

**Option A — one URL (simplest).** Build the frontend once; the backend serves it
as an SPA, so there is only one process and one port:

```bash
cd frontend && npm run build      # emits frontend/dist — only needed after frontend changes
cd ../backend
python -m uvicorn app.main:app --reload --port 8000
```

→ open **http://localhost:8000** · health check: **http://localhost:8000/health**

**Option B — hot-reload dev mode (two terminals).** Vite gives instant frontend
refresh and proxies `/api` calls to the backend:

```bash
# terminal 1 — API
cd backend && python -m uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend dev server
cd frontend && npm run dev        # open http://localhost:5173
```

**Port 8000 already taken by another project?** Run the backend elsewhere and point
the Vite proxy at it:

```bash
python -m uvicorn app.main:app --reload --port 8001       # terminal 1
VITE_API_TARGET=http://localhost:8001 npm run dev         # terminal 2
```

### 3. Log in

`admin / password123` · psychologists `cel / 1234`, `marcus / 4321` · clients `maya_k / sentinel123`
(full table below).

### Local troubleshooting

| Symptom | Fix |
|---------|-----|
| `Refusing to start: JWT_SECRET is still the default` | Create `backend/.env` (step 0) or set `DEBUG=true` |
| `Address already in use` on port 8000 | Another app owns the port — use `--port 8001` (+ `VITE_API_TARGET` in Option B) or free it: `lsof -ti :8000 \| xargs kill` |
| `ModuleNotFoundError: sklearn` or wheel build errors | Wrong Python version — recreate the venv with `python3.11` |
| Login says account is locked | Re-run `python seed_clinic.py` (clears lockouts; wipes local data) |
| AI summaries say "unavailable" | Normal without Ollama/Groq/Azure keys — rule-based fallback is used |

### Full stack (Docker)

```bash
docker compose up --build
```

---

## Testing

```bash
python scripts/test_ring_api.py    # 9 ring SDK/API tests (incl. BLE parsers)
cd backend && python -m pytest     # backend test suite
```

---

## Accounts (clinic seed — `python seed_clinic.py`)

| Role | Username | Password | Notes |
|------|----------|----------|-------|
| Admin | `admin` | `password123` | Clinic oversight console (directory, audit log, crises) |
| Psychologist | `cel` | `1234` | Dr. Celeste Raine — 10 teen clients |
| Psychologist | `marcus` | `4321` | Dr. Marcus Vale — 10 teen clients |
| Teen client | `maya_k` | `sentinel123` | Sample client (all 30 clients use `sentinel123`) |

30 teen clients with 12 months of journals, moods, ring vitals, clinical notes and crisis history.
Re-seed anytime with `python seed_clinic.py` (also clears any login lockouts).

---

## Data Privacy & Security

- Journal raw content encrypted at rest (Fernet, key derived via PBKDF2 600K + HKDF)
- Ring tokens hashed at rest, constant-time comparison, per-request revocation
- HttpOnly cookie JWT (8h) + localStorage fallback for programmatic clients
- Hash-chained audit log; rate limiting (100 req/min/IP); internal Docker network; sanitized 500s
- `.env` holds secrets — excluded from version control

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/TECHNICAL_DESIGN.md` | Full architecture, decisions, trade-offs |
| `docs/ENGINEERING_DECISIONS.md` | Every key decision and alternative |
| `docs/ENGINEERING_LOGBOOK.md` | Build narrative with timestamps |
| `docs/JUDGE_QA.md` | Anticipated judge questions + defensible answers |
| `docs/ROADMAP_HARDWARE.md` | Hardware milestones M1–M3 |
| `docs/sentinel_paper.md` / `.pdf` | Research paper (markdown source + PDF build via `scripts/generate_paper_pdf.py`) |
| `SENTINEL_CODEBOOK.md` | Per-file code explanation |

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.
