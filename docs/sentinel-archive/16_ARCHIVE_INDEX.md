# 16 — ARCHIVE INDEX AND COMPLETENESS CHECK

*Full index, cross-references, source inventory, and the final completeness verification for
`docs/sentinel-archive/`. Compiled 2026-11-16.*

---

## 1. Document map with links

| # | File | Covers | Status |
|---|---|---|---|
| 00 | [`00_COMPLETE_PROJECT_ARCHIVE.md`](00_COMPLETE_PROJECT_ARCHIVE.md) | Master: provenance rules, redaction policy, one-paragraph identity, the no-fabrication principle, document map, source inventory, conflicts, completeness statement. | ✅ |
| 01 | [`01_ORIGIN_AND_VISION.md`](01_ORIGIN_AND_VISION.md) | Inspiration, motivation, problem evolution, vision, ambition, stakeholders, human authority, ethics, privacy, "should/never become", difference from apps/chatbots, AI-locality conflict. | ✅ |
| 02 | [`02_PROJECT_HISTORY.md`](02_PROJECT_HISTORY.md) | Chronology: pre-git hardware → Streamlit → FastAPI/React → security → docs → crisis/PWA/M0 → red-team → research → UI eras → scale/security → Nov 2026 working sessions. | ✅ |
| 03 | [`03_PRODUCT_PHILOSOPHY.md`](03_PRODUCT_PHILOSOPHY.md) | Product principles, UX philosophy, clinical workflow, human-centred design, trust/safety/accessibility/continuity, patient/clinician experiences, feature rationale, boundaries. | ✅ |
| 04 | [`04_SYSTEM_ARCHITECTURE.md`](04_SYSTEM_ARCHITECTURE.md) | Constitution, layers, containers, data flow, 3-tier AI, deterministic engines, storage, networking, 4 deployment topologies, multi-worker scaling, security architecture, proposed/abandoned. | ✅ |
| 05 | [`05_TECHNICAL_IMPLEMENTATION.md`](05_TECHNICAL_IMPLEMENTATION.md) | Stack/versions, backend/frontend structure, APIs, AI/ML, auth/security/privacy, hardware/BLE, testing, deployment, performance, implemented/proposed/abandoned separation. | ✅ |
| 06 | [`06_RESEARCH_ARCHIVE.md`](06_RESEARCH_ARCHIVE.md) | Programme, RQs, hypotheses/nulls, literature L1–L13, flaws F1–F5, experimental design, E1–E4 results, negative result, dataset plan, papers, uncertainties, future research. | ✅ |
| 07 | [`07_DESIGN_AND_PRODUCT_DECISIONS.md`](07_DESIGN_AND_PRODUCT_DECISIONS.md) | 50-row master decisions, UI/theme eras, feature rationale, product boundaries/"not" statements, licensing conflicts, never-implemented ideas. | ✅ |
| 08 | [`08_HARDWARE_AND_EXPERIMENTS.md`](08_HARDWARE_AND_EXPERIMENTS.md) | 3D→PCB attempt, KiCad failure, OEM pivot, KiCad stubs, Viaking R30 PRO identity, YCBT protocol, every measured signal, failures, 0xFE fix, first successful live integration, ECG, errors, scripts/artifacts, forbidden ops. | ✅ |
| 09 | [`09_DECISION_HISTORY.md`](09_DECISION_HISTORY.md) | D1–D11 direction decisions, E1–E18 engineering decisions, UI decisions, rejected/abandoned decisions, constraints, validity review. | ✅ |
| 10 | [`10_VALIDATION_AND_EVIDENCE.md`](10_VALIDATION_AND_EVIDENCE.md) | Evidence classes, test-count history, benchmarks, live HTTPS verification, first hardware integration evidence, research validation, red-team evidence, what is NOT validated. | ✅ |
| 11 | [`11_FUTURE_VISION_AND_ROADMAP.md`](11_FUTURE_VISION_AND_ROADMAP.md) | Original M0–M3 roadmap, paper §9, research roadmap, business/GTM, SWOT roadmap, unlimited-resources list, cloud evolution, unexplored opportunities, original vs later side-by-side. | ✅ |
| 12 | [`12_DEVELOPMENT_HISTORY.md`](12_DEVELOPMENT_HISTORY.md) | Implemented/partial/planned features, ~45-row bug/debugging history, technical debt, key files, git history (73 commits, eras), working-tree state. | ✅ |
| 13 | [`13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md`](13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md) | No-fabrication rule, no clinical conclusions, BLE constraints, privacy-first, human authority, honesty, architecture, operational, licensing constraints. | ✅ |
| 14 | [`14_FOUNDER_WORKING_PREFERENCES.md`](14_FOUNDER_WORKING_PREFERENCES.md) | Project-relevant thinking: problem-solving, decision-making, architecture/research/implementation preferences, AI-assisted development, explanation expectations, shortcut concerns, ethics/privacy/quality priorities, preserved quotes. | ✅ |
| 15 | [`15_UNRESOLVED_QUESTIONS.md`](15_UNRESOLVED_QUESTIONS.md) | Open engineering/research/clinical/hardware/deployment/product items + 18 archive gaps + how to extend. | ✅ |
| 16 | `16_ARCHIVE_INDEX.md` (this file) | Index, cross-references, source inventory, completeness check. | ✅ |

**All 17 requested files exist.** The master (`00`) links to every detailed document via §4. Every
detailed document references `00` for provenance rules and, where relevant, cross-links siblings.

---

## 2. Requirement → coverage cross-reference

| User requirement | Where covered |
|---|---|
| §1 Original vision and identity (inspiration, problem evolution, vision, ambition, users, clinician/tech relationship, human authority, ethics, privacy, should/never become, difference from apps/chatbots, original reasoning) | `01`, plus `03`, `13` |
| §2 Complete project history (chronological, versions, features, challenges, breakthroughs, experiments, validation discussions, collaborations, milestones, direction changes, current state, dates) | `02`, `12` |
| §3 Complete technical knowledge (architecture, frontend, backend, APIs, DB, storage, AI/ML, processing, auth, security, privacy, hardware, BLE, sensors, protocols, testing, deployment, dependencies, infrastructure, performance, scalability; actual vs proposed vs abandoned separated) | `04`, `05`, `08` |
| §4 Research (questions, formulations, hypotheses, literature, approaches, gaps, experiments, findings, unresolved, future, papers, why pursued/abandoned, uncertainty & disagreement) | `06`, `15` |
| §5 Design philosophy & product thinking (principles, UX, clinical workflow, human-centred, explainability, trust, safety, accessibility, continuity, patient/clinician experiences, rationale, boundaries, ideas never implemented) | `03`, `07` |
| §6 Hardware & experimental records (specs, identification, sensors, BLE exploration, connection attempts, GATT, raw observations, data, tests, errors, limitations, integration architecture, future plans; first successful test evidence; actual vs simulated vs assumed separated) | `08`, `10` |
| §7 Decisions & reasoning (what/when/why/alternatives/trade-offs/constraints/validity/implemented; rejected too) | `09`, `07` |
| §8 Development/implementation record (implemented/partial/planned, experiments, bugs, debugging, tech debt, tests, limitations, key files/modules, git history; never unverified-as-working) | `12`, `05`, `10` |
| §9 Future vision & roadmap (immediate, versions, long-term, hardware, cloud, data, scalability, clinical validation, research, integrations, unexplored; original vs later separately) | `11` |
| §10 Founder thinking & working philosophy (project-relevant only) | `14` |
| §11 Create all 17 files | ✅ all present |
| §12 Preservation rules (accessible history, full repo, existing docs, git, terminology, reasoning, outdated marked, conflicts kept, confirmed/historical/inferred/unknown labels, no invention, no credentials, raw evidence, no code changes) | `00` §0 + all files |

---

## 3. Source inventory (everything inspected)

### 3.1 Repositories / project folders on this machine `[REPO]`

| Path | Relation | Git |
|---|---|---|
| `sentinel3/` | Main working repo; all Nov 2026 work lives here | ✅ 73 commits, origin `Sentinel_V_1_.git` |
| `Sentinel_V_1_/` | Older checkout of the **same** origin (71 commits); has Azure deploy files | ✅ |
| `sentinel-mental-health` | Actively developed/deployed repo (Render live app) | remote, **not on disk** `[UNKNOWN]` |
| `Sentinel__/` | KiCad PCB stubs (May 2026) | `.history` only |
| `fieldcrypt/` | Standalone MIT library extracted from Sentinel's field-level AEAD encryption | ✅ 1 commit (2026-09-20) |
| `sentinel3/archive/` | Retired Streamlit prototype source + founder notes | inside `sentinel3` |
| `sentinel3/kiot/` | Incubation-centre document pack (14 PDFs + index + LICENSE) | inside |
| `sentinel3/IRIS/`, `sentinel3/IRIS_2026_SENTINEL/` | Science-fair manuscripts / submission packs | inside |
| `sentinel3/docs - Copy/` | Older docs snapshot | inside |
| `sentinel3/hardware_lab/` | BLE lab (EXPERIMENTAL) | inside |
| `sentinel3/deploy/` | Production VPS runbook/config | inside (untracked) |
| `boost/` (Desktop) | `research_paper.md` 3D/PCB draft template | ❌ |
| `research/ids-distribution-shift/` (Desktop) | Related distribution-shift research | ✅ separate |
| `TKS/`, `portfolio/`, `derive/`, `noted/`, `boards/`, `10-b/`, `Association Team/`, `un policy/`, `research os/`, `github/` (11 networking repos), `dhka log/` | Other projects, mostly unrelated | mixed |

### 3.2 Key documents read `[REPO]`
`README.md`, `SENTINEL_CODEBOOK.md`, `LICENSE`, `concerns.md`, `proposal.md`, `render.yaml`,
`docker-compose.yml`, `.env.example` (**key names only**), `docs/TECHNICAL_DESIGN.md`,
`docs/ENGINEERING_LOGBOOK.md`, `docs/ENGINEERING_DECISIONS.md`, `docs/JUDGE_QA.md`,
`docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/SECURITY_AUDIT.md`,
`docs/ROADMAP_HARDWARE.md`, `docs/sentinel_paper.md`, `docs/hosting-plan.md`,
`docs/pitch.md`, `docs/new_pitch.md`, `docs/executive_summary.md`, `docs/proposal_*.md`,
`docs/business/*` (3 files), `docs/research/*` (6 files), `hardware_lab/*.md` (7 files),
`deploy/DEPLOY.md`, `scripts/sentinel_prompt.md`, `kiot/00_DOCUMENT_INDEX.md`,
`kiot/11_Team_and_Credentials.md`, `IRIS/manuscript_phase10.md` (head),
`boost/research_paper.md` (3D/PCB section), `fieldcrypt/README.md`.

### 3.3 Code / artifacts inspected `[REPO]`
Full `backend/app/` module tree (34 core, 29 api, 21 models, 17 schemas, 13 services, 5
repositories, 5 ml, 4 workers), `frontend/src/` tree (29 pages, 13 components, `ring/*`, `api/*`,
`stores/*`), `backend/requirements.txt`, `frontend/package.json`, `frontend/Dockerfile`,
`frontend/nginx.conf`, `frontend/public/sw.js`, `frontend/public/manifest.webmanifest`,
`hardware_lab/` 30 `.py` scripts + `out/` 39 evidence artifacts (24 `.json`, 14 `.jsonl`, 1
`.csv`), `Sentinel__/` KiCad files, `deploy/*`.

### 3.4 Git history `[GIT]`
`git log --all --date=short --pretty=format` for `sentinel3` (73 commits) and `Sentinel_V_1_`
(71). `git remote -v`, `git branch -a`, `git status --short`.

### 3.5 Conversation record `[SESSION]`
The accumulated checkpoint/memory of the project and all recent working sessions: the BLE lab,
simulation removal, comparison wiring, Web Bluetooth, hosting/domain procurement, live
deployment, demo accounts, empty-vitals UX fix, psych self-care correction, PWA discussion,
preserved verbatim quotes in `14`.

### 3.6 Material deliberately NOT reproduced (existence/location only) `[REPO]`
Root `.env`, `.env.example` values, `SECURITY_AUDIT.md` credential values, demo/seed passwords in
`README.md`, `SENTINEL_CODEBOOK.md`, `archive/FOUNDERS_GUIDE.md`, `archive/answers.md`,
`archive/software/ACCOUNTS.md`, `archive/software/data/.encryption_key`, personal phone number
in `proposal.md` / `docs/proposal_sports_psychologist.md`, founder contact email in
`docs/business/pitch_deck_content.md`, `LICENSE`, `IRIS_2026_SENTINEL/06_VIDEO/Video_Script.md`,
the paper author's correspondence email, the SSH deploy private key, the dev JWT secret,
`archive/thoughts/sentinel.txt` (private chat transcript with apparent credentials / session
token / seed phrase), `archive/thoughts/30,08,2026.txt` (private reflective writing), 14
WhatsApp images. **No values from these appear in any archive file.**

---

## 4. Provenance label usage (audit)

Labels defined in `00` §0: `[REPO]`, `[GIT]`, `[SESSION]`, `[INFERRED]`, `[UNKNOWN]`,
`[HISTORICAL]`, `[CONFLICT]`. Used throughout. Confirmed facts are never presented as inference;
unverified implementations are labelled (e.g. Web Bluetooth "implemented, NOT hardware-verified"
in `05` §10, `10` §8). Outdated information is marked `[HISTORICAL]` rather than deleted (test
counts, palettes, pitch variants, "96%", "$0 cost", "teen" framing). Conflicting versions are
kept (AI locality, crisis framing, licensing, region, discrepancy constants, per-class tables,
E4 tau tables, Python version, PostgreSQL stance). Dates are only given where recorded; none
invented.

---

## 5. Final completeness check results

- ✅ **All 17 files present** (verified below by filesystem listing).
- ✅ **Master links to all detailed documents** (`00` §4, this file §1).
- ✅ **No missing required section**: every user §1–§12 requirement has coverage (§2 table above).
- ✅ **No credentials / API keys / tokens / passwords / sensitive patient data** reproduced.
- ✅ **No application code modified**: the archive only added files under `docs/sentinel-archive/`.
  (The workspace already had ~30 modified files + untracked work from earlier sessions; those
  were left untouched.)
- ✅ **Historical information that could not be accessed** is enumerated in `15` Part B (18
  numbered gaps) and `11` §10, `12` §8, `08` Part C, `06` §13, `01` §10, `04` §11, `05` §11,
  `07` §8, `09` §7, `10` §9, `13` §10, `14` §11.
- ✅ **Areas where the archive may be incomplete** are flagged `[UNKNOWN]` / `[INFERRED]`
  throughout and summarised in `15`.

### 5.1 Verified file listing

Run at compile time: `Get-ChildItem docs/sentinel-archive` → 17 `.md` files. See the tool output
recorded in the conversation at archive completion.

---

## 6. Navigation suggestions

- **New reader:** `00` → `01` → `02` → `03`.
- **Engineer:** `04` → `05` → `12` → `10`.
- **Researcher:** `06` → `10` → `11` → `15`.
- **Hardware:** `08` → `13` → `09` (D1/D4) → `15`.
- **Decisions:** `09` → `07` → `13`.
- **Founder context:** `14` → `01`.
- **"What's still open":** `15`.
- **"What changed / what was abandoned":** `02` §11, `07` §4, `09` §4, `11` §9.

---

*End of archive index. This directory is Sentinel's institutional memory: origin, vision,
research, technical evolution, decisions, experiments, philosophy, constraints, founder working
preferences, validation evidence, future possibilities, and unresolved questions — preserved
with depth, accuracy, and explicit honesty about what is known, what is historical, what is
inferred, and what is unknown.*
