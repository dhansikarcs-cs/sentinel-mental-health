# 09 — DECISIONS AND REASONING ARCHIVE

*For each decision: what, when (if known), why, alternatives, trade-offs, constraints, whether it
remains valid, whether implemented. Rejected/abandoned decisions are included — they are part of
the project's history. Provenance labels per `00`.*

---

## 1. Direction-changing decisions (the big ones)

### D1 — Stop building custom hardware → OEM / software platform (Feb 2026) `[REPO][GIT]`
- **What:** "Stop building hardware. Use consumer smart rings (Oura, Ultrahuman, Apple Watch).
  Sentinel becomes a software platform. Any device exposing HR/HRV via API is compatible."
- **Why:** nRF52840+MAX30102 KiCad PCB (JLCPCB ¥240, 12-day) wouldn't flash — reversed USB
  D+/D− traces, a week with JLink. Rev2 was cheap but enclosure moulding ₹15,000 minimum,
  battery certification months, 3+ months total; plus FDA 510(k)/FCC.
- **Alternatives:** re-spin the board; pursue certification; ring-as-a-service.
- **Trade-offs:** lost hardware control/novelty; gained zero marginal BYOD cost, eliminated
  regulatory burden, enabled the HAL.
- **Constraints:** solo student founder, time, money, no certification path.
- **Valid / implemented:** YES — this is the foundation of `ROADMAP_HARDWARE.md` and the HAL.

### D2 — Streamlit → FastAPI + React rewrite (2026-07-15) `[REPO][GIT]`
- **Why:** Streamlit single-threaded; `time.sleep(3)` crisis auto-refresh froze the whole app;
  no REST API, no frontend framework, one Python process.
- **Alternatives:** keep patching Streamlit; Next.js; Web Components.
- **Trade-offs:** full rewrite cost; gained concurrency, typed client, PWA, Docker, testability.
- **Valid / implemented:** YES; Streamlit archived under `archive/`.

### D3 — Rule-based discrepancy engine, zero ML `[REPO]`
- **Why:** "A false negative in a triage pipeline is lethal"; deterministic/auditable/testable;
  <0.1 ms; 28-label classifier probabilities clinically noisy for a safety function.
- **Alternatives:** TF-IDF+LR (rejected), learned fusion.
- **Trade-offs:** sarcasm/clinical-jargon/English-only blind spots; "false positives acceptable,
  false negatives not".
- **Valid / implemented:** YES (with a later reframing of its "accuracy" — see D9).

### D4 — "Take all simulations away" / no fabricated physiology (Nov 2026) `[SESSION][REPO]`
- **Why:** judge-proof honesty; founder: "don't calculate stuff like hrv from bpm", "take all
  simulations away". A bpm-only push was silently storing 4 fabricated clinical values.
- **Alternatives:** keep seeded demo vitals for a nicer-looking demo (rejected).
- **Trade-offs:** empty-looking dashboards for new accounts (fixed with always-visible dashes).
- **Constraints:** no clinical conclusions from unvalidated wearable measurements.
- **Valid / implemented:** YES — `simulated.py` deleted, 10 fake rows purged, 14 real rows kept.

### D5 — 3-tier AI with local-first Ollama + opt-in cloud `[REPO]`
- **Why:** privacy (India connectivity, "Patient data + free LLM = no"), availability (rule
  fallback never dies), cost.
- **Alternatives:** cloud-only, OpenAI, no fallback.
- **Trade-offs:** ~8 GB RAM local model; cold ~15 s; Groq raw-PHI concern (`concerns.md` #32).
- **Valid:** YES in design; `[CONFLICT]` on whether the running build is local or hosted
  (`pitch.md` vs `new_pitch.md` vs `executive_summary.md`). Working config: `ALLOW_CLOUD_AI=false`.

### D6 — Honest-cost repositioning ("never claim this is a free operation") (2026-09-08/09) `[REPO][GIT]`
- **Why:** older proposals claimed "$0 monthly operating cost / zero financial barrier" —
  inaccurate. `dbb9a7a` refreshed docs with an honest cost model; `proposal_1000.md` now says
  "Deployment is low-cost but never free".
- **Alternatives:** keep the $0 claim (rejected).
- **Valid / implemented:** YES (older `docs - Copy/` PDFs still carry the old claim — `[HISTORICAL]`).

### D7 — Research pivot to the learned emotion classifier (2026-09-01) `[REPO]`
- **Why:** "DECISIVE SCIENTIFIC FINDING": the discrepancy detector is purely rule-based and
  circular; the emotion classifier is the ONE non-circular learned component.
- **Alternatives:** publish discrepancy "96% accuracy" (rejected after F1/F2/F4).
- **Valid / implemented:** YES — Phases 3–9, paper, IRIS manuscripts.

### D8 — Validation-leak fix F5 (Sep 2026) `[REPO]`
- **Why:** `train_goemotions.py` merged splits and swept 4,346 of 5,427 test rows into training,
  inflating micro-F1 to 0.610.
- **Alternatives:** ignore (rejected).
- **Trade-offs:** honest headline number dropped to 0.4642; credibility gained.
- **Valid / implemented:** YES; model MD5 pinned; all experiments re-run.

### D9 — Reframe "96% accuracy" as rule-consistency, not generalisation (Sep 2026) `[REPO]`
- **Why:** F1/F2/F4 — benchmark tested a divergent local copy; held-out labels circular.
- **Alternatives:** keep quoting 96% (rejected; `Evidence_Classification.md` lists "100%
  generalization" as a **Removed** claim).
- **Valid / implemented:** YES in docs; stale PDFs/prep materials remain `[HISTORICAL]`.

### D10 — Hostinger VPS + GoDaddy domain, paid by UPI (2026-11-16) `[SESSION]`
- **Why:** UPI was a hard constraint (no international card); Render is card-only; the founder
  is a minor so AWS signup was not usable; wanted "good and global domain hosting not just inside
  india", one place, no bundle, low ops.
- **Alternatives considered & rejected:** Render (cards only), AWS India Lightsail + CloudFront
  (analysed as "most defensible global + UPI", founder said "nope i just want one thing other
  than aws"), Cloudflare Registrar + Render (needs a card), Hostinger India .com bundle (founder:
  "nope not a bundle"), MilesWeb/BigRock (India-centric).
- **Trade-offs:** Hostinger is globally reachable but single-origin (not multi-region edge); 4 GB
  RAM chosen over 512 MB Render (OOM risk); monthly billing chosen over the 24-month ₹599/mo
  prepay.
- **Constraints:** UPI-only, minor (18+ account holder needed — parent/guardian/co-founder),
  audience mostly **India + New Zealand** (region recommendation Malaysia/Indonesia).
- **Valid / implemented:** YES — live at `https://sentinelpsytech.com`.

### D11 — Psychologist has their OWN ring / self-care space (2026-11-16) `[SESSION]`
- **Why:** founder: "first thing it's abt taking care of themself too", "u r mentioning spec
  patient to a psych not happens". A misreading had built an "assigned patient → psychologist
  vitals" view.
- **Alternatives:** keep the assigned-patient vitals view (rejected/reframed).
- **Trade-offs:** the per-patient vitals endpoint `/{username}/vitals` remains as an API but is
  no longer the psych's primary wearable framing.
- **Valid / implemented:** YES — `WearablesPage`, "💍 My Wearables" tab for both roles, own
  Connect ring button, own last-sync nudge.

---

## 2. Engineering decisions (implemented) `[REPO]`

| ID | Decision | When | Why | Alternative(s) | Valid? |
|---|---|---|---|---|---|
| E1 | SQLite WAL over PostgreSQL for single node | 2026-07-15 | ~4 MB vs ~100 MB idle, no DBA, `cp` backup | PG (later added), JSON, NoSQL | Yes for single node; PG for scale |
| E2 | Fernet + PBKDF2 600K + HKDF | 2026-07-18 | HIPAA-ish at-rest, 4 bundled ops | AES-GCM raw, scrypt, Argon2id KDF | Yes |
| E3 | SHA-256 hash-chained audit log | 2026-07-15 | tamper-evident | proper blockchain | Yes ("not tamper-proof") |
| E4 | HttpOnly cookie + `sessionStorage` token | 2026-07-18 / 08-05 | XSS + per-tab sessions | localStorage, Redux, Context, Zustand | Yes |
| E5 | Argon2id with transparent bcrypt re-hash | 2026-09-09 | OWASP | bcrypt-only | Yes |
| E6 | Read-path encryption hard-fail | 2026-09-09 | no ciphertext leakage | silent `[ACCESS DENIED]` | Yes |
| E7 | Per-patient crisis state rows | 2026-08-30 (`f75600b`) | crises overwrote each other | singleton | Yes (docs still list OPEN — lag) |
| E8 | PG advisory lock single scheduler (`749493`) | 2026-09-09 | exactly one scheduler, failover | Redis/Celery | Yes |
| E9 | PG LISTEN/NOTIFY WS fan-out (`sentinel_ws`) | 2026-09-09 | cross-worker without Redis | Redis | Yes |
| E10 | Non-root containers UID 1001, internal network | 2026-07-18 | pen-test | root | Yes |
| E11 | Negation handling (26 prefixes, 4-word window) | 2026-07-18 | "I am not happy" FP | — | Yes (English-only limitation) |
| E12 | HMAC-signed trustee links | 2026-08-05 | predictable tokens Critical finding | plain tokens | Yes |
| E13 | Durable IndexedDB ring queue + cold-start retry | 2026-11-15/16 | closed tab / sleeping backend loses nothing | direct POST | Yes `[SESSION]` |
| E14 | Server-side `/discrepancy/check-patient` | 2026-11-15/16 | client could inject fake bpm/hrv | `/check` with client values | Yes `[SESSION]` |
| E15 | `npm ci` instead of `npm install` in frontend Dockerfile | 2026-11-16 | lockfile reproducibility (fresh install could break build) | `npm install` | Yes `[SESSION]` |
| E16 | Caddy reverse proxy with auto-HTTPS | 2026-11-16 | free SSL, preserves `/api` prefix, WS upgrades | nginx-only, ACM+CloudFront | Yes `[SESSION]` |
| E17 | Key-only SSH + managed firewall 22/80/443 | 2026-11-16 | password shared in chat; DROP-ALL default | password SSH | Yes `[SESSION]` |
| E18 | `ENCRYPTION_REQUIRED=false` for the pilot | 2026-11-16 | migrated local DB has plaintext journals | fresh DB + fixed passphrase/salt | Yes for pilot; must change for real data |

---

## 3. UI / product decisions (implemented, some superseded) `[REPO]`

| Decision | Why | Status |
|---|---|---|
| Rose-mauve → dusk-slate → warm neutrals → sage → light therapeutic calm → user-selectable light/dark | readability, research, user feedback ("worse than before", "cool but ruins UI/UX") | `[HISTORICAL]` eras, final = user-selectable |
| Risk score clamp 0–10 | "15/10 risk looked broken" | Implemented |
| Plain-English insights, Raw Data in last tab | "they r psych not data analyst na it might be annoying" | Implemented |
| Explicit accept/cancel on AI drafts | no next step previously | Implemented |
| Shared `MoodPicker`, 💩 → 😔 | unprofessional picker | Implemented |
| PWA installable offline shell | continuity of care | Implemented (SW cannot do background BLE) |
| Always-visible vitals card with dashes | empty account looked broken | Implemented `[SESSION]` |
| Last-synced / sync-due nudge | forgotten click | Implemented `[SESSION]` |

---

## 4. Rejected / abandoned decisions (kept) `[REPO][SESSION]`

| Rejected | Why rejected | When |
|---|---|---|
| Custom PCB rev2 / 3D casing / certification | cost, time, regulatory | Feb 2026 |
| Streamlit monolith | froze on `time.sleep(3)` | 2026-07-15 |
| TF-IDF+LR for **discrepancy detection** | 28 noisy probabilities, 4 MB pickle, safety | 2026-07 |
| Redis / Celery for crisis scheduling | broker overhead | 2026-07/09 |
| Next.js / Web Components / Redux / Context / Zustand | gated SPA, bundle, complexity | 2026-07 |
| OAuth2/OIDC, RS256 JWT, refresh tokens, Direct AES-GCM stored key, scrypt, Argon2id-for-KDF, NoSQL | offline clinics, complexity (refresh tokens OPEN) | 2026-07/09 |
| `localStorage` JWT | XSS | 2026-07-18 |
| Dark sage theme / dark gradient | "worse than before" / "cool but ruins UI/UX" | 2026-08-05 |
| Simulated ring & fake seeded vitals | no fabrication rule | 2026-11 |
| "96% learned accuracy" / "100% generalization" claims | F1/F2/F4, circular | Sep 2026 |
| Q8 selective-prediction question | merged into Q3 | research Phase 3/4 |
| Naive confidence abstention (H4) | REFUTED — negative result | Phase 8/9 |
| AWS India Lightsail + CloudFront | founder: "nope i just want one thing other than aws" | 2026-11-16 |
| Cloudflare Registrar + Render | needs international card | 2026-11-16 |
| Hostinger bundled free domain / 24-month prepay / Monarx / daily backups | "not a bundle", monthly pilot, extra agent, paid | 2026-11-16 |
| GoDaddy Full Domain Protection / Titan email / extra domain variations | unnecessary | 2026-11-16 |
| Alpine Linux / 26.10 / 26.04 / 22.04 / RHEL / Kali / Arch OS images | musl breaks numpy wheels; interim/too new/old | 2026-11-16 |
| "Assigned patient → psychologist vitals" as the psych's wearable framing | founder correction: psych has their OWN ring | 2026-11-16 |
| Secure Transport Layer (STL) implementation | design-only, not built | 2026-08-04 |

---

## 5. Constraints that shaped decisions `[REPO][SESSION]`

- **UPI-only payment** (no international card); **minor founder** (18+ account holder required by
  AWS/Hostinger terms → parent/guardian/co-founder).
- **Solo founder + inactive co-founder** (working on AI) → low-ops choices; AI keys left as blank
  env vars for the co-founder to fill later without touching deploy config.
- **One patient, one month pilot** → SQLite + single VPS + 4 GB RAM sufficient; no Postgres, no
  CloudFront, no multi-region.
- **Audience India + New Zealand** → region recommendation Malaysia/Indonesia; free CDN
  (Hostinger Sydney PoP) as a later option.
- **No clinical validation** → every hardware value labelled experimental; no clinical
  conclusions; dashes for unmeasured signals.
- **All Rights Reserved licence** → "released for review", no open-source claim.
- **No guessed proprietary BLE commands** → only documented/verified YCBT opcodes; no DFU,
  reset, OTA, history deletes, unknown writes.

---

## 6. Validity review (as of 2026-11-16) `[INFERRED]`

- D1–D11 all remain valid.
- E1 (SQLite) valid **only** for the single-node pilot; the paper/scale work already validated PG.
- E18 (`ENCRYPTION_REQUIRED=false`) is **explicitly temporary** — must be revisited before real
  patient data.
- D5 / D10 host the `[CONFLICT]`s about AI locality and hosting region.
- Per-patient crisis states (E7) shipped but docs still list OPEN — a documentation debt, not a
  code gap. `[REPO]`

---

## 7. Gaps `[UNKNOWN]`

- Exact decision dates for the working-session decisions (D10–D11, E13–E18) are inferred from
  file timestamps / conversation record, not git commits. `[SESSION]`
- The "three clinical psychologists" consultation that informed the clinical concept has no
  accessible record. `[UNKNOWN]`
- The final chosen VPS region (Malaysia/Indonesia vs Boston) is not recorded. `[UNKNOWN]`
