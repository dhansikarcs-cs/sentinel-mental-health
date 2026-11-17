# 07 — DESIGN AND PRODUCT DECISIONS

*Design decisions, feature rationale, UI/theme evolution, product boundaries, and ideas
discussed but never implemented. Distinguishes decided / implemented / rejected / historical.*

---

## 1. Master decisions table (from `docs/ENGINEERING_DECISIONS.md`, 50 numbered rows) `[REPO]`

| Area | Decision | Why | Alternatives rejected | Trade-off |
|---|---|---|---|---|
| Auth | Argon2id password hashing | OWASP; transparent legacy bcrypt re-hash | bcrypt (retained as fallback) | CPU cost |
| Auth | HS256 JWT, 8-hour expiry, no refresh tokens | Simple, offline-capable | RS256 (needs key management); refresh tokens (OPEN) | 8h re-login |
| Auth | 5 failures → 15-min lockout | Brute-force defence | Progressive delay ("known simplification") | No progressive delay |
| Auth | Two-factor model = password + **encryption unlock** (separate PBKDF2 key) | "cryptographically independent" | Direct AES-GCM stored key; OAuth2/OIDC ("unacceptable for a clinic that may operate offline") | Passphrase loss = unrecoverable |
| Crisis | Thread-based 3-stage countdown at 20× compression | No broker; deterministic | AsyncIO, Redis scheduled tasks, Celery | TIME_FACTOR simulation |
| Crisis | Singleton crisis state → per-patient rows | Multi-patient correctness | — | Docs still list OPEN (doc/code lag) |
| Discrepancy | Rule-based, zero ML | "A false negative in a triage pipeline is lethal" | TF-IDF+LR (28 noisy probabilities, 4 MB pickle) | Sarcasm/clinical jargon blind spots |
| Encryption | Fernet (AES-128-CBC + HMAC-SHA256) | 4 bundled operations | Raw AES-GCM; scrypt (variable latency); Argon2id for KDF (retained PBKDF2 for deterministic serial behavior) | 128-bit not 256-bit |
| Encryption | PBKDF2 600,000 iterations + HKDF-Expand | NIST SP 800-132 100–300 ms band | — | ~154.8–233.2 ms derive |
| Storage | SQLite WAL | ~4 MB idle, no DBA, one `cp` backup | PostgreSQL (later added for multi-worker); JSON (original); NoSQL (relational data + cloud dependency) | Single-writer |
| Storage | String ISO timestamps | Portable | — | — |
| AI | Ollama local primary (7.2B, ~8 GB) | Zero data leaves clinic | Cloud-first | Cold ~15 s |
| AI | 3-tier fallback (Ollama → Groq → rule) | Graceful degradation | — | Rule outputs truncated, not hallucinated |
| AI | Dual-mode summarization (companion / OAP clinical) | Two readers, two voices | Single-voice | — |
| AI | Regex JSON extraction | Defensive parsing | — | — |
| Audit | SHA-256 hash-chained log | Tamper-evident | Proper blockchain (consensus/mining) | "Not tamper-proof" |
| Frontend | React 19 + TS + Vite 6 | Type safety ("caught 7 type-level bugs, ~3 h saved") | Streamlit, Next.js, Web Components | Build step |
| Frontend | Custom pub/sub auth store (~50 lines) | Minimal | Redux (100+ lines), Context API (re-renders), Zustand | — |
| Frontend | Emoji icons, no icon/chart/state library | 56 KB (34 KB gzip) bundle | lucide, Chart.js/D3 | No charts (OPEN) |
| Frontend | Encryption Unlock Gate | Fail-closed UI | — | Extra step |
| Deploy | Docker Compose (local) + Render (cloud) | Two commands; auto-deploy | — | Free-tier cold starts |
| Deploy | Non-root `USER sentinel` (UID 1001), internal network | Pen-test fixes | root containers | — |
| Deploy | Multi-stage Node → nginx (20 MB image) | Small | — | — |
| Hardware | Per-device token auth (`X-Device-Serial` + `X-Device-Token`) | Device binding | — | Token rotation tooling |
| Hardware | Pluggable `RingSource` adapters + canonical `SensorData` | HAL: adding a device never touches engines/dashboards | — | Vendor spec still needed |
| Hardware | Deterministic `SimulatedRing` | Deterministic CI | — | "must not be mistaken for real patient data"; **later removed** `[SESSION]` |

**"Key Defensible Positions (For Judges)"** `[REPO]`: "A deterministic system with 100% auditable
accuracy is safer than a probabilistic system with 94% accuracy when false negatives are
lethal"; SQLite on a ~$200 mini-PC; local AI over cloud; custom auth over OAuth2; threads over
tasks.

**"What Would You Do Differently With Unlimited Resources?"** `[REPO]`: DONE = Argon2id,
Redis pub/sub (solved WITHOUT Redis via PG LISTEN/NOTIFY), PostgreSQL, Alembic, CSP headers, CI
pipeline; PARTIAL = rate limiting (memory|db shipped); **OPEN** = refresh tokens, per-patient
crisis states (critical path), Chart.js/D3 biometric trends.

---

## 2. UI / theme evolution (all eras preserved) `[REPO][HISTORICAL]`

| Date | Palette / change | Driver |
|---|---|---|
| 2026-06-16 (9 commits) | dusk-slate → rose-mauve → warm neutrals; emoji visibility; date-picker→dropdown; mood per-day UTC/IST fix | UI sprint |
| Streamlit era | rose-mauve (`ACCENT #c06a8b`, `BG_DARK #0f1420`, "No blue accent tones", "zero cold clinical vibes") | `styles_.py` / FOUNDERS_GUIDE |
| 2026-08-05 | **Sage & earth** colour therapy ("psych uses this all day"): deep green-charcoal `#151c19`/`#121715`, accent sage `#8fcbb1`, warm ivory-sage text; ~630 hardcoded tokens across 28 files | All-day clinician use, lower blue-light glare |
| 2026-08-05 (later same day) | **Light "therapeutic calm" (Calm Pulse / Calm Sky)**: warm-white `#FFFFFF`, gradient `#F4F9F8 → #E8F2F0`, teal `#17796E`/`#3E9C8F`/`#0E5E55`, deep-slate text; status OK `#2E8B57`, danger `#C7463B`, amber `#B7791A`, info `#2E7DB8` | Dark sage "read as 'worse than before'" in side-by-side review; research-backed (~35% lower pre-session anxiety, ~42% better retention, light mode wins daytime, halation for astigmatism) |
| 2026-08-05 | **Mojibake fix** in 7 pages (`ðŸ"‹`) — bulk PowerShell 5.1 `Get-Content` read UTF-8 as Windows-1252, double-encoding; reverse-decoded CP1252→UTF-8. Also 8-digit hex alphas `#17796E60` → invalid `var(--accent)60` → rewritten `color-mix(in srgb, …)` | Demo readout |
| 2026-08-05 | **User-selectable light/dark theme**: ~30 CSS custom properties, `:root` (light) + `[data-theme="dark"]`, `useTheme()` hook, 🌙/☀️ toggle, `localStorage('sentinel-theme')`, OS `prefers-color-scheme`, pre-paint inline script (no flash) | "Light/dark choice instead of a debate" |
| 2026-08-05/06 | Dark-mode polish: flat `#101714` (no gradient banding), killed hardcoded light stop `#FBFDFC` in `.card`, real `--shadow`/`--shadow-lg`, borders `#31423A`; theme-aware biodata metric cards | User: gradient "cool but ruins UI/UX" |

**Rationale preserved:** "do not turn this into a debate — ship a theme system the user controls,
rather than us picking one palette for them." `[REPO]`

---

## 3. Feature rationale (design-level) `[REPO][SESSION]`

- **Explicit accept/cancel** for AI drafts: clicking a patient previously "dumped the AI draft
  into the editor card's 'AI draft' box on the far side of the screen with no next step".
- **"Insights speak human, not math"**: two tabs "Current State" (headline "HOW SHE'S DOING",
  3–5 plain insights, "WHAT TO DO NEXT") / "Raw Data" (last tab, "there for review, not daily
  use"). Driven by founder feedback *"they r psych not data analyst na it might be annoying"*.
- **Per-tab sessions:** "two open tabs swapped profiles on refresh" → `localStorage` →
  `sessionStorage`.
- **Risk clamp 0–10:** "15/10 risk looked broken" — legacy DB rows held `risk_score` 15/20.
- **Shared `MoodPicker`** (Constitution #6): uniform segmented chips instead of oversized
  cartoon emojis; `terrible` 💩 → 😔.
- **Follow-up authz:** closed a grade-tampering hole where a patient could grade their own task.
- **PWA:** installable offline app shell; network-first API cache; SW cannot keep BLE alive in
  background (browser limit) — the ring's own history + IndexedDB queue are the resilience
  mechanism. `[SESSION]`
- **Always-visible vitals card with dashes:** an account with 0 ring rows previously hid the
  entire card — "real data absence, but bad UX". `[SESSION]`
- **"💍 My Wearables" for BOTH roles:** self-care; the psychologist has their own ring, not a
  view into a specific patient's vitals. Founder correction. `[SESSION]`
- **Last-sync nudge / sync-due flag:** offered and built in Nov 2026 (relative "Last synced",
  "Sync due today", reading count, 60 s refresh). `[SESSION]`

---

## 4. Product boundaries and "not" statements `[REPO]`

- "not clinic-management software, not a chatbot, not a wearable company" (SWOT).
- "**SENTINEL PILOT-READY v1 — Not: Sentinel Product v1.** Because the goal is not to prove a
  healthcare company exists. The goal is to prove one thing: Does Sentinel's longitudinal
  multimodal synthesis provide clinicians with information that is genuinely useful?" with
  "**If physiology adds nothing → kill the ring**" (`docs/business/SENTINEL_SWOT_AND_STRATEGY.md`
  Action Plan: "Decide whether physiology adds value — If no → kill ring. If yes → continue.").
- **"Don't touch yet"**: native mobile app, ABHA/ABDM, ring manufacturing, PHQ-9/GAD-7 (SWOT).
- **Engineering gates:** 🟢 required for pilot … 🔴 not relevant yet.
- **Positioning:** "Sentinel's Real Moat (if earned): **Not: 28 emotions. Not: ring. Not:
  customized website. Not: AI chatbot.** Instead: patient-specific, longitudinal, multimodal
  clinical information synthesis that is explainable, uncertainty-aware, clinician-controlled,
  and eventually backed by real-world evidence."
- **Milestone:** "**SENTINEL PILOT-READY v1**".
- **Current scores (SWOT):** technical 8/10, research 9/10, **clinical validation 2/10**,
  differentiation today 5.5, business readiness 3/10, regulatory 3/10, hardware 2/10.
- **"Too many strategic identities — needs one core sentence"** listed as a weakness.
- **Crisis timings and discrepancy thresholds are configuration, not evidence.**
- **Never** claim clinical efficacy, diagnosis, treatment, generalisation, or "$0 operation".

---

## 5. Design decisions from the working sessions (Nov 2026) `[SESSION]`

| Decision | Why | Status |
|---|---|---|
| Remove all simulations / fake vitals | Founder: "take all simulations away"; judge-proof honesty | Implemented |
| Unmeasured signals → NULL/dash, never derived | "don't calculate stuff like hrv from bpm" | Implemented |
| Server-side `POST /discrepancy/check-patient` | Client could inject fake bpm/hrv into a clinical result | Implemented + UI-wired |
| Wire comparison into BOTH patient Dashboard and psych Triage | "no frontend page calls these endpoints yet — they're API-only" | Implemented |
| Durable IndexedDB ring queue + cold-start retry | Closed tab / sleeping Render backend | Implemented |
| Web Bluetooth for hosted use | Server has no BLE radio | Implemented (hardware handshake not live-verified) |
| Domain `sentinelpsytech.com` at GoDaddy + Hostinger VPS, UPI | Global reach, UPI payment, low ops; founder rejected AWS | Implemented & live |
| KVM 1 / Ubuntu 24.04 LTS / monthly billing / Docker manager only | 4 GB enough; skip Monarx + paid backups; avoid 24-month prepay | Implemented |
| Key-only SSH + managed firewall 22/80/443 | Password shared in chat; DROP-ALL firewall requires SSH rule first | Implemented |
| Clear Caddy staging-cert fallback before production TLS | Long failed-attempt history left staging cert | Implemented |
| Demo accounts by direct DB seed (weak passwords) | Public signup policy requires 6+ mixed chars | Implemented |
| Psych's OWN wearables space (not assigned-patient view) | Founder: self-care; "u r mentioning spec patient to a psych not happens" | Implemented |

---

## 6. Licensing / legal identity conflicts (kept, not resolved) `[CONFLICT][REPO]`

- Root `LICENSE`: **All Rights Reserved**, "demonstration and review purposes only", "Access to
  the repository does not grant any license to use, copy, or build upon the work".
- `kiot/LICENSE`: **MIT License**. `kiot/00_DOCUMENT_INDEX.md` + `11_Team_and_Credentials.md`
  footers: **"Licensed under the Apache License, Version 2.0"**.
- `README.md`: "Educational project. Built for demonstration of a full-stack healthcare
  simulation platform."
- `docs/hosting-plan.md`: "shared for review under an All Rights Reserved license" **but** also
  "Software and Docker are open source (no licensing cost)" — internally contradictory.
- Commit `1bd8573` (2026-09-13): "correct license wording — released for review (All Rights
  Reserved), not open source"; `2ba89f1`/`86a450a` trimmed/kept research probes out of the
  public repo.
- `JUDGE_QA.md` I: "Will you open-source this?" → no; post-pilot benchmark/training publication
  planned "under a license chosen at that time".
- `fieldcrypt` (separate repo) is MIT. `[REPO]`

---

## 7. Ideas discussed but never implemented (design-level) `[REPO][SESSION]`

- **Secure Transport Layer (STL)** — E2EE+PFS, clinic pull+ACK, dead-letter, zero-metadata
  routing; design only (`concerns.md` #35/#36: "design document, not a system").
- **Native mobile app / background BLE** — impossible via PWA service worker (browser limit);
  ring's own history + durable queue used instead.
- **Camera-based PPG phone app** — JUDGE_QA idea, not built.
- **"Smart room" ambient visualisation** — Streamlit-era `smart_room_.py` (golden circle calm vs
  blue concentric circles + EEG bars intense); not carried forward.
- **Clinician self-monitoring / burnout dashboard** — described in proposals ("the platform also
  watches over the clinician: self-monitoring metrics surface their own stress and fatigue before
  secondary trauma sets in"); partially echoed by the psych's own-wearables page, but no dedicated
  burnout dashboard exists. `[INFERRED]`
- **Chart.js / D3 biometric trends, refresh tokens, per-patient crisis states** — OPEN.
- **Sensor-room / multisensory environment** — `ROADMAP_HARDWARE.md` M3 mentions "sensory room";
  no implementation recorded. `[REPO][INFERRED]`
- **"Patient ring status" side-panel list** — built 2026-11-16 then removed/reframed to the
  psych's own ring. `[SESSION][HISTORICAL]`

---

## 8. Confidence / gaps `[UNKNOWN]`

- The full enumerated "architecture constitution" text is referenced but not in the accessible
  docs. `[UNKNOWN]`
- The exact origin conversation for several design choices (e.g. why rose-mauve was first
  chosen) is not archived verbatim; only the resulting commits/docs survive. `[UNKNOWN]`
