# 11 — FUTURE VISION AND ROADMAP

*Original roadmap and all later changes preserved separately. Immediate priorities, planned
versions, long-term capabilities, hardware/cloud/data/clinical/research expansion, and
unexplored opportunities. Nothing unimplemented is described as delivered.*

---

## 1. Original roadmap (hardware M0→M3, `docs/ROADMAP_HARDWARE.md`, 2026-08-03) `[REPO]`

**Context:** Emergent Ventures grant; OEM ring from **Jport (China)** — "not a consumer ring with
a public SDK"; goal "real sensor data into clinical/crisis pipelines **without re-architecting
anything downstream**" (only new surface = ingestion).

- **M0 — DONE (2026-08-03):** `services/ring/` SDK, `ring_devices` table, 4 endpoints,
  `sim_ring.py`, `ring_bridge.py`, `test_ring_api.py`, `requirements-bridge.txt`; verified E2E
  pair → token push → stored log → `last_seen_at` → 401 on bad auth.
- **M1 — First live device:** obtain Jport documentation; configure BLE UUIDs
  (`--hrm-uuid`, `--hrv-uuid`, `--stress-uuid`) + byte parsers, or subclass
  `VendorAPIRingSource._fetch()`; offline buffering/queue-flush; device health (battery, signal)
  + "ring status" chip. **Spec request sheet (8 questions):** service/characteristic UUIDs per
  metric, byte format/endianness/units, sampling rate, raw sleep periods vs aggregate hours,
  battery service, pairing PIN/bonding, app-local BLE vs vendor cloud, cloud REST endpoints/auth/
  rate limits/raw HR-HRV availability.
- **M2 — Live vitals + automatic safety pipelines:** WebSocket live vitals to psych dashboard;
  auto-discrepancy on journal save; biometric crisis triggers **sustained stress > 80,
  HR > 130, HRV < 20** with cooldown "to avoid alert spam".
- **M3 — Pilot readiness (target Sept 2026, 30 rings):** pair-onboarding UX (code/QR), device
  registry + uptime/battery, dedup/gap/backfill, Docker Compose `ring-bridge` service, token
  rotation/revocation tooling, E2E simulated stream → discrepancy → crisis.
- **Security notes:** tokens SHA-256 hashed at rest + constant-time compare; "A ring never holds
  a patient password"; revocation immediate; vendor cloud creds in bridge config, never DB.
- **Open questions before M1:** which Jport interface; full UUID map or only vendor app; raw
  signals vs aggregated wellness scores; bridge location (clinic LAN gateway vs user's phone).

---

## 2. Paper §9 immediate roadmap (September 2026) `[REPO]`

1. **Live-timing validation of crisis escalations against real email/SMS delivery** (current
   evidence is compressed-time only, TIME_FACTOR=20).
2. **IRB-approved clinical validation with 30 subjects** comparing automated classification
   against clinician assessment ("the next milestone is an ethics-board-approved pilot with 30
   subjects (September 2026)").
3. **A companion mobile application** for journal entry and wearable synchronization.
4. **Calibration-then-select** on the emotion classifier (motivated by the H4 negative result).
5. **Cycle- and sleep-aware baselines** from acquired tiered datasets.
6. **Long-term: turnkey deployment** — "a preloaded mini-PC, LAN connectivity, clinician
   credential configuration".

Human closing: *"Software that reduces neither the clinician's burden nor the patient's
isolation is incomplete."*

---

## 3. Research roadmap (`docs/research/`) `[REPO]`

- Phase 5 deliverables: runnable scripts + CSV logbook; reliability curves, per-class F1,
  decision-flip matrix, precision-recall vs tau; Master manuscript (Phase 10) + IRIS adaptation
  (Phase 11).
- `DATASETS_TRAINING_PLAN.md` 5-step training path: per-user "expected today" distributions →
  sleep-debt residual → mood–physiology discrepancy validated against the 23-case golden set →
  seasonality → cycle-aware `SimulatedRing` profiles. Status: **RESEARCH — no data downloaded,
  no code written**; gated access (PhysioNet DUA, All of Us Workbench, RADAR-MDD) incomplete;
  WHOOP raw never training rows.
- **Unresolved readiness gate:** "can the experiment script load GoEmotions test split locally
  (network/disk)? — Phase 6/7 setup will confirm" (unchecked).
- `IRIS/phase13_claim_audit.md` outstanding non-science items: Render deploy action; "Prep
  materials (proposal/PDF/demo) still quote the OLD pre-audit '96%' framing … PDFs need
  regeneration".

---

## 4. Business / GTM roadmap `[REPO]`

From `docs/business/pitch_deck_content.md` Slide 09/10 and `docs/hosting-plan.md`:
- **GTM Phase 1:** 1–3 clinicians, 20–50 patients. **Phase 2:** 5–10 clinicians, 100–300
  patients. **Phase 3:** 20+ clinicians, 500+ patients.
- **"The Ask":** "Seeking mentorship and domain expertise to stress-test Sentinel's clinical
  workflow, commercialisation strategy, pricing, and deployment model." Mentors wanted:
  clinical (psychiatry/clinical psychology), healthcare commercialisation, pilot clinics,
  hardware/OEM partners. "The next validation stage is a clinical workflow pilot with real
  clinicians and patients. **Sentinel is ready for it.**"
- **Pricing (working hypothesis):** one-time deployment ₹9,999–19,999 / $399–799; clinic SaaS
  ₹2,499/mo + ₹999 maintenance (≈$198/mo combined ₹3,498); patient subscriptions
  ₹499–1,499/mo / $29–79; ring/HaaS ₹1,499/mo; BYOD ₹999; reference unit economy
  **≈₹40,948/mo recurring per 50-patient clinic at >70% gross margin**.
- **Reference deployment costs:** mini-PC (Pi 5 / Intel N100) ≈$200; cloud VM ≈$15/mo; domain
  ≈$8–10/yr; managed PG free–$25/mo; Groq "cents/month"; "no license fee; Tier 3 AI is built
  in. The primary ongoing cost is clinician review… 5–10 min/patient/week".
- **Interim pilot (hosting-plan §0):** "laptop as server + Cloudflare Tunnel" — "**This proves
  the product; it is not the production deployment.**"

---

## 5. SWOT strategic roadmap (`docs/business/SENTINEL_SWOT_AND_STRATEGY.md`) `[REPO]`

- **Milestone name:** "**SENTINEL PILOT-READY v1** — Not: Sentinel Product v1. Because the goal
  is not to prove a healthcare company exists. The goal is to prove one thing: Does Sentinel's
  longitudinal multimodal synthesis provide clinicians with information that is genuinely
  useful?"
- **Action Plan (4 phases):** protect system / pilot-ready data architecture / reproducible
  research / pilot.
- **Gate:** "**Decide whether physiology adds value — If no → kill ring. If yes → continue.**"
- **Opportunities:** own the clinical intelligence layer ("sit above existing infrastructure"),
  integrate instead of replace, governed longitudinal dataset, patient-specific baselines,
  clinician feedback learning loop, four-model experiment (M1–M4), "**Evidence-based
  escalation — transform 'AI says risk' into 'AI surfaces evidence-governed signal with context
  and uncertainty'**", regulatory readiness as moat, India as strategic starting market.
- **Moat (if earned):** clinical evidence / governed longitudinal dataset / clinician feedback
  dataset. "**Don't touch yet**": native mobile app, ABHA/ABDM, ring manufacturing, PHQ-9/GAD-7.
- **Current scores:** technical 8/10, research 9/10, clinical validation 2/10, business
  readiness 3/10, regulatory 3/10, hardware 2/10.

---

## 6. Engineering "unlimited resources" list (status as recorded) `[REPO]`

| Item | Status |
|---|---|
| Argon2id | **DONE** (2026-09-09) |
| Redis pub/sub | **SOLVED WITHOUT REDIS** (PG LISTEN/NOTIFY) |
| PostgreSQL | **DONE** (psycopg2, RUN_WORKERS, scaled profile, PG 17) |
| Alembic | **DONE** (head `9f3e2a1b7c4d`) |
| **Refresh tokens** with HttpOnly cookie | **OPEN** |
| Rate limiting | **PARTIAL** (memory\|db shipped) |
| CSP headers | **DONE** |
| **Per-patient crisis states** | **OPEN (critical path for the pilot)** — but `f75600b` shipped per-patient rows; doc/code lag |
| **Chart.js / D3 biometric trends** | **OPEN** |
| CI pipeline | **DONE** (6 jobs incl. golden-gate `--strict`) |

Other known OPEN/TODO: ~8 open TODOs (logbook); `JUDGE_QA.md` I future work: per-patient crisis
states, labelled corpus, companion mobile app; "no formal certification" (IEC 62304, ISO 13485,
ISO 14971); session revocation/MFA; SBOM; DB-file-level encryption before real pilot data;
ethical exit path; dynamic informed consent; non-English sentiment support.

---

## 7. Cloud / networking / data infrastructure evolution `[REPO][SESSION]`

- Original: Docker Compose local + Render cloud blueprint.
- Interim: laptop + Cloudflare Tunnel.
- Research/analysis: **AWS India Lightsail (US region + CloudFront)** — "most defensible global +
  UPI"; analysed, **not adopted**.
- **Adopted 2026-11-16:** GoDaddy `.com` (`sentinelpsytech.com`) + Hostinger India VPS KVM 1,
  UPI, Caddy TLS, managed firewall, key-only SSH, single SQLite bind mount.
- Later options recorded: Hostinger free CDN (Sydney PoP closest to NZ) for India + NZ latency;
  Cloudflare free CDN; upgrade VPS anytime; port local `sentinel3` changes into the live
  `sentinel-mental-health` repo (still pending — see `15`).

---

## 8. Unexplored / speculative opportunities (ideas only) `[REPO][INFERRED]`

- Camera-based PPG phone app (JUDGE_QA idea).
- Multi-sensory / "sensory room" environment (`ROADMAP_HARDWARE.md` M3 mention; Streamlit-era
  `smart_room_.py` ambient visualisation).
- Clinician self-monitoring / burnout dashboard (described in proposals, no dedicated build).
- `fieldcrypt` as a standalone MIT package (done, 1 commit 2026-09-20).
- Secure Transport Layer (E2EE+PFS, zero-metadata routing) — designed, never built.
- ABHA/ABDM integration, PHQ-9/GAD-7 standard instruments (explicitly deferred).
- Ring-as-a-service subscription for clinic-provisioned rings.
- Companion mobile app with background wearable sync (browser limits make PWA insufficient).

---

## 9. Original roadmap vs later changes (side by side)

| Topic | Original (M0–M3 / paper §9 / hosting-plan) | Later (Nov 2026 working sessions) |
|---|---|---|
| Hardware | Jport OEM ring, vendor SDK/BLE, M1–M3 | **Viaking R30 PRO** actually reverse-engineered; YCBT protocol recovered; real measurements ingested; custom PCB/3D path abandoned |
| Ring source | SimulatedRing + VendorAPIRingSource + BLEGATTRingSource | **SimulatedRing deleted**; real hardware + browser Web Bluetooth path |
| Deployment | mini-PC / Render / Cloudflare Tunnel / AWS analysis | **Hostinger VPS + GoDaddy domain, UPI, Caddy, live HTTPS** |
| AI | local Ollama → Groq → rule; own model "still in training" | `ALLOW_CLOUD_AI=false`, blank Groq key left for co-founder; offline/rule fallback accepted |
| Vitals UI | Wearable Vitals card only when data exists | **Always-visible card with dashes, last-synced nudge, reading count** |
| Psych wearables | view assigned patients' vitals | **psych's OWN ring / self-care space** (`WearablesPage`) |
| Data | demo/simulated vitals acceptable for demo | **no simulations; 14 real hardware rows; unmeasured → NULL/dash** |
| Clinical validation | 30-subject Sept 2026 IRB pilot | still specified, not recorded executed |

---

## 10. Gaps `[UNKNOWN]`

- Whether M1–M3 were executed with Jport, or a spec sheet was ever delivered: not recorded.
- Whether the Sept 2026 30-subject pilot occurred: not recorded.
- Exact future dates beyond those in the documents: none exist; nothing invented here.
- Final live VPS region (Malaysia/Indonesia vs Boston) not recorded.
