# 03 — PRODUCT PHILOSOPHY AND DESIGN THINKING

*Product principles, UX philosophy, clinical workflow, human-centred design, explainability,
trust, safety, accessibility, continuity of care, patient/clinician experiences, feature
rationale, product boundaries — including ideas discussed but never implemented.*

---

## 1. Product principles (stated repeatedly across the corpus) `[REPO]`

1. **Clinician-centred.** "Supports decision-making; does not autonomously diagnose or treat."
   The primary user is the clinician; the patient is secondary. AI "organizes patient-generated
   information so clinicians can understand the patient better, **not AI talks to distressed
   people**" (SWOT).
2. **Local-first.** "Sensitive processing designed to occur locally where possible." On-premises
   / Ollama / edge; cloud AI is opt-in (`ALLOW_CLOUD_AI=false`).
3. **Explainable.** "Every risk signal traceable to specific inputs. No black-box scoring."
   Every output carries model version, prompt version, confidence, and `AiSourceBadge`
   provenance ("⚠ RULE-SCORED — MODEL OFFLINE" when degraded).
4. **Multi-modal.** "Reads both subjective (journal text) and objective (physiology) channels."
5. **Human-in-the-loop.** "Alerts escalate to a human. **The system flags; people decide.**"
   "Nothing AI produces is authoritative until a clinician approves it."
6. **Trajectory > snapshot.** "Longitudinal information is more valuable than a single
   assessment" (SWOT). The 167-hour gap is the core problem.
7. **Honest evidence.** "Engineering and simulated evaluations; not evidence of clinical
   efficacy"; "we would rather be honest about where we are than oversell it"; rule-consistency
   is explicitly *not* generalisation.
8. **Deployment is low-cost but never free.** "Never claim this is a free operation."
9. **No fabrication.** Only real measured physiology; unmeasured → dash. `[SESSION][REPO]`
10. **Architecture constitution (Constitution #6):** "every file has exactly one home, and every
    value has exactly one owner. A change that needs the same value in two places is a bug in the
    architecture, not an opportunity." `[REPO]`
11. **Constitution #8 (consultation-first):** "Clinician's consultation is the flow; patient
    data is organized around the patient but always serves the clinician." "The frontend
    renders, it does not orchestrate." `[REPO]`

---

## 2. User experience philosophy

- **"It is not another dashboard; it is hours returned."** The assistant is "work that does
  itself, so the end of the day is earlier"; "The assistant is not an extra screen; it is the
  time that comes back." `[REPO]`
- **Clinician-friendly language, not math.** Direct founder feedback: *"they r psych not data
  analyst na it might be annoying"* — drove `/patients/{username}/plain-insights` (plain-English
  narrative), a two-tab "Current State / Raw Data" split, and moving all numbers to the last tab.
  `[REPO]`
- **Explicit accept/cancel, never silent automation.** Journal→Note drafts now generate in-place
  with "✓ Accept to editor" / "✕ Cancel" and a "review and Save" confirmation, rather than
  dumping text in a distant box with no next step. `[REPO]`
- **Warm, non-clinical patient voice; neutral clinical OAP voice — never mixed.** The master AI
  prompt calls this a global guardrail; patient mode "No advice whatsoever … Zero prescription."
  `[REPO]`
- **Calm "therapeutic" visual design.** Research-backed light theme chosen because desaturated
  mid-tone blues/teals/greens measurably calm (a Journal of Environmental Psychology study
  reported ~35% lower pre-session anxiety and ~42% better treatment retention); light mode wins
  for daytime professional work; dark UI causes halation for astigmatism. Several palette eras
  existed (see `07`). `[REPO]`
- **Always show state, never a blank/broken-looking space.** In the November 2026 work, an empty
  vitals account previously hid the whole Wearable Vitals card; corrected to always show dashes +
  "No readings yet" + "Last synced / Sync due today" so an empty account reads as a state, not a
  bug. `[SESSION][REPO]`
- **Self-care for the clinician too.** The psychologist has **their own** ring/wearables space
  ("💍 My Wearables") — the founder corrected a misreading that framed it as viewing a specific
  assigned patient's vitals. `[SESSION]`

---

## 3. Clinical workflow considerations

- **Central workflow:** `Consultation → Patient Overview (GET /patients/{username}/overview) →
  AI assistance (drafts, triage, briefs — proposed only, invisible) → Decision
  (PUT /psychologists/notes/{id}/approve) → Documentation (ClinicalNote with provenance) →
  Follow-up (FollowupTask)`. `[REPO]`
- **Bounded review.** "flagged review bounded at **5–10 minutes per patient per week**"; the
  clinician benefit is reduced administrative load / secondary-trauma risk. `[REPO]`
- **Priority triage** with decision priorities (reason / evidence / action), consultation-first
  "Open Session" workspace, pre-session brief, compliance radar, silent-period watch, relapse
  indicators, cross-patient patterns, journal-to-note, draft-followup, suggest-slots, AI clinical
  insight, "Why this summary?" explainability panel. `[REPO]`
- **Follow-ups** with due dates, "Assign Now", re-grading, patient proof upload, status badges,
  psychologist feedback box (graded note shown to patient). `[REPO]`
- **Crisis escalation chain:** patient → psychologist → trusted contact → helpline; staged
  30s/60s; halt with one tap; trustee portal with HMAC-signed links. `[REPO][CONFLICT — see §5]`
- **Follow-up research gate:** all AI outputs carry prompt/model version + confidence; clinician
  approval provenance stored. "Nothing enters a clinical record without their approval."
  `[REPO]`
- **No autonomous clinical action:** "Nothing that runs on AI output can take autonomous clinical
  action — that is the `CrisisPolicy` boundary." `[REPO]`

---

## 4. Human-centred design, safety, trust, accessibility, continuity of care

- **Safety language outranks tone** (master prompt). "In any crisis-related content, keep
  language calm and non-alarming, take the content seriously, and never minimize." `[REPO]`
- **Canonical safety copy:** "Sentinel assists monitoring. It never determines whether you are
  safe. If you feel unsafe, seek help immediately regardless of Sentinel's assessment."
  `[REPO]` Also embedded as the AI-generated-insights disclaimer: "AI-generated insights, not
  reviewed by your psychologist. Sentinel assists monitoring — it never determines whether you
  are safe." `[REPO]`
- **"Avoid green 'you're fine' verdicts"**; avoid therapeutic dependence; define an ethical exit
  (all from `concerns.md`, i.e. the project's own critique of what good design requires).
  `[REPO]`
- **Trust via auditability:** SHA-256 hash-chained audit log; "tamper-evident, not
  tamper-proof"; every state-modifying operation appended. `[REPO]`
- **Explainability for the patient:** `AiSourceBadge`, patient-facing disclaimers, "raw data"
  tab separated from human-readable narrative. `[REPO]`
- **Accessibility / continuity:** PWA offline app shell; IndexedDB durable queue so a closed tab
  or sleeping backend loses nothing; the ring keeps its own history so a once-a-day sync works;
  multi-tab sessions via `sessionStorage`; user-selectable light/dark theme with OS
  `prefers-color-scheme` and pre-paint script (no theme flash). `[REPO][SESSION]`
- **Accessibility concerns raised by the red team:** English-only sentiment/negation vs Indian
  vernacular target population (disparate clinical safety for non-English speakers); alarm
  blindness / alert fatigue; "24/7 passive monitoring is structured surveillance". `[REPO]`

---

## 5. Trust, and the honesty discipline `[REPO][SESSION]`

The project treats *honest claims* as a trust mechanism:
- Discrepancy engine "100% rule-consistency" is explicitly labelled a **rule-fidelity
  consistency check, not generalisation**; "It's a rule-based system — there's nothing to
  overfit."
- Held-out labels were derived from the same rules (circular) — flagged and fixed (F1/F2).
- Validation leakage (F5) was found and corrected; inflated 0.610 → honest 0.4642 micro-F1.
- Selective prediction **H4 REFUTED** was published as a negative result.
- No clinical efficacy / diagnostic / human-subjects claims; "Simulated data only", "Not
  clinically validated", "No human participants".
- 30s/60s escalation and BPM/HRV thresholds are configuration/policy, **not validated clinical
  protocol**.
- "no clinical-grade physiological validation"; experimental wearable data labelled, "not a
  clinical assessment".

The founder repeatedly reinforced this: "don't calculate stuff like hrv from bpm", "take all
simulations away", and insisted the UI show real data or dashes, never invented numbers.
`[SESSION]`

---

## 6. Patient and clinician experiences (as built)

**Patient:** journal with 28-label emotion tagging, mood once-per-day lock, today's mood,
journal activity, wearable vitals card, journal↔vitals comparison, AI companion summary (warm,
no advice), crisis/SOS button with staged escalation, follow-up tasks with proof upload,
timeline, bookings, trustee link, emergency page, onboarding tour, light/dark theme, PWA install.
`[REPO][SESSION]`

**Clinician:** triage dashboard with priority tiers, per-patient expanders (mood, AI clinical
insight, explainability, crisis risk assessment, journal↔vitals comparison, wearable vitals),
consultation-first Open Session, clinical notes with accept/cancel drafts, patient insights
(plain-English + raw-data tab), follow-ups with feedback, availability/bookings, export centre,
activity feed, plain-insights narrative, "Patient ring status"/own-wearables space. `[REPO][SESSION]`

---

## 7. Feature rationale (selected) `[REPO]`

| Feature | Rationale recorded |
|---|---|
| Rule-based discrepancy (zero ML) | "A false negative in a triage pipeline is lethal"; deterministic, auditable, testable, <0.1 ms; TF-IDF probabilities too noisy for a safety function |
| Deterministic rule fallback Tier 3 | "a system that returns nothing when the network is down is worse than a system that returns a rough estimate"; errs toward truncation not hallucination |
| SQLite over PostgreSQL (single node) | ~4 MB vs ~100 MB idle; no DBA in target clinics; one `cp` backup; PG kept as a `DATABASE_URL` change for scale |
| Hash-chained audit log | tamper-evident integrity; "not tamper-proof" |
| Fernet field encryption | 4 bundled operations; 22 patient-identifiable fields across 11 model classes |
| Encrypted numerics left plaintext | "would break the core engines" (`bpm >= 110`, `stress > 70`); compensating DB-file-level encryption required before real pilot data |
| Non-root containers, internal network | penetration-test fixes |
| HttpOnly cookie + sessionStorage | XSS resistance + per-tab sessions |
| HMAC trustee links | predictable tokens were a Critical red-team finding |
| PWA + IndexedDB queue | offline resilience, no lost ring readings |
| Light therapeutic-calm theme | research-backed; dark sage "worse than before" |
| `WearablesPage` for both roles | self-care; clinician also has their own ring `[SESSION]` |
| Always-visible vitals card | empty state must not look broken `[SESSION]` |

---

## 8. Product boundaries / ideas discussed but never implemented

**Never implemented / explicitly out of scope:**
- **Custom smart ring hardware** — abandoned Feb 2026 (see `08`). `[REPO]`
- **Secure Transport Layer (STL / `transport.md`)** — E2EE+PFS, clinic pull+ACK, dead-letter,
  zero-metadata routing: *design document only*; `concerns.md` #35/#36 and Transport score 2/10.
  `[REPO][UNVERIFIED]`
- **Redis / Celery** — rejected; PG LISTEN/NOTIFY + threads used instead. `[REPO]`
- **Refresh tokens** — OPEN. `[REPO]`
- **Chart.js / D3 biometric trends** — OPEN. `[REPO]`
- **Companion mobile application** — future work (paper §9). `[REPO]`
- **Native mobile BLE background sync** — discussed in working sessions; impossible via
  PWA/service worker (browser limit); the ring's own history + IndexedDB queue used instead.
  `[SESSION]`
- **Clinical validation / IRB 30-subject pilot, dataset acquisition programme** — specified,
  not executed ("none are yet acquired"). `[REPO]`
- **ABHA/ABDM, PHQ-9/GAD-7, ring manufacturing** — SWOT "Don't touch yet". `[REPO]`
- **Per-patient crisis states, calibration-then-select, cycle-/sleep-aware baselines** — planned
  / partially addressed (per-patient crisis rows shipped in `f75600b` but docs still list OPEN —
  a documented doc/code lag). `[REPO]`
- **"Smart room" ambient visualisation** — existed in the archived Streamlit prototype
  (`smart_room_.py`: golden circle calm vs blue concentric circles + EEG bars intense), not
  carried into the new stack. `[REPO][HISTORICAL]`
- **Camera-based PPG phone app** — raised in JUDGE_QA as an idea, not built. `[REPO]`

**Explicit "should never become" boundaries:** see `01_ORIGIN_AND_VISION.md` §7 and
`13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md`.
