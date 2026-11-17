# 05 — TECHNICAL IMPLEMENTATION

*Every available technical detail. Implemented / experimental / proposed / abandoned are
separated. Nothing unverified is called working. Provenance labels per `00`.*

---

## 1. Stack and versions `[REPO]`

| Component | Version |
|---|---|
| Python | 3.11 (pinned in Dockerfile 2026-08-26; paper says 3.11, one design doc says 3.12-slim — `[CONFLICT]`) |
| FastAPI | 0.109 (requirements `>=0.115.0`) |
| Starlette | `>=1.3.1` |
| SQLAlchemy | 2.0 |
| Pydantic / pydantic-settings | 2.x |
| Uvicorn | `>=0.32.0` |
| React | 19 |
| TypeScript | 5.4 (`tsc -b` used in CI) |
| Vite | 6 |
| Docker Compose | 2.24 (dev) / v5.7.1 (live VPS) |
| Nginx | 1.25 |
| TailwindCSS | v4 |
| bleak | ~0.22 (bridge-only) / 3.1.0 (hardware lab) |
| argon2-cffi, bcrypt<4.2, cryptography>=49, python-jose, scikit-learn, joblib, numpy, requests, psycopg2-binary, alembic, python-multipart | per `backend/requirements.txt` |

Stats (logbook): ~25,000 lines; 222 backend pytest tests; 23-case golden set; 6-job CI;
54 benchmarks (52 pass). `[REPO]`

---

## 2. Backend structure `[REPO]`

`backend/app/`:
- **`main.py`** — FastAPI app, lifespan (encryption init if passphrase, `_init_db()`, event
  subscribers, WS pubsub, reminder/celebration tasks gated by `run_workers`), middleware stack
  (`RequestIDMiddleware`, `APIGatewayMiddleware`, `SecurityHeadersMiddleware`,
  `RateLimiterMiddleware`, `CORSMiddleware`), `v1_router = APIRouter(prefix="/api")` including 29
  routers, global exception handlers, `/health`, `/health/live`, `/health/ready`,
  `/api/ai/health`, and a SPA catch-all that serves `frontend/dist` when present.
- **`core/`** (34 modules): `config.py` (pydantic-settings, env_file `../.env`),
  `database.py`, `security.py` (Argon2id, Fernet, PBKDF2 600K + HKDF, trustee HMAC links),
  `encrypted_fields.py` (`EncryptedText` TypeDecorator), `dependencies.py`
  (`get_current_user`, `require_role`, `RingIdentity`, `get_ring_identity`),
  `rbac.py` (`owns_or_psych`), `api_gateway.py`, `api_response.py` (`ok()` wrapper →
  `{success,message,data}`), `request_id.py`, `structured_errors.py`, `security_headers.py`,
  `rate_limiter.py` / `rate_limit_store.py` / `login_rate_limiter.py`, `token_blacklist.py`,
  `pagination.py`, `idempotency.py`, `input_validator.py`, `password_validator.py` (Policy:
  min 6, max 128, 1 upper, 1 lower, 1 digit, 1 special, common-password blocklist),
  `health.py`, `logging_config.py`, `dates.py`, `location.py` (`user_timezone`),
  `device_tracker.py`, `feature_flags.py`, `leader.py`, `ws_pubsub.py` (actually in services).
- **`api/`** (29 modules): activity, agents, ai_analyses, auth, bookings, crisis, discrepancy,
  emotions, emotion_results, event_store_api, export_data, feature_flags_api, followups, journal,
  ml_registry, mood, notifications, patients, physio, psychologists, psych_journal, ring,
  risk_assessments, search_api, sensor_readings, sync_api, timeline, triage, ws.
- **`models/`** (21): ai_analysis, audit, booking, clinical_note, crisis, emotion_result,
  event_store, followup, journal, mood, notification, physiological_signal, psych_journal,
  rate_limit_counter, revoked_token, ring, ring_device, risk_assessment, sensor_reading, triage,
  user (`patient_profiles` table).
- **`schemas/`** (17 pydantic models, all optional physiological fields with range validators).
- **`repositories/`** (5): base, booking, followup, journal, patient.
- **`services/`** (13): ai_service, audit, event_store_service, notification, notify,
  patient_context, plain_insights, search_service, timeline_service, websocket_manager,
  ws_pubsub, physio, ring (base/ble_gatt/vendor_api).
- **`ml/`**: crisis_policy, emotion_classifier, model_registry, risk_engine, train_goemotions.
- **`events/subscribers/`**: audit, event_store.
- **`workers/`**: ai_worker, reminder_worker, celebrations_worker, runner.
- **`alembic/`**: migration chain `a059d07dd9b6 → 4ff25c97017e → d0e1c7a9b2f3 →
  9f3e2a1b7c4d`.

---

## 3. Frontend structure `[REPO][SESSION]`

`frontend/src/` — `App.tsx` (routes + `RequireAuth` + `RequireRole`), `main.tsx` (SW register,
ring-queue flush on boot/online), `constants.ts`, `index.css` (~30 CSS custom properties,
light/dark palettes), `ErrorBoundary.tsx`, `hooks/useTheme.ts`, `stores/auth.ts` (pub/sub,
`sessionStorage`), `api/client.ts` (BASE `/api`, token handling, cold-start retry for
GET/login, all API methods), `api/outbox.ts` (offline outbox).

**Pages** (29): ActivityFeed, Bookings, ClinicalNotes, Consultation, Crisis, Dashboard, Export,
Followups, Journal, Login, Mood, Onboarding, PatientInsights, Profile, PsychJournal,
PsychOnboarding, PsychTriage, Register, Timeline, TrusteePortal, **Wearables** (Nov 2026).

**Components** (13): AiSourceBadge, EmotionBar, Layout (sidebar with system status, daily ops,
high-risk, AI insights, notifications, wearable ring section), MoodPicker, OnboardingTour,
PatientSelector, PrioritiesPanel, RingConnect, RingConnectButton, RingVitalsCard, TourGuide.

**`ring/`** (Nov 2026): `ycbt.ts` (frame/CRC/parse/UUIDs/GET_TAGS/extractRecords),
`webBluetooth.ts` (connectAndSync, picker filters, handshake, history pull, terminal ACK,
paired stop in `finally`), `syncRing.ts` (shared connect→enqueue→flush path + error wording),
`ringQueue.ts` (IndexedDB durable queue `sentinel-ring-queue`, deterministic `seq`, backoff).

**PWA:** `public/manifest.webmanifest` (`display: standalone`), `public/sw.js`
(network-first API cache, stale-while-revalidate assets, offline shell, `SKIP_WAITING` message),
icons, `index.html` pre-paint theme script.

---

## 4. APIs (selected, with contracts) `[REPO][SESSION]`

- **Auth:** `POST /api/auth/register` (password policy enforced), `/login`, `/refresh`,
  `/logout`, `/unlock`. `RegisterRequest` requires username (3–50, `^[a-zA-Z0-9_]+$`),
  password (6–128), name, dob (10 chars), occupation; role `patient|psychologist`;
  professional codes `PSY-0001..0005` → clinic codes `SENTINEL-01..05`.
- **Ring:** `POST /api/ring/pair` (one-time device token, SHA-256 hashed), `/unpair`,
  `GET /ring/devices`, `POST /ring/data` (idempotent on `(device_id, seq)`; only measured
  fields; ranges bpm 30–250, stress 0–100, sleep 0–24, spo2 50–100, hrv 0–300),
  `GET /ring/data`. `get_ring_identity`: `X-Device-Serial` + `X-Device-Token` (constant-time)
  OR patient JWT fallback.
- **Sensor readings:** `POST /api/sensor-readings`, `GET /api/sensor-readings`,
  `GET /api/sensor-readings/{username}` (psych only).
- **Patients:** `GET /api/patients/me`, `/me/wellness` (latest genuinely measured value PER
  signal across last 50 rows + `last_synced`, `sync_due`, `reading_count`),
  `/{username}/profile`, `/summary`, `/overview`, `/plain-insights`, `/{username}/vitals`
  (Nov 2026; self or assigned psychologist), `/me/consent`, `/{username}/assign-psych`.
- **Discrepancy:** `POST /api/discrepancy/check` (client supplies text+bpm+hrv),
  `POST /api/discrepancy/check-patient` (Nov 2026; server reads real DB rows; RBAC patient self
  or assigned psych; `insufficient_data` when missing; mismatch → `discrepancy_alert` WS +
  HIGH-severity audit).
- **Agents:** `/triage-summary`, `/suggest-slots`, `/draft-followup`, `/journal-to-note`,
  `/pre-session-brief`, `/compliance-radar`, `/silent-period-watch`, `/relapse-indicators`,
  `/cross-patient-patterns`, `/ring-vitals-risk` (psych; defaults latest among assigned
  patients), `/crisis-debrief`.
- **Crisis:** `/state`, `/log`, `/assess-risk`, `/acknowledge`, `/trigger`, `/resolve`,
  public trustee endpoints with HMAC links.
- **Others:** journal, mood, timeline, bookings, followups, notifications, activity,
  psych-journal, clinical notes, export, event store, sync (offline), search, feature flags,
  ml registry, risk assessments, ai analyses, emotion results, WebSocket `/api/ws/psych`,
  `/api/ws/admin`.

**Note:** comparison endpoints `/compliance-radar`, `/silent-period-watch`,
`/relapse-indicators`, `/cross-patient-patterns`, `/agents/*` are **POST**; `/api/emotions/
timeline/{u}` is psych/admin-only; `/api/patients/me/wellness` is the correct path (not
`/api/wellness`). `[SESSION][REPO]`

---

## 5. AI / ML `[REPO]`

- **Emotion classifier:** TF-IDF (10,000 features, ngram 1–3, sublinear) + OneVsRest
  LogisticRegression (C=2.0, `class_weight=balanced`); 28 simplified GoEmotions labels;
  trained on official train+validation **48,836**; official test **5,427**; leak-free
  (audit F5); artifact `emotion_model.pkl` MD5 `9a8d157c6e42706c43b354df6d1025fc`;
  micro-F1 **0.4642**, macro-F1 **0.4047**, samples-F1 **0.4947**; ~10 s CPU training; 2.5 MB.
- **Risk engine:** keyword tiers (crisis 10 / high 7 / moderate 4), emotion blend, score 1–10,
  history escalation requires ≥3 recent texts; `assess_risk_with_explainability()`.
- **Crisis policy:** data-driven frozen `CRISIS_POLICY`, `auto_trigger_threshold` 8, cooldown
  3600 s, thresholds 8/7/6/4 mirrored in plain-insights wording.
- **Model registry:** `model_registry.json` with register/activate and `trained_at` preservation
  (bug fixed: import used to mutate it).
- **Prompt versioning:** `NOTE_SYNTHESIS_PROMPT_V1/V2`, `RING_VITALS_RISK_PROMPT_V1`,
  `clinical_journal_summary/v1`; `prompt_version` persisted on `AIAnalysis`; golden-set gate
  `scripts/eval_golden_set.py --strict` (16 risk + 7 emotion cases).
- **Dual-mode summarization:** companion voice (patient) vs structured OAP (clinician); regex
  JSON extraction; echo guard (`_is_raw_echo()` >85% word overlap); rule truncation fallback.

---

## 6. Authentication / security / privacy `[REPO]`

Argon2id (time_cost 3, memory 65536 KiB, parallelism 4) with bcrypt verify fallback and
transparent re-hash; HS256 JWT 8 h, payload `{sub, role}`, HttpOnly cookie + `sessionStorage`;
5-failure/15-min lockout; `require_role`; `_owns_or_psych()`; `hmac.compare_digest`;
DOMPurify; 100 req/min/IP; internal Docker network; CSP/HSTS/nosniff; non-root UID 1001;
Fernet field encryption (22 fields / 11 model classes) with PBKDF2 600K + HKDF, fail-closed
read; SHA-256 hash-chained audit; device token hashing; HMAC trustee links; sanitized errors;
`ALLOW_CLOUD_AI=false` opt-in boundary; DB-file-level encryption required before real pilot
data.

**Known open security items:** no refresh tokens; no MFA/session revocation (red team #18);
`SECURITY_AUDIT.md` (2026-09-04) flagged live credentials in `.env` for rotation and weak demo
passwords; no SBOM/supply-chain control; no MFA. `[REPO]`

---

## 7. Hardware / BLE integration `[REPO][SESSION]`

- **Native path (verified):** Windows Python 3.11.9 + bleak 3.1.0/WinRT → YCBT over GATT
  `be940000-7333-be46-b7ae-689e71722bd5`, cmd `be940001`, stream `be940003`; CRC16/CCITT-FALSE
  frames; `hardware_lab/` scripts (30) + `out/` evidence (39 files). See `08`.
- **Browser path (implemented, not hardware-verified):** Web Bluetooth `requestDevice` with
  filters `namePrefix 'R30 PRO'`, `'F085'`, `services ['heart_rate']`; `optionalServices`
  `[YCBT_SERVICE]`; handshake with vendor Get tags; history `05 06` / `05 09`; mandatory
  `05 80 {00}` ACK; paired stops in `finally`; requires HTTPS + user gesture + Chrome/Edge;
  cannot run in background (browser limit). `[SESSION]`
- **Abandoned:** `SimulatedRing` (deleted Nov 2026), `mockHistory`, hardcoded defaults,
  derived `sdnn`, vendor-cloud passthrough for the pilot. `[SESSION]`
- **Forbidden writes:** Nordic Secure DFU `0xFE59`, reset, OTA, history deletes `05 40..05 4E`,
  unknown/guessed opcodes. `[REPO]`

---

## 8. Testing `[REPO][SESSION]`

24 backend test modules (auth_flow, celebrations, crisis_emails, crisis_policy, crisis_security,
discrepancy_engine, export_data, followups, journal_api, model_registry, notification_flows,
offline_sync, overview_priorities, password_hardening, physio, plain_insights, regression_fixes,
ring_dedupe, ring_sensor, risk_engine, scale_runtime, scaling, security_hardening, sync_events).
`conftest.py` in-process harness (isolated SQLite, disabled rate limiter/Ollama/Groq/WS
broadcast, seeded fixtures). **222 passed** (latest, ~72–85 s, 33 warnings), ruff check +
format, `tsc -b`, `vite build`, golden `--strict`, 6-job GitHub Actions CI.

Repeatable gates (working sessions): `python -m ruff check backend/`, `python -m ruff format
--check backend/`, `python -m pytest backend/tests -q`, `tsc -b --pretty false` and
`npm run build` **run from `frontend/`** (running from repo root gives `TS5083` / npm ENOENT).
`[SESSION]`

---

## 9. Deployment / dependencies / infrastructure / performance / scalability `[REPO][SESSION]`

- `docker-compose.yml` (dev + `scaled` profile), `render.yaml` (Render blueprint),
  `deploy/docker-compose.prod.yml`, `deploy/Caddyfile`, `deploy/bootstrap.sh`,
  `deploy/.env.example`, `deploy/DEPLOY.md`. Full runbook preserved in `deploy/DEPLOY.md`.
- Live: `https://sentinelpsytech.com`, Hostinger KVM 1 VPS, Ubuntu 24.04.5 LTS, key-only SSH,
  managed firewall, Caddy TLS, 3 containers, SQLite bind mount.
- Performance numbers recorded: discrepancy <0.1 ms; crisis concurrency 101–109 ms 1–25 loads
  0 drops; PBKDF2 600K 154.8–233.2 ms (NIST 100–300 ms band); Fernet <2 ms; JWT ~0.5 ms;
  Ollama 5,076 ms cold / 1,449–1,746 ms warm; REST 7–41 ms; login 397.5 ms; full AI triage
  4,711.6 ms; storage 23–181 ms at 10–500 profiles; 100 concurrent writes in 62.6 ms zero
  errors. `[REPO][CONFLICT — several runs/differing numbers preserved]`
- Scalability: PG 17 verified for multi-worker; advisory-lock scheduler failover; LISTEN/NOTIFY
  fan-out; SQLite single-writer limitation documented.

---

## 10. Experimental vs proposed vs abandoned (explicit separation)

| Status | Items |
|---|---|
| **Implemented & verified** | FastAPI/React stack, rule engines, 3-tier AI, Fernet/Argon2id, hash-chained audit, PWA, ring SDK M0, Web Bluetooth UI path, discrepancy `/check-patient`, `/{username}/vitals`, live VPS deployment, 222 tests, golden gate, real BLE lab ingestion |
| **Implemented, NOT hardware-verified** | Browser Web Bluetooth connect (built, type-checked, bundle-verified, but no recorded successful live BLE handshake from a hosted browser) `[SESSION]` |
| **Experimental / non-production** | Entire `hardware_lab/` (EXPERIMENTAL label, "not clinically validated"), raw ECG ADC waveform, BP candidate decoding |
| **Proposed only** | Secure Transport Layer (STL); dataset acquisition programme; calibration-then-select; cycle-/sleep-aware baselines; companion mobile app; per-patient baselines; IRB 30-subject pilot |
| **Abandoned** | Custom PCB/3D casing hardware; Streamlit monolith; simulated ring & fake vitals; dark sage theme; Redis/Celery; AWS Lightsail hosting plan; "assigned patient → psych vitals" framing (reframed to psych's own ring) |

---

## 11. Confidence / gaps `[UNKNOWN]`

- Exact live VPS region not recorded. `[UNKNOWN]`
- `Sentinel_V_1_/` sibling checkout contains Azure deployment files (`Dockerfile.azure`,
  `azure-startup.sh`, `build-azure-deploy.sh`, `docs/DEPLOY_AZURE.md`) not present in
  `sentinel3`; whether Azure was ever used is not recorded. `[UNKNOWN][INFERRED]`
- The `GPU & LLM`, `API`, `AI Router` items seen in the Hostinger panel are platform menu items,
  not Sentinel features. `[INFERRED]`
