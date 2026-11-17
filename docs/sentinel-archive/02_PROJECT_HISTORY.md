# 02 — COMPLETE PROJECT HISTORY (CHRONOLOGICAL)

*Reconstructed from git history (73 commits, 2026-05-12 → 2026-10-03), the engineering logbook,
the research phase documents, the hardware lab timestamps, and the accumulated working-conversation
record. Dates are preserved where available; nothing is invented. Older/superseded states are kept
as `[HISTORICAL]`.*

---

## 0. Summary of eras

| Era | Dates | What happened |
|---|---|---|
| Pre-git hardware prototyping | Late 2025 – Feb 2026 | Custom smart ring dream → MAX30102/Arduino → KiCad PCB → failure → **OEM pivot** |
| Phase 1 — Streamlit prototype | 2026-03 → 2026-06-20 | Monolithic Streamlit app, first git commit, V1 ecosystem, UI sprints |
| Phase 2 — FastAPI + React rewrite | 2026-07-15 | Complete rewrite, audit log, SQLite fix, Render deploy, WebSocket fix |
| Phase 3 — Security hardening | 2026-07-18 | Pen-test 22 findings patched same day |
| Phase 4 — Documentation | 2026-07-18 | Docs refresh, logbook, PDF generation (6 attempts) |
| Phase 5 — Crisis, PWA, funding, hardware M0 | 2026-07-19 → 2026-08-03 | Trustee portal, PWA, Emergent Ventures, Jport ring, ring SDK/M0 |
| Phase 6 — Red-team audit | 2026-08-04 | 43 findings; 8 code-solvable fixed |
| Phases 1–9 (research/refactor programme) | 2026-08-03 → 2026-09-01 | Architecture constitution, refactors, decision priorities, research audit |
| Test expansion / demo review | 2026-08-05 | 82 → 89 → 93 → 98 tests; bugs found; UI/theme eras |
| Scale + security batch | 2026-09-08 → 2026-09-09 | PostgreSQL, multi-worker, Argon2id, 222 tests |
| Research programme (Phases 1–13) | 2026-09 (context) | Repo audit, F1–F5 flaws, RQ selection, lit matrix, E1–E4 results, negative result |
| Docs/licence refresh | 2026-09-13 → 2026-10-03 | All-rights-reserved wording, README points to live repo |
| **Working sessions (uncommitted)** | 2026-11-15 → 2026-11-16 | Viaking R30 PRO BLE lab, simulation removal, comparison UI, Web Bluetooth, hosting & live deployment |

**Note on two parallel "Phase N" numbering systems.** The engineering logbook uses Phases
1–9 for *development*; `docs/research/PHASE*.md` uses Phases 1–9 (and IRIS phases 10–13) for the
*research programme*. They are distinct and both are preserved. `[CONFLICT in terminology only]`

---

## 1. Pre-git — hardware prototyping (Late 2025 → Feb 2026) `[GIT][REPO]`

From `docs/ENGINEERING_LOGBOOK.md` §"Pre-Git — Hardware Prototyping":

- **Late 2025:** "Started with a dream: build a custom smart ring for emotion detection. Ordered
  MAX30102 PPG sensors. Prototyped on Arduino Nano. Got heart rate readings after a week of I2C
  register hacking."
- **Early 2026:** "HRV was a nightmare on raw sensor data. Peak detection, inter-beat intervals,
  frequency-domain analysis — spent weeks getting a rolling 5-minute HRV window that didn't
  crash."
- **Jan 2026:** "Designed a custom 2-layer PCB in **KiCad 7.0** — **nRF52840 BLE + MAX30102**,
  **37 vias**. Sent to **JLCPCB (¥240, 12-day lead)**." **Failure:** "PCB arrived. Soldered it.
  nRF52840 wouldn't flash. `JLinkARM.dll: Could not connect to target`. Root cause: **USB D+/D−
  traces were reversed**. Took a week to trace the schematic error."
- **Feb 2026 — OEM Pivot:** "Did the math. PCB rev2 = ¥240 + 12 days. **Enclosure molding =
  ₹15,000 minimum**. Battery certification = months. Time = 3+ months. **Decision: Stop building
  hardware. Use consumer smart rings (Oura, Ultrahuman, Apple Watch). Sentinel becomes a software
  platform. Any device exposing HR/HRV via API is compatible.**"

The paper (§5.2) restates this: an "nRF52840 (BLE) + MAX30102 photoplethysmography PCB
fabricated at JLCPCB (¥240, 12-day lead-time) would not flash firmware: the USB D+/D− traces were
reversed, and isolating the schematic error against the JLink debugger took roughly a week";
the pivot "eliminated FDA 510(k) and FCC certification and procurement", and "an FDA
510(k)-classifiable custom device was explicitly rejected after a failed PCB fabrication
attempt". `[REPO]`

**3D-casing evidence.** `boost/research_paper.md` (a *template/draft*, with "Your Draft Expansion
Space" placeholders) §II.A asks to "Map out the **3D casing file logic** and the tight spatial
tolerances required to fit a low-power BLE antenna, a curved lithium-polymer battery, and
surface-mount sensor arrays (PPG and EDA) inside a **rigid-flex PCB layout**." This is a
*planned* hardware-design narrative, not a completed 3D design. `[REPO][INFERRED]`

**A later, separate KiCad artifact.** `C:\Users\dhans\Desktop\Sentinel__\` contains
`Sentinel__.kicad_pcb` (79 bytes), `Sentinel__.kicad_sch` (230 bytes), `Sentinel__.kicad_pro`,
`Sentinel__.kicad_prl`, LastWriteTime **2026-05-24**, generator **pcbnew/eeschema 10.0**. These
are near-empty stubs — evidence of a *later attempted restart* of a board design (May 2026),
not a finished PCB. `[REPO][INFERRED]` See `08_HARDWARE_AND_EXPERIMENTS.md`.

---

## 2. Phase 1 — Streamlit prototype (2026-03 → 2026-06-20) `[GIT][REPO]`

- **2026-03 to 2026-04:** Entire app in **Streamlit 1.28**, monolithic:
  `main_.py` (444 lines), `agent_.py` (720), `database.py` (966, raw SQLite), `crisis_.py`,
  `patient_portal_.py`, `psychologist_.py`, `ring_.py` (**ring data simulator**),
  `app/ml/emotion_model.pkl` (2.5 MB GoEmotions TF-IDF model).
  **Bug:** "Streamlit single-threaded. `time.sleep(3)` auto-refresh for crisis alerts locked the
  entire app. Patient typing journal? Frozen."
- **2026-05-12 — first git commit** `5801c0e`: "initial commit — Sentinel mental health
  platform". Same-day commits: streamlit-autorefresh dep, remove `.venv`, fix Groq logging /
  encryption key for cloud (`f964bdd`), `.gitattributes` binary handling (later, 2026-08-26).
- **2026-06-09 16:45 — `e180f34`:** "Initial commit: Sentinel V1 ecosystem — patient/psych
  portals, crisis detection, ring pipeline, AI agents, activity feed, priority triage,
  onboarding."
- **2026-06-16 — UI sprint (9 commits):** calendar toggle bug, **three palette iterations**
  (dusk-slate → rose-mauve → warm neutrals), 4 agent tests fixed, date-picker → dropdown, mood
  per-day fix (UTC vs IST), emoji visibility CSS.
- **2026-06-19 21:21:** onboarding flow, assigned psychs, TF-IDF emotion classifier training
  pipeline.
- **2026-06-20:** docs updated, proposals finalized, mood timeline chart + risk badge, passwords
  corrected in docs.

The archived Streamlit source survives under `archive/` (`main_.py`, `agent_.py`, `database.py`,
`ai_kernel_.py`, `patient_journal_.py`, `crisis_.py`, `FOUNDERS_GUIDE.md`, `answers.md`,
`software/ACCOUNTS.md`, `INSTALL.md`, logs). `SENTINEL_CODEBOOK.md` explicitly notes it documents
this superseded prototype. `[REPO]`

---

## 3. Phase 2 — FastAPI + React rewrite (2026-07-15) `[GIT][REPO]`

Timeline from the logbook (same day, all commits present in git):

- **06:10 `14c1a01`** — "feat: backend FastAPI+SQLAlchemy, frontend React+Vite, Docker,
  benchmark suite, discrepancy engine, WebSocket real-time alerts". Stack: FastAPI 0.109 +
  SQLAlchemy 2.0 + SQLite/WAL; React 19 + TypeScript 5.4 + Vite 6; bcrypt + HS256 JWT + PBKDF2
  unlock; Docker Compose; thread-based crisis + WebSocket; rule-based discrepancy (18 positive,
  22 negative words); 3-tier AI (Ollama → Groq → rule); **45 benchmarks across 5 categories**.
- **06:42 `dc66736`** — SHA-256 hash-chained audit log with `prev_hash`.
- **07:21 Docker crash** — `sqlalchemy.exc.OperationalError: unable to open database file`.
  Fix: `mkdir -p` in Dockerfile + `os.makedirs()` in main.py (commit `320a621`).
- **18:51 `4cd42ec`** — Render deployment blueprint, nginx WebSocket proxy. **Bug (3 hours):**
  "Nginx strips Upgrade header. Returns HTTP 200 instead of 101." Fix:
  `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`

---

## 4. Phase 3 — Security hardening (2026-07-18) `[GIT][REPO]`

- **05:00 penetration test — 22 findings: 4 critical, 8 high, 7 medium, 3 low.**
- **08:00–10:45 all 22 patched** (IDs A–S): WebSocket auth; `/crisis/*` auth; role escalation
  (`Literal["patient","psychologist"]`); brute-force lockout (5 attempts / 15 min); password
  policy; IDOR (`_owns_or_psych()`); HMAC constant-time compare; non-root containers (UID 1001);
  explicit CORS; default-JWT-secret warning; **HttpOnly cookie auth**; **EncryptedText
  TypeDecorator** (Fernet on 5 fields across 3 models); **RateLimiterMiddleware** (100 req/min/IP);
  DOMPurify; internal Docker network; global exception handlers; **negation handling**
  ("I am not happy" → accuracy 92% → 96%, FN 2 → 0); WAL backup; Ollama request queuing.
- **10:45 cleanup:** deleted `software/` (59 files, ~10,700 lines Streamlit) → `archive/`.
- **Benchmarks:** 43/45 tests; accuracy 96% (TP 21, TN 27, FP 2, FN 0); SQLite 48 ms;
  crypto 600K 233.2 ms.

---

## 5. Phase 4 — Documentation (2026-07-18) `[GIT][REPO]`

- `TECHNICAL_DESIGN.md` (14 edits), `JUDGE_QA.md` (12 new Q&A), `ENGINEERING_DECISIONS.md`
  (12 new rows 31–42). **Bug found:** agent wrote rows 31–42 with 5 columns instead of 6;
  manually rewritten; footer "10 patches" → "22 patches".
- `ENGINEERING_LOGBOOK.md` created/revised multiple times: v1 "too casual" → v2 "make it
  specific" → v3 "include everything from start".
- **PDF generation — 6 attempts:** Unicode (Courier → Consolas), horizontal space (`set_x(14)`),
  120-char pre-wrap, `avail < 10` guard, success at 75 pages, concise 4-page stable version.

---

## 6. Phase 5 — Crisis escalation, PWA, funding, hardware M0 (2026-07-19 → 2026-08-03) `[GIT][REPO]`

- **2026-07-19:** suicidal-ideation journal → high-confidence classifier → immediate hotline card
  + trusted-contact portal; real SMTP email to trusted contact; crisis demo handled end-to-end.
- **2026-07-20:** dual-mode AI summaries (warm patient companion + structured **OAP** clinical
  summary); frontend converted to installable **PWA** (manifest, icons, service worker with
  network-first API caching, stale-while-revalidate assets, offline app shell).
- **2026-07-31:** **Emergent Ventures grant** received for hardware procurement + pilot; OEM ring
  sourced from **Jport (China)**, vendor SDK/API + BLE interface (spec sheet pending).
- **2026-08-03 — Hardware M0 (`17261ab`):** ring ingestion + device binding. `RingDevice` model;
  `POST /ring/pair`, `/ring/unpair`, `GET /ring/devices`, `POST /ring/data`; `get_ring_identity`;
  SDK with `RingSource` base, `SimulatedRing`, `VendorAPIRingSource`, `BLEGATTRingSource`
  (bleak, HRM `0x2A37`, battery `0x180F`); scripts `sim_ring.py`, `ring_bridge.py`,
  `test_ring_api.py`; `docs/ROADMAP_HARDWARE.md` created (M1–M3). Verified 9/9 SDK tests.

---

## 7. Phase 6 — Red-team audit (2026-08-04) `[GIT][REPO]`

- `concerns.md` (gitignored private review): **43 findings** (41 + 2), 6 critical, 10 high,
  15 medium, 12 low. 8 code-solvable implemented in `cc43d0b`: export URL token leak, cloud-AI
  opt-in, HMAC trustee links, AI-worker crash evidence, `AiSourceBadge` provenance,
  `scripts/backup_db.py` (Fernet + S3-signed PUT), golden-set CI gate (14 cases → later 23).
- `a824327` — **secure transport layer design** (constitution, E2EE+PFS, clinic pull+ACK,
  dead-letter, zero-metadata routing). **Design only, never implemented** — flagged in
  `concerns.md` #35/#36 and later red-team scoring (Transport 2/10). `[REPO][UNVERIFIED]`

---

## 8. Research programme and refactor phases (2026-08-03 → 2026-09-09) `[GIT][REPO]`

**Development refactor phases (git commits, all 2026-08-03):**
`36dd277` Phase 1 delete dead scaffolding + **architecture constitution**; `5cfbd8e` Phase 2
unify patient-context builder; `ba9efd5` Phase 3 align event store / single SMTP owner / search
index; `befcb03` Phase 4 compose patient overview on backend; `7bd95b3` Phase 5 shared frontend
constants / typed uploads / consultation-first nav; `460ec99` Phase 6 data-driven crisis policy /
prompt versioning / clinician approval provenance; `61842ec` Phase 7 Render deploy alignment /
JSON observability / deployment docs; `3873e61` Phase 8 decision priorities + consultation-first
Open Session.

**Research programme (`docs/research/`)** — dates 2026-09-01 (Phase 1&2 audit), Sep 2026:
- **Phase 1&2 `PHASE1_REPO_AUDIT.md`** — evidence map; `[IMPLEMENTED]/[EXPERIMENTALLY TESTED]/
  [SIMULATED]/[EXTERNALLY VALIDATED]/[PARTIALLY IMPLEMENTED]/[PLANNED]/[UNSUPPORTED]`
  classification; **DECISIVE SCIENTIFIC FINDING**: discrepancy detector is purely rule-based and
  circular; the **emotion classifier is the ONE component with a real label source**; flaws
  **F1–F5** (F1 benchmark tested a divergent local copy; F2 held-out circular; F3 mock latency;
  F4 prose overstates; **F5 validation leakage**: `train_goemotions.py` merged all splits, 80/20
  re-split swept ~80% of official test (4,346 of 5,427) into training, inflating micro-F1 to
  0.610 — fixed to official train+val 48,836, test 5,427, leak-free 0.4642).
- **Phase 3&4 `PHASE3_4_GAPS_AND_QUESTIONS.md`** — gaps G1–G4; candidate questions Q1–Q8 with
  0–3 scoring; **Q2 (calibration, 10/12) primary**, Q1 (distribution shift, 10/12), Q3
  (selective prediction, 9/12) practical arm; Q8 merged into Q3; Q7 relegated to position paper.
- **Phase 5 `PHASE5_QUESTION_SPEC.md`** — formal RQ + RQ-appl; H1–H4 + nulls H0_1–H0_4; IV/DV;
  E1–E4; 7 explicit NON-claims; readiness gate with one unchecked item.
- **Phase 6&7 `PHASE6_7_LIT_MATRIX_AND_DESIGN.md`** — literature L1–L13; locked experimental
  design; D_IN/D_CALIB/D_OUT; statistics (1,000 paired bootstraps, seed 42, McNemar).
- **Phase 8&9 `PHASE8_9_RESULTS.md`** — E1–E4 results; **H1/H2/H3 SUPPORTED, H4 REFUTED**
  ("NEGATIVE RESULT — important and honest"); calibration-then-select proposed.
- **IRIS phases 10–13** (`IRIS/`): `manuscript_phase10.md`, `manuscript_phase11_iris.md`,
  `phase12_adversarial_review.md`, `phase13_claim_audit.md` ("No claim may exceed its evidence").

Full research detail: `06_RESEARCH_ARCHIVE.md`.

---

## 9. Test expansion, demo review, UI/theme eras (2026-08-05) `[GIT][REPO]`

- `1fc6465` — 82-test suite + 3 bugs: **journal summarization always crashed** (literal
  `{"summary": ...}` braces parsed by `.format()` → `KeyError` on every submission, entries stuck
  `ai_source="pending"`), whitespace-only journals accepted, `model_registry` import mutated
  `model_registry.json`.
- `8f3c520` — demo review: risk-scale clamp to 0–10, tokens `localStorage` → `sessionStorage`
  (per-tab sessions), follow-up polish (`due_date`, ownership authz fix, grade-tampering hole),
  shared `MoodPicker`. 89 tests.
- `b7ddb3e` / `273ba61` — psych feedback box, clinician-friendly Patient Insights ("they r psych
  not data analyst na it might be annoying"), plain-English `/patients/{username}/plain-insights`,
  duplicate event-bus subscribers bug. 93 → 98 tests.
- `1306c7a` — Journal→Note explicit accept/cancel; **sage/earth colour-therapy palette** (~630
  tokens across 28 files).
- `2ea6387` — **light "therapeutic calm" theme** (research-backed), scrapping the dark sage pass
  after it "read as worse than before". Palette: warm-white surfaces, calm teal `#17796E`,
  deep-slate text. `[HISTORICAL]`
- `42507e0` — encoding fix (**mojibake** in 7 pages from a PowerShell 5.1 CP1252 bulk edit) +
  **user-selectable light/dark theme** via ~30 CSS custom properties, `useTheme()` hook,
  `localStorage('sentinel-theme')`, OS `prefers-color-scheme`, pre-paint script.
- `15f3137` / `acd88ab` / `49cd13f` — dark-mode polish, light-token darkening, theme-aware biodata.
- **2026-08-06:** incubation-centre pack (`kiot/`, `20db2b7`, `9be2e38`, `c9834ca`); research
  paper (21 pp), white paper (5 pp), validation & timing report (4 pp); fresh validation: **98
  passed**, 47 logged benchmark runs (45 PASS / 2 expected-skip), discrepancy 96.0% at 0.1 ms,
  crisis concurrency 102–109 ms 0 dropped threads, real Ollama 5,076 ms cold / 1,449–1,746 ms
  warm, live API REST 7–41 ms, login 397.5 ms, full AI triage 4,711.6 ms; logbook CSV 47 rows.
  `499f0d5` — trustee ACK link reads `SENTINEL_ACK_LINK` via settings.

---

## 10. Scale + security batch (2026-08-25 → 2026-09-09) `[GIT][REPO]`

- `813d69f` — emotion classifier trained on **real GoEmotions** (54k examples).
- `e79477f` / `3c61bac` — pin Python 3.11 in Dockerfile; binary `.gitattributes`.
- `f75600b` — **per-patient crisis state rows** (previously singleton, crises overwrote each
  other).
- `b2e809a` — all-rights-reserved licence.
- `8161e3b` / `fb6a9e7` / `aedb78e` (2026-09-09) — multi-worker rate limiting, DB blacklist,
  single failover scheduler (PostgreSQL advisory lock `749493`), zero-cost PG LISTEN/NOTIFY
  fan-out (`WS_PUBSUB`), **Argon2id** (time_cost 3, memory 65536, parallelism 4) with transparent
  legacy-bcrypt re-hash, **read-path encryption hard-fail** (`EncryptionNotReadyError`), golden
  set expanded to 16 risk + 7 emotion, `.env.example` field names fixed. **216 → 222 passed.**
- `dbb9a7a` — docs end-to-end refresh, honest cost model, updated paper.
- `1bd8573` (2026-09-13) — correct licence wording "released for review (All Rights Reserved),
  not open source".
- `d5d05fa` (2026-09-17) — Bearer token on `POST /ring/data` patient-JWT fallback; sim_ring
  survives already-paired devices.
- `e1d58fa` (2026-10-03, HEAD) — README points to the actively developed/deployed repo
  `sentinel-mental-health`.

---

## 11. Working sessions — the November 2026 period `[SESSION][REPO]`

These changes are **uncommitted** in `sentinel3` (git status shows ~30 modified + ~15 untracked
files). They are a first-class part of project history.

**2026-11-15 — Viaking R30 PRO BLE lab.** Full reverse-engineering of the YCBT protocol from a
physical ring (see `08_HARDWARE_AND_EXPERIMENTS.md`). First genuine measurement 10:34:04 UTC
(83 bpm); ECG waveform 245 frames / 21,315 samples; final live history sync ~13:54 UTC —
**11 × `POST /api/ring/data`, all HTTP 200**. Raw packets preserved in `hardware_lab/out/`.

**2026-11-15/16 — "take all simulations away".** Deleted `backend/app/services/ring/simulated.py`;
removed `mockHistory` from `frontend/src/constants.ts`; made ring/sensor-reading schemas and
models nullable with no defaults; removed derived `sdnn = hrv*0.8` and hardcoded
`temperature=36.5`; stopped the `/api/physio.py` derivation; deleted 10 fake seeded `ring_alaya`
rows from the local DB, leaving **14 real hardware rows with zero non-null stress/sleep**. Fixed
`ring-vitals-risk` (was filtering by the psychologist's own username) and `/me/wellness` (newest
row only) to report the latest genuinely measured value per signal across the last 50 rows.

**2026-11-15/16 — journal↔vitals comparison wired into the UI.** Added
`POST /api/discrepancy/check-patient` (server reads real stored journal + real wearable rows,
RBAC: patient self or assigned psychologist, missing data → `insufficient_data`), client method,
and cards in `PsychTriagePage.tsx` and `Dashboard.tsx`. Fixed stale login demo buttons.

**2026-11-15/16 — Web Bluetooth for hosted use.** New `frontend/src/ring/`
(`ycbt.ts`, `webBluetooth.ts`, `ringQueue.ts`), `RingConnect.tsx`/`RingConnectButton.tsx`,
durable IndexedDB queue (`sentinel-ring-queue`), deterministic idempotent `seq`, API cold-start
retry (502/503/504), boot/online flush. Verified `tsc -b` 0, `vite build`, ruff, **222 tests**.

**2026-11-16 — hosting/domain procurement and live deployment.** Long decision process (Render
card-only, AWS India UPI, Hostinger India VPS, minor/18+ account-holder constraint). Domain
`sentinelpsytech.com` bought at GoDaddy with UPI; Hostinger KVM 1 / Ubuntu 24.04 LTS / UPI;
firewall group `sentinel-web` (Accept TCP 22/80/443); DNS A record → VPS; **production Let's
Encrypt TLS** via Caddy (had to clear a **staging** fallback); key-only SSH; Docker Compose
production stack deployed to `/opt/sentinel`. Full detail: `deploy/DEPLOY.md`,
`04_SYSTEM_ARCHITECTURE.md`, `09_DECISION_HISTORY.md`.

**2026-11-16 — demo accounts and self-care.** Created patient `Sankari` (password withheld) and
psychologist `Dhansika` (password withheld) by direct DB seed (the public signup policy requires
6+ chars with mixed case/digit/special); reassigned Sankari from `cel` to `Dhansika`. Corrected a
misreading: the psychologist has **their own** ring/self-care space (`WearablesPage`, "💍 My
Wearables" tab for both roles, own Connect ring button, own last-sync nudge), not a view into a
specific patient's vitals. Added an always-visible `RingVitalsCard` (dashes + "No readings yet" +
relative "Last synced" + "Sync due today") so an empty account never looks broken.

**2026-11-16 — PWA/background-collection discussion.** Confirmed the existing service worker
cannot keep BLE alive in the background (browser limit); the ring stores its own history and the
IndexedDB queue survives tab closes. A brief connect-then-disconnect for charging explained the
0 stored rows for the new account — backend logs showed zero `POST /api/ring/data` in the last
hour. `[SESSION]`

---

## 12. Milestones and direction-changing decisions (quick index)

- Feb 2026 **OEM pivot** — biggest early direction change (custom hardware → software platform).
- 2026-07-15 **FastAPI + React rewrite** — Streamlit abandoned.
- 2026-07-18 **22 security patches** in one morning.
- 2026-08-03 **hardware M0** ring SDK + device binding.
- 2026-08-05 **light theme** chosen over dark sage after side-by-side review.
- 2026-09-01 **F5 validation-leak fix** — honest research metrics (0.610 → 0.4642).
- 2026-09-09 **Argon2id / 222 tests**.
- 2026-11-15 **first real BLE hardware integration** — no simulations.
- 2026-11-16 **live hosted deployment** on a real domain with UPI payment.

See `09_DECISION_HISTORY.md` for the full decision register and `12_DEVELOPMENT_HISTORY.md` for
bugs/debugging/technical debt.

---

## 13. Uncertainties `[UNKNOWN]`

- Exact dates for the pre-git hardware narrative are approximate ("Late 2025", "Early 2026",
  "Jan 2026", "Feb 2026") as written in the logbook; no finer timestamps exist. `[REPO]`
- The 2026-11-15/16 working-session events are dated from file timestamps and the conversation
  record, not git commits (they are uncommitted). `[SESSION][INFERRED]`
- `IRIS`/`ISEF`/`Samsung Solve for Tomorrow` submission outcomes, and whether the Sept 2026
  30-subject IRB pilot actually occurred, are not recorded as completed in the accessible corpus.
  `[UNKNOWN]`
- The `docs - Copy/` folder is an undated snapshot of an older docs generation. `[UNKNOWN]`
