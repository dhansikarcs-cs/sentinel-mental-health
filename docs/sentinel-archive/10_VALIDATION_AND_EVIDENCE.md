# 10 — VALIDATION AND EVIDENCE

*Tests, benchmarks, live verification, the first successful hardware integration, and evidence
classification. Nothing unverified is described as validated.*

---

## 1. Evidence classification scheme (the project's own) `[REPO]`

`docs/research/PHASE1_REPO_AUDIT.md` §1: `[IMPLEMENTED]`, `[EXPERIMENTALLY TESTED]`,
`[SIMULATED]`, `[EXTERNALLY VALIDATED]`, `[PARTIALLY IMPLEMENTED]`, `[PLANNED]`,
`[UNSUPPORTED]`. `IRIS_2026_SENTINEL/09_COMPLIANCE/Evidence_Classification.md`: Demonstrated /
Implemented / Proposed / **Removed**. `IRIS/phase13_claim_audit.md`: `[R]` reproducible
(MD5-pinned), `[L]` literature, `[P]` policy/implementation constant, `[S]` synthetic corpus.

**Section 5 of the audit (REAL / SIMULATED / UNSUPPORTED):**
- REAL: TF-IDF classifier + risk engine, server `_detect` discrepancy, crisis state machine /
  per-patient rows / escalation config, authn/authz/rate limiting/audit/encryption scaffolding,
  golden-set CI gate.
- SIMULATED: prose benchmark figures (esp. "96%", latency, storage), the (then) ring, 30s/60s as
  clinical protocol.
- UNSUPPORTED: clinical effectiveness, diagnostic capability, treatment effect, generalisation
  to real patients.

---

## 2. Test history (counts preserved as historical layers) `[REPO][SESSION]`

| Count | Era | Source |
|---|---|---|
| 43/45 | Phase 3, 2026-07-18 | logbook |
| 45 benchmarks / 5 categories | Phase 2, 2026-07-15 | logbook |
| 9 ring API/SDK tests | M0, 2026-08-03 | logbook |
| **82 → 89 → 93 → 98** | 2026-08-05 demo/feedback/insights rounds | logbook |
| 98 passed (12 modules, 71.37 s) + 47 benchmark runs | 2026-08-06 | logbook |
| 98/98 in 67.5 s | IRIS_2026_SENTINEL pack | Experimental_Results.md |
| 99 pass locally | Phase 1 audit, 2026-09-01 | PHASE1_REPO_AUDIT.md |
| 99-test research suite | IRIS phases 12/13 | phase13 |
| **216 → 222 passed** | Phase 8 scale + Phase 9 security | logbook |
| **222 passed, 33 warnings, ~72–85 s** | Current (repeatedly verified in working sessions) | pytest `[SESSION]` |

**CI gates (used in working sessions):** `python -m ruff check backend/` (All checks passed),
`python -m ruff format --check backend/` (178 files already formatted),
`python -m pytest backend/tests -q` (222 passed), `tsc -b --pretty false` (exit 0),
`npm run build` (exit 0) — both frontend commands **run from `frontend/`**. `[SESSION]`

**Golden set:** 14 cases (10 risk + 4 emotion) → **23 cases (16 risk + 7 emotion)**,
`python -m scripts.eval_golden_set --strict`, enforced in CI. Expanded with grief, financial
stress, burnout, hopeful recovery, physical illness, loneliness; optimism/caring/grief emotions.
`[REPO]`

**6-job GitHub Actions CI** (`.github/workflows/ci.yml`): lint+typecheck, security scan, backend
tests, frontend build, docker build, deploy. `[REPO]`

---

## 3. Benchmark results (multiple runs — all preserved) `[REPO]`

| Component | Result |
|---|---|
| Discrepancy engine | **96% (48/50)** TP 21, TN 27, FP 2, FN 0, <0.1 ms (older); **100% in-set + held-out 50-profile suites, zero FP/FN** (newer rule-fidelity framing) |
| Crisis concurrency | 1/5/10/25 patients **101.6–109.3 ms**, **0 dropped threads**; halt at 15/45/65 sim-s → 750/2,250/3,266 ms; TIME_FACTOR=20 |
| Storage I/O | JSON unencrypted 33.4 ms / 2.7 KB (10 profiles), 23.6 ms / 13.5 KB (50); JSON encrypted 38.7/48.5 ms; SQLite WAL 35.8/41.1 ms; **100 concurrent writes (10 threads × 10 profiles) in 62.6 ms, zero errors**; 23–181 ms at 10–500 profiles |
| Crypto | PBKDF2 600K **154.8 ms** (TD §4) / **≈173 ms derive, ≈169 ms round-trip** (paper §6.4, logbook #0023/#0030) / **233.2 ms** (earlier Phase-3) — all within NIST SP 800-132 100–300 ms band; Fernet <2 ms; JWT ~0.5 ms |
| AI latency | Mock **≈50.5–51.3 ms** (dominated by mock's own 50 ms sleep); real Ollama **5,076 ms cold / 1,449–1,746 ms warm**; Groq Ollama/Groq benchmark rows FAIL = missing services in Docker (expected, not routing defect) |
| Live API | REST 7–41 ms; login 397.5 ms; full AI triage pipeline **4,711.6 ms** |
| Benchmark harness | 47 logged runs, 45 PASS / 2 expected-skip (Groq, no key); CSV `backend/benchmarks/logbook_benchmark.csv` rows `#0001`–`#0047`; "33-row logbook" IRIS-standard columns |
| Final stack stats | 54 benchmarks (52 pass; 9 ring API/SDK tests); ~25,000 lines |

**Explicit caveat:** "The 2 FAIL results are expected"; "only exerciseable provider is the
always-available mock"; pilot load simulator `scripts/sim_pilot_load.py` up to 100 software
clients but "**no load-test numbers are claimed**" (not archived in the logbook). `[REPO]`

---

## 4. Live API / deployment verification (2026-11-16, over real HTTPS) `[SESSION][REPO]`

From `deploy/DEPLOY.md` §"FINAL LIVE VERIFICATION" and the working-session checks:
```
GET  /health                                  -> 200 (healthy; DB read+write, classifier up)
POST /api/auth/login alaya / <withheld>       -> 200
POST /api/auth/login cel / <withheld>         -> 200
POST /api/auth/login Sankari / <withheld>     -> 200 (Patient)
POST /api/auth/login Dhansika / <withheld>    -> 200 (Psychologist)
GET  /api/patients/me/wellness (alaya)        -> bpm 81, spo2 98.0, hrv 41, temp 35.86,
                                                 stress None, sleep None   (no fakes)
GET  /api/patients/me/wellness (Sankari)      -> ring=null, last_synced=None,
                                                 sync_due=true, reading_count=0
POST /api/discrepancy/check-patient           -> 200 (patient self & assigned psych)
     patient comparing someone else           -> 404 (RBAC)
     Dhansika -> alaya                        -> 403
     cel -> Sankari                           -> 403
     unauth /api/patients/me/wellness         -> 401
GET  /api/patients/{username}/vitals          -> self 200 / assigned psych 200 /
                                                 unassigned 403
GET  /  and /trustee                          -> 200 SPA
GET  /api/ring/data, /api/sensor-readings     -> 200 (empty for new accounts)
bundle contains: "Ring not connected", "Wearable Ring", "Bluetooth unavailable",
                 "Journal ↔ Vitals Comparison", "No readings yet", "Last synced",
                 "Sync due today", "My Wearables", "These are your own ring readings"
```
Production certificate issued by `acme-v02.api.letsencrypt.org` via tls-alpn-01; auto-renewal
by Caddy. Full BLE-path bundle check returned **ALL: True** (navigator.bluetooth, requestDevice,
`R30 PRO`/`F085`/`heart_rate` filters, all three YCBT UUIDs, startNotifications,
`/ring/data`, `/sensor-readings`, `sentinel-ring-queue`, all state strings). `[SESSION]`

**Docker/container verification:** `docker compose -f deploy/docker-compose.prod.yml config
--quiet` exit 0; built images `sentinel-prod-sentinel-backend`, `-frontend`; 3 containers Up
(backend healthy); `npm ci --dry-run` exit 0 (lockfile in sync); `sshd -t` valid before reload;
key-only SSH re-verified after `systemctl reload ssh`. `[SESSION]`

---

## 5. First successful live hardware integration (evidence) `[REPO]`

- **2026-11-15T10:34:04 UTC** — `hardware_lab/out/first_measurement.json`: `status: SUCCESS`,
  heart rate **83 bpm**, frame `06 01`, payload `53`, raw `06010700533b45`,
  **`crc_validated: true`, `clinically_validated: false`**. `ycbt_session.json`: 7 frames sent,
  8 received, 1 HR frame.
- **End-to-end ingestion (throwaway DB):** `POST /api/ring/data {bpm:83, spo2:96.0, seq:1} →
  200`; `RingSensorLog` stored only measured fields (stress/hrv/sleep None); `SensorReading`
  `hr=83`, `rmssd=None`, `sdnn=None`, `temp=None`.
- **Pilot seeding (`seed_recorded.py`):** 3 real HR (89/85/83) + spo2 96 / hrv 37 + temperature
  35.86 via `/api/sensor-readings`; `seed_recorded_result.json` shows `/me/wellness` ring with
  device_id `viaking_r30pro_F085`.
- **FINAL LIVE SYNC ~13:54 UTC:** `python sync_history.py --enable-writes` → 6 HR + 5 combined
  records → auto-paired → **11 × `POST /api/ring/data`, ALL HTTP 200**. `sync_seq.json` seq 11 at
  13:54:29.
- **History grounding:** `05 06` returned 89/85/83/74 bpm matching live readings exactly.
- **ECG:** 245 CRC-valid `0605` frames, 21,315 int16 samples, 44,100 bytes,
  `ecg_waveform.csv` + `ecg_waveform_summary.json`. **Raw ADC, not clinical ECG.**
- **Local DB after purge:** 14 real hardware rows, zero non-null stress/sleep; UI shows
  `bpm 81 | spo2 98.0 | hrv 41 | temp 35.86 | stress — | sleep —`.

Full detail: `08_HARDWARE_AND_EXPERIMENTS.md`.

---

## 6. Research validation evidence `[REPO]`

- Model artifact MD5 `9a8d157c6e42706c43b354df6d1025fc`; GoEmotions official train+val 48,836 /
  test 5,427; leak-free micro-F1 0.4642 / macro 0.4047 / samples 0.4947; seed 42.
- E1–E4 results with 1,000 paired bootstrap CIs and McNemar exact binomial; H1/H2/H3
  supported, **H4 refuted** (see `06_RESEARCH_ARCHIVE.md` §7).
- Discrepancy verification: `0/131` negative OOD texts flagged; `1,711/1,787 (95.7%)`
  neutral GoEmotions + high-stress flagged — a policy property, not a learned result.
- `IRIS/phase13_claim_audit.md`: 16 headline claims classified, "**Research-quality gate:
  PASS**"; verification signatures `pytest 99 passed`, `phase10 = 8,271 words`, `phase11 =
  1,490 words`.
- `IRIS_2026_SENTINEL/09_COMPLIANCE/Medical_Claim_Audit.md`: "All 14 submission files pass …
  Overall: PASS"; `Redaction_Audit.md`: "All 14 submission-facing files are clean".

---

## 7. Red-team / audit evidence (negative evidence, preserved honestly) `[REPO]`

- **Penetration test 2026-07-18:** 22 findings (4 critical, 8 high, 7 medium, 3 low), all
  patched same day (IDs A–S). `[CONFLICT — one doc says 8 medium]`
- **Red-team 2026-08-04:** 43 findings (41 + 2), 6 critical / 10 high / 15 medium / 12 low; 8
  code-solvable fixed in `cc43d0b`; rest deployment/misconfiguration.
- **`concerns.md`** (private, "Panel mindset: reject Sentinel"): 43 issues across 14 categories;
  **"Overall: 3.8/10 as a deployable clinical system. ~9/10 as a well-engineered prototype."**
  "**excellent engineering discipline aimed at the wrong acceptance criteria.**"
- **`SECURITY_AUDIT.md` (2026-09-04):** Critical 1 (live credentials in `.env` — flagged for
  rotation, values withheld), High 2, Medium 2, Low 5; **git history clean** (`.env` never
  committed); 7 of 20 models encrypted, expanded to `AIAnalysis`/`RiskAssessment`/
  `RingSensorLog.raw_json` on 2026-09-04; numeric physiology/risk/emotion floats plaintext
  **by design**; DB-file-level encryption "**Must be in place before any real pilot data**".
- **Known limitation statements:** "no clinical-grade physiological validation"; "no formal
  certification. IEC 62304, ISO 13485, ISO 14971 … have not been performed"; "no human-subjects
  data use or claim"; crisis timings measured only in compressed time; dataset programme "none
  are yet acquired".

---

## 8. What is explicitly NOT validated `[REPO][SESSION]`

- No clinical efficacy, diagnosis, treatment effect, or generalisation claim.
- No human-subjects / IRB-eligible research; D_OUT is synthetic and non-clinical.
- No hardware-level clinical validation; raw ECG ADC is not a clinical ECG interpretation.
- BP byte layout is an INFERRED candidate, never clinical.
- Stress/fatigue are unsupported by the ring firmware; sleep requires overnight wear.
- Browser Web Bluetooth connect is built and bundle-verified but has **no recorded successful
  live BLE handshake from a hosted browser**; server-side auth/payload shapes were verified.
- The Sept 2026 30-subject IRB pilot and dataset acquisition are specified, not recorded as
  executed.
- No formal regulatory certification; no MFA / refresh tokens; no SBOM.

---

## 9. Confidence / gaps `[UNKNOWN]`

- `deploy/DEPLOY.md` verification lines were produced during working sessions; they are
  consistent with this archive's own live checks but are not independently reproducible from git.
  `[SESSION]`
- Some benchmark numbers differ between `TECHNICAL_DESIGN.md`, the paper, and the logbook
  (different runs/modes) — all preserved, none silently reconciled. `[CONFLICT]`
- The exact outcome of any IRIS/ISEF/Samsung submission is not available. `[UNKNOWN]`
- `backend/benchmarks/` CSV/JSON research result files were not individually opened during
  archiving; numbers come from the phase docs and paper. `[UNKNOWN]`
