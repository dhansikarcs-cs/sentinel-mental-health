# SENTINEL — COMPLETE PROJECT ARCHIVE

**Purpose.** This directory is the permanent institutional memory of Sentinel: its origin,
vision, research, technical evolution, decisions, hardware experiments, philosophy,
founder working preferences, validation evidence and future possibilities. It is written so
that the complete story exists outside any AI agent's memory.

**Compiled:** 2026-11-16. **Scope:** the `sentinel3` working repository, its sibling
repositories/folders on the same machine, the project's documentation and research corpus,
its git history (73 commits in `sentinel3`), the hardware lab records, and the accumulated
working-conversation record of the project.

**This is NOT** a handoff, migration, onboarding document, or a task list for another agent.
It is a historical and knowledge-preservation record.

---

## 0. How to read this archive — provenance labels

Every substantive claim is tagged so that confirmed fact is never confused with memory,
inference, or speculation.

| Label | Meaning |
|---|---|
| `[REPO]` | Verified directly from repository files, code, or documentation on disk. |
| `[GIT]` | Verified from git history (`git log`, commit hashes and dates). |
| `[SESSION]` | From the accumulated working-conversation record of the project (the checkpoint/memory and recent working sessions). Trustworthy as project history, but not independently re-verifiable from files. |
| `[INFERRED]` | Reasoned from other facts; not a direct claim. |
| `[UNKNOWN]` | Not accessible at compile time; explicitly flagged as a gap. |
| `[HISTORICAL]` | True at an earlier point, later superseded. Kept, not deleted. |
| `[CONFLICT]` | Two versions of a claim exist in the record; both preserved. |

**Redaction policy.** No credentials, API keys, tokens, JWT secrets, private keys, account
passwords, or sensitive personal/patient data appear in this archive. Where such values are
known to exist (e.g. a local SSH deploy key, demo-account passwords, monitoring/API keys),
this archive notes their *existence and role* but never reproduces the value. Demo accounts
are described by role and username only. This is deliberate and applies to all 17 files.

**Confidence rule for implementations.** Nothing is described as "working" or "validated"
unless the record contains explicit verification. Partially implemented, unverified, or
abandoned work is labelled as such (see `08_HARDWARE_AND_EXPERIMENTS.md`,
`10_VALIDATION_AND_EVIDENCE.md`, `15_UNRESOLVED_QUESTIONS.md`).

---

## 1. The project in one paragraph

Sentinel is a **mental-health support platform** that pairs private journaling with an AI
companion, real-time emotion scoring, and automatic crisis detection, all feeding a clinician
triage and admin oversight layer that keeps sensitive AI work safe, auditable, and
production-ready. `[REPO][SESSION]` The approved one-line description (kept verbatim because
the founder approved the exact wording) is:

> "Sentinel is a mental-health support platform that pairs private journaling with an AI companion, real-time emotion scoring, and automatic crisis detection, all feeding a clinician triage and admin oversight layer that keeps sensitive AI work safe, auditable, and production-ready."

The founder explicitly rejected describing it as a "teen" product; the correct framing is a
general mental-health support platform. `[SESSION][HISTORICAL]` (Earlier "teen" framing was
superseded — see `01_ORIGIN_AND_VISION.md` and `09_DECISION_HISTORY.md`.)

---

## 2. The single most important principle

**No fabricated physiology.** Every number shown in Sentinel must be a real measurement from
a physical wearable. Nothing is invented, derived, defaulted, or simulated. Unmeasured
signals stay NULL / render as a dash. The founder's explicit instruction: "don't calculate
stuff like hrv from bpm", and later "take all simulations away". `[SESSION][REPO]`

This principle drove: deletion of the simulated ring source, removal of hardcoded defaults
(e.g. `temperature=36.5`), removal of derived values (e.g. `sdnn = hrv*0.8`), purging of
fake seeded vitals rows, and the server-side journal↔vitals comparison that reads only real
stored rows. It is documented across `03_PRODUCT_PHILOSOPHY.md`,
`05_TECHNICAL_IMPLEMENTATION.md`, `08_HARDWARE_AND_EXPERIMENTS.md`, and
`13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md`.

---

## 3. What the project is, at a glance `[REPO][GIT][SESSION]`

- **Current working repo:** `sentinel3` (origin `Sentinel_V_1_.git`), 73 commits,
  2026-05-12 → 2026-10-03 (git); plus extensive uncommitted work from later sessions.
- **Architecture:** FastAPI + SQLAlchemy backend (29 API router modules, ~120 routes),
  React 19 + TypeScript + Vite frontend, SQLite (single node) or PostgreSQL 17 (scaled),
  served behind nginx/Caddy reverse proxy, containerised with Docker Compose.
- **AI:** three-tier pipeline (local Ollama → Groq cloud opt-in → deterministic rule
  fallback); TF-IDF + logistic-regression GoEmotions emotion classifier; rule-based
  discrepancy engine; data-driven crisis policy; dual-mode (patient companion /
  clinician OAP) summaries; plain-English clinician insights.
- **Hardware:** Viaking R30 PRO smart ring, reverse-engineered YCBT BLE protocol, direct
  Windows BLE → Python → Sentinel ingestion, plus a browser Web Bluetooth path for hosted
  use. Real signals observed: HR, SpO₂, temperature, HRV, BP candidates, raw PPG, battery,
  ECG waveform. Stress/fatigue unsupported by firmware; sleep requires overnight wear.
- **Live deployment (2026-11-16):** `https://sentinelpsytech.com` on a Hostinger VPS,
  production Let's Encrypt TLS via Caddy, key-only SSH, managed firewall, SQLite with a
  persistent bind mount, payable by UPI.
- **Testing/CI:** 222 backend pytest tests, ruff check + format, `tsc -b`, `vite build`,
  6-job GitHub Actions CI, 23-case golden-set gate.
- **Research:** IRIS 2026 / ISEF 2026 / Samsung Solve for Tomorrow context; a research paper
  on calibration and distribution shift in the GoEmotions classifier; incubation-centre
  document pack; a standalone `fieldcrypt` library extracted from Sentinel's encryption.

---

## 4. Document map

| # | File | Covers |
|---|---|---|
| 00 | `00_COMPLETE_PROJECT_ARCHIVE.md` | This file — master, provenance rules, navigation |
| 01 | `01_ORIGIN_AND_VISION.md` | Why Sentinel exists, inspiration, problem evolution, ambition, stakeholders, human-authority philosophy, ethics, boundaries, what it should/never become |
| 02 | `02_PROJECT_HISTORY.md` | Chronological reconstruction, phases, versions, milestones, direction-changing decisions |
| 03 | `03_PRODUCT_PHILOSOPHY.md` | Product principles, UX philosophy, clinical workflow, human-centred design, explainability, trust, safety, accessibility, continuity of care |
| 04 | `04_SYSTEM_ARCHITECTURE.md` | Architecture constitution, layers, containers, data flow, networking, storage, deployment topologies |
| 05 | `05_TECHNICAL_IMPLEMENTATION.md` | Backend/frontend/API/DB/AI/ML/auth/security/privacy/hardware/BLE/testing/deployment/dependencies — implementations vs proposals vs abandoned |
| 06 | `06_RESEARCH_ARCHIVE.md` | Research questions, hypotheses, literature, datasets, findings, negative results, papers, unresolved questions |
| 07 | `07_DESIGN_AND_PRODUCT_DECISIONS.md` | Design decisions, feature rationale, UI/theme evolution, product boundaries, ideas never implemented |
| 08 | `08_HARDWARE_AND_EXPERIMENTS.md` | The 3D→PCB custom-hardware attempt and its abandonment, the OEM pivot, Viaking R30 PRO discovery, all BLE experiments, raw evidence, errors, limitations |
| 09 | `09_DECISION_HISTORY.md` | Decision register: what/when/why/alternatives/trade-offs/validity/implemented — including rejected decisions |
| 10 | `10_VALIDATION_AND_EVIDENCE.md` | Test results, benchmarks, live verification, the first successful hardware integration, evidence classification |
| 11 | `11_FUTURE_VISION_AND_ROADMAP.md` | Original roadmap, later changes, long-term capabilities, hardware/cloud/data/clinical expansion |
| 12 | `12_DEVELOPMENT_HISTORY.md` | Features implemented/partial/planned, bugs, debugging, technical debt, git history, known limitations, key files |
| 13 | `13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md` | Non-negotiable constraints, no-fabrication rule, privacy-first rules, forbidden operations, ethics |
| 14 | `14_FOUNDER_WORKING_PREFERENCES.md` | Project-relevant founder thinking and working preferences (not a personality profile) |
| 15 | `15_UNRESOLVED_QUESTIONS.md` | Open questions, gaps, unknowns, archive incompleteness |
| 16 | `16_ARCHIVE_INDEX.md` | Full index, cross-references, source inventory, completeness check |

---

## 5. Source inventory (what was inspected)

**Repositories / project folders on this machine** `[REPO]`
- `sentinel3/` — main working repo (73 commits). All working sessions' code changes live here.
- `Sentinel_V_1_/` — a second checkout of the *same* origin (71 commits, older HEAD). Not a
  separate project. Contains Azure deployment files not present in `sentinel3`.
- `sentinel-mental-health` — a distinct repository (remote, not on this disk) that the
  README names as the actively developed/deployed codebase and that the Render live app
  deploys from. `[REPO][SESSION][UNKNOWN: not locally accessible]`
- `Sentinel__/` — KiCad project files (custom PCB attempt); contains a `.history` git repo.
- `fieldcrypt/` — standalone git repo (1 commit, 2026-09-20) extracted from Sentinel's
  field-level encryption layer.
- `archive/` — the original Streamlit prototype source, archived inside `sentinel3`.
- `kiot/` — incubation-centre document pack (14 documents + LICENSE).
- `IRIS/`, `IRIS_2026_SENTINEL/` — science-fair manuscripts and submission materials.
- `docs - Copy/` — a snapshot copy of the docs set.
- Other sibling folders on the Desktop (`boost/`, `research/`, `derive/`, `TKS/`, `portfolio/`,
  `boards/`, `10-b/`, `Association Team/`, `noted/`, `un policy/`, `research os/`, `github/`,
  `dhka log/`) — mostly separate projects; `boost/` and `fieldcrypt` contain
  Sentinel-relevant material and are cited where relevant. `research/ids-distribution-shift/`
  is a related but separate research repo. See `16_ARCHIVE_INDEX.md` for the full list.

**Key documents** `[REPO]`: `README.md`, `SENTINEL_CODEBOOK.md`, `docs/TECHNICAL_DESIGN.md`,
`docs/ENGINEERING_LOGBOOK.md`, `docs/ENGINEERING_DECISIONS.md`, `docs/JUDGE_QA.md`,
`docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/SECURITY_AUDIT.md`,
`docs/ROADMAP_HARDWARE.md`, `docs/sentinel_paper.md`, `docs/research/PHASE*.md`,
`docs/business/*`, `docs/hosting-plan.md`, `concerns.md`, `hardware_lab/*.md`,
`deploy/DEPLOY.md`, `render.yaml`, `docker-compose.yml`, `.env.example`, `LICENSE`,
`proposal.md`, `docs/pitch.md`, `docs/new_pitch.md`, `docs/executive_summary.md`.

**Conversation record** `[SESSION]`: the accumulated checkpoint/memory of the project plus
the recent working sessions covering hosting/domain procurement, the Viaking R30 PRO BLE
lab, simulation removal, the journal↔vitals comparison, Web Bluetooth for hosted use,
PWA discussion, account creation, the empty-vitals UX fix, and the final live deployment.
This is a first-class source; where it conflicts with on-disk docs, both are preserved.

---

## 6. Known conflicts and superseded positions (kept, not resolved)

- Product description: earlier "teen" framing `[HISTORICAL]` vs approved "mental-health
  support platform" `[CURRENT]`. `[CONFLICT]`
- Hardware strategy: build a custom ring `[HISTORICAL, abandoned]` vs bring-your-own-device
  consumer wearables `[CURRENT]`. `[CONFLICT]`
- Hosting: AWS India Lightsail was the "most defensible global + UPI" analysis `[SESSION]`,
  but the founder rejected AWS and the project was actually deployed on Hostinger India
  VPS `[CURRENT]`. `[CONFLICT]`
- VPS region: Boston/US initially shown in the panel `[HISTORICAL]` vs the later
  recommendation of Malaysia/Indonesia for an India + New Zealand audience `[SESSION]`.
  The final chosen region is not recorded in this archive. `[UNKNOWN]`
- Psychologist wearables: an "assigned patient → psychologist vitals view" was built
  `[HISTORICAL, later reframed]` vs the corrected "psychologist has their OWN ring/self-care
  space" `[CURRENT]`. `[CONFLICT]`
- Colour/theme: multiple palette eras (dusk-slate → rose-mauve → sage → light therapeutic
  calm → user-selectable light/dark). All preserved in `07`. `[HISTORICAL]`
- Data: the original simulated ring and seeded fake vitals `[HISTORICAL, removed]` vs
  "real measurements only" `[CURRENT]`. `[CONFLICT]`

---

## 7. Completeness statement

This archive was built by reading the full on-disk doc corpus, the code tree, git history,
hardware lab artifacts, sibling repos, and the working-conversation record. Areas that could
not be fully recovered are listed in `15_UNRESOLVED_QUESTIONS.md` and `16_ARCHIVE_INDEX.md`.
Nothing was invented to fill gaps. Per the preservation rules, no application code was
modified during archiving; the archive only adds files under `docs/sentinel-archive/`.
