# Sentinel — On-Premises Psychophysiological Triage Node

**Continuous, clinician-in-the-loop mental health infrastructure: journal monitoring plus wearable physiology, AI-assisted summaries, crisis escalation, and structured follow-up — built for clinics that are short on psychiatrists.**

> **Stack:** FastAPI + SQLAlchemy (SQLite/PostgreSQL) · React 19 + TypeScript + Vite · local-first AI (Ollama) with hosted fallback · PWA · Docker Compose · GitHub Actions CI
> **Status:** Working prototype · 222 tests (~72s) across 6 CI jobs · Hardware adapters built (BLE-GATT, vendor cloud, deterministic simulator) · 30-subject pilot planned (September 2026)

> **Live demo:** https://sentinel-frontend-dhkcs.onrender.com · API docs: https://sentinel-backend-dhkcs.onrender.com/docs
> **Origin:** this is the current, actively developed codebase. The original milestone prototype lives at `dhansikarcs-cs/Sentinel_V_1_` (hardware M0 ring SDK, original README/docs).

---

## What Sentinel Does

- **Continuous biometric ingestion** from smart rings (HR, HRV, stress, sleep) via a pluggable adapter SDK (`BLE` gateway, vendor cloud, or deterministic simulator)
- **Journal analysis** with AI summaries — a warm companion tone for the patient, a structured OAP clinical summary for the psychologist
- **Discrepancy engine** — rule-based, zero-ML, flags mismatches between subjective journal text and objective physiology (e.g. "I'm fine" alongside sustained high stress)
- **Crisis engine** — deterministic escalation (patient → psychologist → trusted contact → helpline) that always waits for a human to decide, with an active-crisis WebSocket broadcast
- **Clinical workspace** — triage, clinical notes, bookings, follow-ups, session reports, export center
- **Security** — HttpOnly JWT + per-device ring tokens (SHA-256 at rest, constant-time compare), field-level encryption (Fernet, PBKDF2-600k + HKDF), hash-chained audit log, rate limiting

---

## The AI: honest and local by design

The AI layer is honest about where it is today. Our own model is still in training, so the live build runs on a hosted model with our prompt, guardrails, and safety rules wrapped around every output — always paraphrased, never quoting raw text or raw biometrics. The design stays local-first: the moment our tuned model is ready, it drops onto the clinic's own hardware and patient data never leaves the building.

Beside it, a **28-class emotion classifier** (trained in-repo on 48,836 GoEmotions examples under a leak-free split) is already fully ours and runs on-premises. Every entry gets two views: a warm, motivating message for the patient and a structured OAP clinical summary for the psychologist.

**Fallback chain:** hosted model → local model → deterministic rule fallback keeps the system alive when AI is unavailable. The discrepancy and crisis decisions never depend on the LLM.

---

## Architecture

```
OEM ring ─┬─ BLE gateway (bleak) ──┐
          ├─ vendor cloud SDK ─────┤→ RingSource adapters → SensorData → POST /ring/data
          └─ simulated (dev/test)  ┘                                    │
                                                    get_ring_identity (device token)
                                                                        ↓
Frontend (PWA) ── Nginx ── FastAPI API ── SQLite/PostgreSQL
                       │        └─ AI: hosted (today) → Ollama (local) → rule fallback
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
│   │   ├── services/                  # audit, websocket, search, plain insights
│   │   │   └── ring/                  # RingSource SDK: base, simulated, ble_gatt, vendor_api
│   │   ├── ml/                        # emotion_classifier, risk_engine, model_registry
│   │   ├── events/                    # Event subscribers (audit trail, event store)
│   │   ├── workers/                   # AI worker, reminder/celebration schedulers
│   │   └── repositories/              # Data-access layer
│   ├── benchmarks/                    # IRIS-style benchmark suite
│   ├── alembic/                       # DB migrations
│   ├── tests/                         # 222 tests across 6 CI jobs
│   └── requirements*.txt
├── frontend/                          # React 19 + TypeScript + Vite + Tailwind (PWA)
│   └── src/{api,components,lib,pages,stores}
├── scripts/                           # ring_bridge, sim_ring, test_ring_api, seeding, ML training
├── docs/                              # Design, decisions, judge Q&A, hardware roadmap, codebook
├── docker-compose.yml
└── README.md
```

---

## Hardware Ingestion

| Component | What it does |
|-----------|--------------|
| `POST /ring/pair` | Binds a device serial to the patient, issues a one-time device token |
| `POST /ring/unpair` | Revokes a device; re-pairing issues a fresh token |
| `POST /ring/data` | Authenticated push (device token or patient JWT) → canonical `SensorData` |
| `GET /ring/devices` | Device state for patient or psychologist |
| `RingSource` SDK | `SimulatedRing` (deterministic per-user/hour), `VendorAPIRingSource` (cloud SDK), `BLEGATTRingSource` (bleak, HRM 0x2A37 + battery 0x180F) |
| `scripts/ring_bridge.py` | Polls any adapter and pushes through the authenticated path |
| `scripts/sim_ring.py` | Streams simulated device-token data (`--once` for a single push) |

Tokens are stored as SHA-256 hashes, compared with `hmac.compare_digest`, and honored per-request. See `docs/ROADMAP_HARDWARE.md` for the hardware roadmap.

---

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-bridge.txt   # only needed for the BLE ring bridge
```

Set encryption **once** — never change it afterwards or existing data cannot be decrypted:

```
ENCRYPTION_PASSPHRASE=your_long_passphrase
ENCRYPTION_SALT=<fixed hex salt, e.g. from: python -c "import secrets; print(secrets.token_hex(16))">
```

```bash
python seed_clinic.py                  # seed admin + 30 client clinic demo
uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full stack (Docker)

```bash
docker compose up --build
```

---

## Testing

```bash
python scripts/test_ring_api.py        # ring SDK/API tests (incl. BLE parsers)
cd backend && python -m pytest         # full backend suite (222 tests, ~72s)
```

---

## Accounts (clinic seed — `python seed_clinic.py`)

| Role | Username | Password | Notes |
|------|----------|----------|-------|
| Admin | `admin` | `password123` | Clinic oversight console (directory, audit log, crises) |
| Psychologist | `cel` | `1234` | 14 teen clients |
| Psychologist | `marcus` | `4321` | 16 teen clients |
| Teen client | `maya_k` | `sentinel123` | Sample client (all 30 clients use `sentinel123`) |

30 teen clients with 12 months of journals, moods, ring vitals, clinical notes and crisis history. Re-seed anytime with `python seed_clinic.py` (also clears any login lockouts).

---

## Data Privacy & Security

- Journal raw content encrypted at rest (Fernet, key derived via PBKDF2-600k + HKDF)
- Ring tokens hashed at rest, constant-time comparison, per-request revocation
- HttpOnly cookie JWT + ring device tokens; ALWAYS set `ENCRYPTION_PASSPHRASE` and `ENCRYPTION_SALT` to stable values
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
| `docs/ROADMAP_HARDWARE.md` | Hardware roadmap |
| `docs/sentinel_paper.md` / `.pdf` | Research paper (markdown source + PDF build via `scripts/generate_paper_pdf.py`) |
| `SENTINEL_CODEBOOK.md` | Per-file code explanation (original prototype) |

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.