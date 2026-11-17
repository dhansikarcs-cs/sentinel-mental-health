# 12 — DEVELOPMENT AND IMPLEMENTATION RECORD

*Features implemented / partially implemented / planned; experiments; bugs; debugging history;
solutions; technical debt; test results; known limitations; important files/modules; git history.
Never describes an unverified implementation as working.*

---

## 1. Features implemented `[REPO][SESSION]`

**Backend:** 29 API router modules (~120 routes); patient & psychologist portals; journal with
28-label emotion tagging; mood once-per-day; crisis detection/escalation with per-patient state +
trusted contact + helpline; rule-based discrepancy engine; risk engine with explainability;
three-tier AI with dual-mode summarization; plain-English clinician insights; priority triage;
consultation-first Open Session; clinical notes with approval provenance; follow-ups (due dates,
grades, feedback, proof upload); bookings with rescheduling; timeline; notifications/reminders;
export centre; activity feed; event store + replay; offline sync; search; feature flags; ML model
registry; audit hash chain; WebSocket real-time alerts; ring SDK/device binding; physiological
ingestion; `/me/wellness` latest-per-signal; `/{username}/vitals`; `/discrepancy/check-patient`;
PWA backend support; Alembic migrations; PG multi-worker scaling; health endpoints.

**Frontend:** 29 pages, 13 components, PWA (manifest + service worker + icons), light/dark theme
system, onboarding tour, per-tab sessions, offline outbox, Web Bluetooth ring connect, durable
IndexedDB ring queue, always-visible vitals card, last-sync nudge, "My Wearables" for both roles.

**Infrastructure:** `docker-compose.yml` (+`scaled` profile), `render.yaml`,
`deploy/docker-compose.prod.yml`, `deploy/Caddyfile`, `deploy/bootstrap.sh`,
`deploy/.env.example`, `.github/workflows/ci.yml` (6 jobs), `scripts/` (backup_db,
eval_golden_set, sim_ring, ring_bridge, generate_paper_pdf, Modelfile, sentinel_prompt),
`hardware_lab/` (30 scripts, 39 evidence artifacts).

---

## 2. Features partially implemented `[REPO]`

- **BLE GATT adapter** `[PARTIALLY IMPLEMENTED]` — needs vendor spec/UUIDs; `bleak` optional. The
  Nov 2026 Viaking lab recovered the real YCBT protocol, but `BLEGATTRingSource` (standard HRM
  `0x2A37`) was still a scaffold; the real integration lives in `hardware_lab/` (non-production).
- **Vendor API / SDK adapter** `[PARTIALLY IMPLEMENTED]` — single `_fetch()` hook; Jport spec
  sheet pending.
- **Browser Web Bluetooth** — implemented & bundle-verified, **no recorded successful live BLE
  handshake from a hosted browser** `[SESSION]`.
- **Rate limiting** — memory|db shipped; "PARTIAL" per decisions doc ("Redis unnecessary for the
  target scale").
- **Trusted-contact portal, crisis email** — implemented; `concerns.md` flags SMTP silent-failure
  and no clinician-in-the-loop as unresolved.
- **AI provenance** — badges + prompt/model versions implemented; full clinician approval gating
  on all outputs is a design principle, not uniformly enforced (red team #34).
- **Encryption** — 22 fields / 11 models; numeric physiology/risk/emotion floats plaintext by
  design; DB-file-level encryption still required before real pilot data.

---

## 3. Features planned but NOT implemented `[REPO]`

Refresh tokens; Chart.js/D3 biometric trends; secure transport layer (STL); companion mobile
app; cycle-/sleep-aware baselines; calibration-then-select; IRB 30-subject clinical pilot;
dataset acquisition (mcPHASES, WHOOP, Figshare, WESAD, etc.); per-patient contextual baselines;
clinician burnout/self-monitoring dashboard; ABHA/ABDM; PHQ-9/GAD-7; ring manufacturing;
native background BLE sync; MFA/session revocation; SBOM; full regulatory certification (IEC
62304, ISO 13485, ISO 14971); non-English sentiment support; governed longitudinal dataset.

---

## 4. Bug and debugging history (chronological) `[REPO][GIT][SESSION]`

| Date | Bug | Root cause | Fix |
|---|---|---|---|
| 2026-03/04 | Streamlit froze while patient typed | `time.sleep(3)` auto-refresh in single thread | Full rewrite (D2) |
| 2026-06-16 | Calendar toggle bug | useEffect dependency | dependency fix |
| 2026-06-16 | Mood per-day lock wrong | UTC vs IST | timezone fix |
| 2026-06-16 | Emoji invisible / mojibake | CSS; later PowerShell CP1252 bulk edit | CSS fix; CP1252→UTF-8 reverse decode |
| 2026-06-20 | Passwords wrong in docs | doc drift | `d510fd4` |
| 2026-07-15 07:21 | `unable to open database file` | `/app/data` missing in Docker | `mkdir -p` in Dockerfile + `os.makedirs()` in main.py (`320a621`) |
| 2026-07-15 18:51 | WebSocket returned 200 instead of 101 (3 h) | nginx stripped Upgrade header | `proxy_set_header Upgrade/Connection` (`4cd42ec`) |
| 2026-07-18 | 22 pen-test findings | mixed | A–S patches |
| 2026-07-18 | "I am not happy" false positive | keyword match ignored negation | 26 negation prefixes + 4-word window; 92%→96%, FN 2→0 |
| 2026-07-18 | ENGINEERING_DECISIONS rows 31–42 | 5 columns instead of 6 | manual rewrite |
| 2026-07-18 | PDF generation | Unicode / spacing / page breaks | 6 attempts → 4-page stable |
| 2026-08-04 | Export URL leaked JWT in query string | `?token=` fallback | `Authorization: Bearer` + blob download |
| 2026-08-04 | Cloud AI fired when disabled | no opt-in gate | `allow_cloud_ai=False` |
| 2026-08-04 | Trustee links predictable | plain tokens | HMAC over patient+expiry |
| 2026-08-04 | AI worker crashed with no evidence on skip | cooldown skip path | emits `journal:summarized`; cooldown centralized |
| 2026-08-04 | No DB backup | — | `scripts/backup_db.py` (Fernet + S3) |
| 2026-08-04 | No golden-set regression gate | — | `scripts/eval_golden_set.py --strict` |
| 2026-08-05 | **Journal summarization ALWAYS crashed** | literal `{"summary": ...}` braces parsed by `.format()` → `KeyError: '"summary"'` on every submission; worker caught it → entries stuck `ai_source="pending"` | escape braces `{{...}}` + regression test |
| 2026-08-05 | Whitespace-only journals accepted | sanitize→"" not rejected | explicit 422 |
| 2026-08-05 | `model_registry` import mutated `model_registry.json` | module-level register rewrote `trained_at` | preserve `trained_at`, skip no-op writes |
| 2026-08-05 | "15/10" risk looked broken | legacy DB rows 15/20 predate 10-cap | clamp 0–10 at read + write |
| 2026-08-05 | Two tabs swapped profiles | `localStorage` shared token | `sessionStorage` per-tab |
| 2026-08-05 | Patient could grade own follow-up | missing authz | ownership + grade-tampering fix |
| 2026-08-05 | Duplicate event-bus subscribers | bus accumulated subscribers per lifespan | `register_all_subscribers` clears bus first |
| 2026-08-05 | "Top Emotions" bar math wrong | raw 0–1 shown as % | fixed |
| 2026-08-05 | 8-digit hex alphas invalid | `var(--accent)60` | `color-mix(in srgb, …)` |
| 2026-09-01 | **F1** benchmark tested a divergent local discrepancy copy | extra `negative+moderate→True` rule | import real `_detect` |
| 2026-09-01 | **F2** held-out labels circular | derived from same rules | reframe as consistency |
| 2026-09-01 | **F5 validation leakage** | merged splits, 80/20 re-split | train+val only, official test, MD5-pinned model |
| 2026-09-09 | PG driver missing → deploy path broken | `psycopg2-binary` absent | added |
| 2026-11-15 | `0xFE` "Data error" | missing vendor 2-byte Get tags | `GET_TAGS` |
| 2026-11-15 | `collector.py` got no HR | subscribed only `be940001`; real `0601` arrives on `be940003` | subscribe both |
| 2026-11-15 | `sync_history.py` device_id mismatch | different id used | aligned to `viaking_r30pro_F085` |
| 2026-11-15 | Ring stuck in ECG streaming mode, 0 devices | interrupted run, no paired stop | charging case 10 s, rewear; `probe_ecg_final.py` stops in `finally` |
| 2026-11-15 | SpO₂ "no data" on 18–20 s windows | algorithm needs 26+ iterations / 30–60 s | 90 s window + 20 s cooldown |
| 2026-11-15/16 | `/me/wellness` & `ring-vitals-risk` lost bpm on partial rows | newest row only | latest measured value PER signal across last 50 rows |
| 2026-11-15/16 | Fake vitals leaked (`stress:40`, `sleep:8.6`) | 10 old `ring_alaya` seeded rows | deleted; 14 real rows remain |
| 2026-11-15/16 | `ring-vitals-risk` filtered by psych's own username | wrong filter | defaults latest among assigned patients + optional username check |
| 2026-11-15/16 | `checkOwnDiscrepancy` would send fake `bpm:0/hrv:0` | no-fabrication violation | removed; server-side `/check-patient` used |
| 2026-11-15/16 | TS `Uint8Array<ArrayBufferLike>` BufferSource error | TS 5.6+ | copy to plain `ArrayBuffer` |
| 2026-11-15/16 | `ai_service.py` `NOTE_SYNTHESIS_PROMPT_V1` | stale constant | → `V2` |
| 2026-11-16 | Frontend Docker build could resolve fresh deps | only `COPY package.json`, `npm install` | `COPY package.json package-lock.json` + `npm ci` |
| 2026-11-16 | Frontend nginx template missing `PORT`/`BACKEND_URL` | compose had no frontend env | prod compose sets both |
| 2026-11-16 | Backend port mismatch (Dockerfile 10000 vs compose 8000) | `${PORT:-10000}` default | prod compose sets `PORT=8000` |
| 2026-11-16 | CORS/ACK link built from bare hostname | `${DOMAIN}` reused | derive `https://${DOMAIN}` |
| 2026-11-16 | Bootstrap health check hit wrong URL | Caddy redirects HTTP→HTTPS | check inside backend container |
| 2026-11-16 | Python script `/tmp` couldn't import `app` | `sys.path[0]` = script dir | `-w /app -e PYTHONPATH=/app` |
| 2026-11-16 | Caddy stuck on **staging** cert | long failed-attempt history | clear `caddy_data` certificates/acme, restart → production cert |
| 2026-11-16 | CRLF in `bootstrap.sh` on Linux | Windows line endings | normalized to LF before upload |
| 2026-11-16 | Tarball leaked test `.db`/WAL files | insufficient excludes | `*.db`, `*.db-wal`, `*.db-shm`, `backend/data` excludes; copy only the real DB separately |
| 2026-11-16 | Wellness card vanished with 0 rows | `{wellness?.ring && ...}` | always-visible `RingVitalsCard` |
| 2026-11-16 | `WearablesPage.tsx` created but route/tab missing | oversight | added route + "💍 My Wearables" tab for both roles |

---

## 5. Technical debt / known limitations `[REPO][SESSION]`

- ~8 open TODOs; refresh tokens OPEN; per-patient crisis states doc/code lag; no Chart.js/D3.
- Rule-based engine: sarcasm, clinical jargon ("DSM-5 criteria, PHQ-9 items, GAD-7 phrases"),
  English-only negation, code-switching ("I feel very anxious yaar"), dissociation with calm
  biometrics.
- Encryption: numeric physiology/risk/28 emotion floats plaintext by design; Fernet 128-bit;
  hash-chained audit "not tamper-proof"; passphrase loss → unrecoverable.
- Deployment: Render ephemeral filesystem = expected data loss; SQLite single-writer; Groq
  raw-PHI concern default-off; free-tier cold starts (45–60 s).
- Research: synthetic OOD, no clinical/IRB claims, no dataset acquired, no certification,
  validation scale small.
- Live VPS: `ENCRYPTION_REQUIRED=false` (pilot only); single origin (not multi-region edge);
  all Nov 2026 changes **local/uncommitted** in `sentinel3`; the live Render app deploys from the
  separate `sentinel-mental-health` repo, so local changes have **not** been ported/pushed.
- `backend/app/ml/model_registry.json` must be reverted if dirty before commits.
- `docs - Copy/`, `IRIS_2026_SENTINEL/`, `SENTINEL_CODEBOOK.md`, `archive/` retain pre-audit
  numbers (0.465 / 54,263 / 96%) — a real historical inconsistency layer.
- Root `.env`, `SECURITY_AUDIT.md`, `archive/software/ACCOUNTS.md`, `archive/thoughts/*` contain
  credentials / private personal data — flagged for rotation/redaction, values withheld here.

---

## 6. Important files and modules `[REPO]`

| Path | Role |
|---|---|
| `backend/app/main.py` | app, middleware, routers, health, SPA fallback |
| `backend/app/core/config.py` | all settings / env var names |
| `backend/app/core/security.py` | Argon2id, Fernet, PBKDF2+HKDF, trustee HMAC |
| `backend/app/core/dependencies.py` | auth, role, `get_ring_identity` |
| `backend/app/core/encrypted_fields.py` | `EncryptedText` TypeDecorator |
| `backend/app/api/ring.py` | pair/unpair/data; only measured fields; idempotent seq |
| `backend/app/api/patients.py` | `_ring_vitals`, `/me/wellness`, `/{username}/vitals` |
| `backend/app/api/discrepancy.py` | `_detect`, `/check`, `/check-patient` |
| `backend/app/api/agents.py` | `ring-vitals-risk`, triage, insights |
| `backend/app/ml/*` | emotion classifier, risk engine, crisis policy, registry |
| `backend/app/services/ring/*` | base / ble_gatt / vendor_api (simulated removed) |
| `frontend/src/ring/*` | ycbt, webBluetooth, syncRing, ringQueue |
| `frontend/src/components/RingConnect*.tsx`, `RingVitalsCard.tsx` | ring UI |
| `frontend/src/pages/{Dashboard,PsychTriage,Wearables}.tsx` | vitals/comparison/self-care |
| `frontend/src/components/Layout.tsx` | side panel, sync nudge |
| `frontend/src/api/client.ts` | BASE `/api`, retry, all API methods |
| `frontend/nginx.conf`, `frontend/Dockerfile` | template with `${PORT}` / `${BACKEND_URL}` |
| `deploy/*` | production compose, Caddyfile, bootstrap, runbook |
| `hardware_lab/*` | BLE lab (EXPERIMENTAL) |
| `docs/*`, `docs/research/*`, `kiot/*`, `IRIS/*`, `IRIS_2026_SENTINEL/*` | documentation & research corpus |
| `scripts/sentinel_prompt.md` | master AI guardrails |
| `concerns.md` | private red-team review |
| `render.yaml`, `docker-compose.yml`, `.env.example` | deployment blueprints |

---

## 7. Git development history `[GIT]`

- **73 commits**, 2026-05-12 → 2026-10-03, branch `main`, origin
  `https://github.com/dhansikarcs-cs/Sentinel_V_1_.git`.
- Exact per-date counts: 05-12 (5), 06-09 (1), 06-16 (9), 06-19 (1), 06-20 (4), 07-15 (4),
  08-03 (11), 08-04 (1), 08-05 (14), 08-06 (5), 08-25 (3), 08-26 (2), 08-30 (2), 09-08 (4),
  09-09 (4), 09-13 (1), 09-17 (1), 10-03 (1).
- **Eras:** Genesis & Streamlit v3 (20 commits) → FastAPI+React rewrite & Render (4) →
  `refactor(phaseN)` constitution sprint (11) → transport design/red-team/test expansion/UI/
  pitch (20) → real dataset/lint/licensing (7) → repo hygiene + physiological pipeline (4) →
  scale-hardening + security batch (4) → licence wording/last bugfix/hand-off pointer (3).
- **HEAD** `e1d58fa` (2026-10-03) "docs(readme): point to actively developed/deployed repo
  sentinel-mental-health". Commit `c0af377` (crisis loophole fixes) is referenced in working
  sessions as the last good Render deploy but is **not in this repo's 73 commits** — it belongs to
  the separate `sentinel-mental-health` repo. `[SESSION][CONFLICT]`
- **Sibling checkout** `C:\Users\dhans\Desktop\Sentinel_V_1_\` — same origin, **71 commits**,
  older HEAD `1bd8573` (2026-09-13), contains Azure deployment files
  (`Dockerfile.azure`, `azure-startup.sh`, `build-azure-deploy.sh`, `docs/DEPLOY_AZURE.md`).
- **Separate repos:** `fieldcrypt` (1 commit, 2026-09-20, MIT), `Sentinel__/` (KiCad stubs +
  `.history` git), `Sentinel_V_1_` (above), `research/ids-distribution-shift` (related research),
  `sentinel-mental-health` (remote, live Render deploy — not on disk).

**Working-tree state (2026-11-16):** ~30 modified files + ~15 untracked, including
`deploy/`, `hardware_lab/`, `frontend/src/ring/`, `RingConnect*.tsx`, `RingVitalsCard.tsx`,
`WearablesPage.tsx`, `docs/executive_summary.*`, `docs/pitch.md`, `docs/new_pitch.md`,
`backend/venv/`. **Nothing from the November 2026 sessions is committed or pushed.** `[SESSION]`

---

## 8. Confidence / gaps `[UNKNOWN]`

- `c0af377` and the Nov 2026 crisis-loophole fixes live in the inaccessible
  `sentinel-mental-health` repo; their exact content is summarised from the conversation record
  only. `[UNKNOWN]`
- Several PDF artifacts (`kiot/*.pdf`, `docs/*.pdf`, `MindRise_Hub_Administrative_Project_Paper.pdf`)
  were not opened; they are indexed by filename/size. `[UNKNOWN]`
- Root ZIP artifacts (`.docker.zip` ~594 MB, `compliance.zip`, `link.zip`, `tested.zip`,
  `IRIS_2026_SENTINEL.zip`, `test.pdf`) were not inspected. `[UNKNOWN]`
- `archive/thoughts/` contains private personal writing/chat transcripts — deliberately not
  reproduced. `[UNKNOWN]`
