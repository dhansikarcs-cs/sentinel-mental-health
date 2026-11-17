# 01 — ORIGIN AND VISION

*Why Sentinel exists. Preserved with original reasoning, nuances, and conflicting historical
phrasings. Provenance labels as defined in `00_COMPLETE_PROJECT_ARCHIVE.md`.*

---

## 1. The original inspiration and motivation

**The monitoring gap.** The founding observation, repeated across the pitch, proposals, paper
and README, is that outpatient mental-health care observes a patient for roughly **one hour per
week** and leaves the remaining **167 hours** unobserved. `[REPO]` The paper's abstract states it
as: "an outpatient sees a psychiatrist for roughly one hour per week and spends the remaining
167 hours unobserved". The `docs/ENGINEERING_LOGBOOK.md` header and the paper subtitle name the
system *"On-Premises Psychophysiological Triage Node"*.

**The workforce gap.** India has about **0.75 psychiatrists per 100,000** people — described as
roughly one-tenth of the WHO recommendation, and elsewhere as "7.5% of the minimum recommended
psychiatric workforce". `[REPO]` The proposals add: "no real view of what happens between visits,
and crisis risk guessed from a single self-report". The paper cites 80–85% untreated (National
Mental Health Survey), ~60% of districts with no mental-health services, and a ~$1 trillion
annual global economic burden. `[REPO]`

**The clinician, not the chatbot.** From the beginning the intended beneficiary was the
**overloaded clinician**. All four `proposal_*.md` files are titled *"The Sentinel System: An
Assistant for the Overloaded Clinician."* `[REPO]` The problem was framed as clinicians
"buried, not absent" / "not failing their patients; they are drowning", facing administrative
workload, secondary traumatic stress, and burnout. Sentinel was conceived as an assistant that
reads longitudinal signals and returns *time* to the clinician, not as a consumer wellness app.

**The very first dream was hardware.** The earliest recorded ambition (pre-git, `ENGINEERING_LOGBOOK.md`,
"Late 2025") was: *"Started with a dream: build a custom smart ring for emotion detection."*
`[REPO][GIT]` MAX30102 PPG sensors on an Arduino Nano; HRV from raw sensor data was "a nightmare"
— peak detection, inter-beat intervals, frequency-domain analysis, weeks spent on a rolling
5-minute HRV window. This hardware origin and its abandonment are preserved in full in
`08_HARDWARE_AND_EXPERIMENTS.md`.

**Founder context.** The project is the work of a solo student founder (self-described in
`proposal.md` and `docs/proposal_sports_psychologist.md` as "a 15-year-old building Sentinel",
and in `kiot/11_Team_and_Credentials.md` as a "10th-grade student with 3 years of independent
research in psychology and technology"). `[REPO]` A co-founder exists but was described in
working sessions as inactive and focused on the AI side. `[SESSION]` Competition/exhibition
context: **Samsung Solve for Tomorrow · IRIS · ISEF 2026**; an **Emergent Ventures** award is
recorded as funding hardware procurement and pilot deployment. `[REPO]`

---

## 2. How the problem definition evolved

This is important: the framing changed several times and the archive keeps every version.

| Era | Framing | Source |
|---|---|---|
| Streamlit prototype (earliest) | "Sentinel is an emotion-aware, AI-assisted mental health platform connecting patients… with psychologists… all with a warm rose-mauve dark UI and zero cold clinical vibes." | `archive/FOUNDERS_GUIDE.md` `[REPO][HISTORICAL]` |
| Outreach one-liner | "a mental-health assistant that flags when a client's journal doesn't match their stress signals — with customization available for different fields" | `proposal.md`, `docs/proposal_sports_psychologist.md` `[REPO][HISTORICAL]` |
| IRIS submission | "clinician-support system integrating simulated biometrics… with keyword-based text sentiment analysis to flag cases where body signals and written self-report disagree" | `IRIS_2026_SENTINEL/01_IRIS_SUBMISSION/Abstract_250.md` `[REPO]` |
| Executive summary | "A clinic-runs-it-itself mental-health triage tool that reads journals and physiology together, with a human doctor always in the loop." | `docs/executive_summary.md` `[REPO]` |
| Pitch deck | "Privacy-first clinical intelligence for continuous mental-health support." | `docs/business/pitch_deck_content.md` `[REPO]` |
| SWOT strategy | "clinician-controlled clinical intelligence platform that synthesizes longitudinal patient-generated and physiological information to support mental-health care" | `docs/business/SENTINEL_SWOT_AND_STRATEGY.md` `[REPO]` |
| README | "Continuous mental health infrastructure connecting patients and clinicians through real-time monitoring, AI-powered journal analysis, crisis escalation, and structured follow-up management." | `README.md` `[REPO]` |
| **Approved session description** | "Sentinel is a mental-health support platform that pairs private journaling with an AI companion, real-time emotion scoring, and automatic crisis detection, all feeding a clinician triage and admin oversight layer that keeps sensitive AI work safe, auditable, and production-ready." | founder-approved `[SESSION]` |

**Key repositioning.** The SWOT document explicitly narrows the identity: *"Sentinel is strongest
when positioned as a clinician-controlled, longitudinal multimodal clinical-intelligence layer —
not as clinic-management software, not as a chatbot, and not as a wearable company."* `[REPO]`
The founder rejected a "teen" product framing in favour of a general **mental-health support
platform**. `[SESSION]`

---

## 3. The vision, long-term purpose, ambition

- **"The 167-hour gap"** — continuous, longitudinal observation between appointments; "trajectory
  > snapshot" (SWOT). `[REPO]`
- **Two signals, one picture** — subjective (journal text) + objective (wearable physiology),
  cross-checked by a discrepancy engine. This is the core product idea from the outreach
  one-liner onward. `[REPO]`
- **Clinician-first, not patient-chatbot** — "AI organizes patient-generated information so
  clinicians can understand the patient better, **not AI talks to distressed people**" (SWOT).
  `[REPO]`
- **On-premises / local-first** — "the data lands on clinic hardware and stays there"; a ~$200
  mini-PC reference deployment; Ollama local inference. `[REPO][HISTORICAL for the "hosted now"
  variant — see §6]`
- **Low-cost, deployable anywhere** — "any clinic, school, or community center"; Tier-2/Tier-3
  Indian clinics; BYOD consumer wearables at "≈0 marginal cost". `[REPO]`
- **Honesty as a design value** — "we would rather be honest about where we are than oversell it";
  "100% rule-consistency … Is that real world generalization? No, and we say that out loud."
  `[REPO]` The founder repeatedly insisted on this. `[SESSION]`
- **The human closing line of the paper:** *"Software that reduces neither the clinician's burden
  nor the patient's isolation is incomplete."* `[REPO]`
- **"It is not another dashboard; it is hours returned."** `[REPO]`

**Long-term ambition (paper §9, roadmap):** a turnkey deployment — a preloaded mini-PC, LAN
connectivity, clinician credential configuration; IRB-approved clinical validation; a companion
mobile app; calibration-then-select; cycle- and sleep-aware physiological baselines. `[REPO]`
See `11_FUTURE_VISION_AND_ROADMAP.md`.

---

## 4. Intended users and stakeholders

- **Primary:** clinician / psychologist / psychiatrist. **Secondary:** patient.
- **Escalation chain:** patient → psychologist → trusted contact → helpline. `[REPO]`
- **"The platform also watches over the clinician"** — self-monitoring metrics to surface the
  clinician's own stress/fatigue before secondary trauma. `[REPO]` This connects directly to the
  later working-session decision that **the psychologist also has their own ring / self-care
  space** (`WearablesPage`, "💍 My Wearables" for both roles). `[SESSION]`
- **Stakeholders sought:** clinical mentors (psychiatry/clinical psychology), healthcare-
  commercialisation mentors, pilot clinics, hardware/OEM ring partners, an external review/ethics
  board, IRB, regulators. `[REPO]`
- **Buyers:** B2B clinic SaaS + maintenance; B2B2C patient subscriptions; one-time deployment
  packages. `[REPO]`

---

## 5. The philosophy of human authority

This is the project's central ethical commitment, stated in several near-identical forms:

- **"The system flags; people decide."** / "Alerts escalate to a human." `[REPO]`
- **"The AI summarizes, triages, and alerts — it never diagnoses, prescribes, or overrides
  judgment. … an alert is never a black box. The clinician's decision is final, and nothing
  enters a clinical record without their approval. This design is deliberate: in mental health,
  the wrong inference can harm."** `[REPO]`
- **"Sentinel does not replace clinical judgment. It protects it — and gives it back the time
  it lost."** `[REPO]`
- **"Sentinel supports clinical decision-making; it does not autonomously diagnose or treat
  patients."** `[REPO]`
- **"This is a clinician-support mechanism, not a diagnostic system."** `[REPO]`

**Master AI prompt guardrails (`scripts/sentinel_prompt.md`, "single source of truth"):**
"Never diagnose, never prescribe, never reassure clinically, and never claim to be a therapist
or a doctor. Describe what you observe; flag anything that needs a clinician's attention; then
stop." / "Never reproduce raw data … Paraphrase the feeling, never the wording." / "Never invent
facts." / "Safety language outranks tone." / two voices never mixed (warm patient companion vs
neutral clinical OAP). / "**NEVER do a full model training run for behavior fixes.** Persona
fixes live in this prompt, not in model weights." `[REPO]`

**A documented contradiction (kept, not resolved).** Two mutually inconsistent descriptions of
the crisis escalation chain exist: the pitch/executive-summary say "it always waits for a human
to decide first" / "nothing is ever sent before a person decides"; the proposals/README say the
staged protocol "responds automatically … 30 seconds … 60 seconds — and the clinician halts it
with one tap". The private red-team review (`concerns.md` Issue 1, Critical/P0) sides with the
second reading and calls the lack of a clinician in the loop a critical defect. `[CONFLICT][REPO]`

---

## 6. Ethical principles, boundaries, and privacy-first principles

**Prohibited claims (`IRIS_2026_SENTINEL/09_COMPLIANCE/Medical_Claim_Audit.md`):** "Sentinel
diagnoses", "Sentinel treats/prevents", "Improved outcomes", "Clinically validated", "No existing
system", "Improves detection", "Reliably detects", "100% generalization (rule-consistency only)".
Required disclaimers: "Simulated data only", "No human participants", "Not clinically validated",
"Future work". `[REPO]`

**Canonical patient-facing safety copy (from `concerns.md` Issue 42):**
> "Sentinel assists monitoring. It never determines whether you are safe. If you feel unsafe, seek help immediately regardless of Sentinel's assessment."

with a "design that avoids green 'you're fine' verdicts" and "the system is an adjunct, not a
monitor of record". `[REPO]`

**Privacy-first rules:**
- "Patient data + free LLM = no." (`docs/hosting-plan.md`) `[REPO]`
- `ENCRYPTION_REQUIRED=true` fail-closed; field-level Fernet encryption; hash-chained audit log;
  HttpOnly JWT cookies; hashed device tokens with constant-time compare. `[REPO]`
- Local-first AI as the default; cloud AI opt-in behind `ALLOW_CLOUD_AI=false`. `[REPO][SESSION]`
- **No fabricated physiology** — see `13_PROJECT_CONSTRAINTS_AND_PRINCIPLES.md`. `[SESSION][REPO]`
- Experimental wearable data is labelled and "is not a clinical assessment"; no clinical
  conclusions from unvalidated wearable measurements. `[REPO][SESSION]`
- The project actively self-audited redaction: `concerns.md`, `Redaction_Audit.md`,
  `Submission_Checklist.md`, and the video script's rules ("No school name, city, or state / No
  real patient data / 'SIMULATED DATA' label visible / No credentials visible"). `[REPO]`

**Ethical self-critique is part of the project.** `concerns.md` is a private red-team review with
"Panel mindset: reject Sentinel", 43 findings, verdict *"3.8/10 as a deployable clinical system.
~9/10 as a well-engineered prototype"*, and the conclusion *"excellent engineering discipline
aimed at the wrong acceptance criteria."* `[REPO]` Issues include structured-surveillance /
digital-coercion concerns (#7), English-only bias (#9), therapeutic dependence (#42), and the
absence of an ethical exit (#43). This is preserved because the founder wanted reasoning and
uncertainty kept, not polished away. `[SESSION]`

---

## 7. What Sentinel should never become

- Not clinic-management software, not a chatbot, not a wearable company. `[REPO]`
- Not a diagnostic or prescribing system; not autonomous treatment. `[REPO]`
- Not a "monitor of record"; not something that determines whether a patient is safe. `[REPO]`
- Not a "teen" product (explicit founder correction). `[SESSION]`
- Not a system that fabricates physiology, derives HRV from BPM, or invents unmeasured signals.
  `[SESSION][REPO]`
- Not a "black box": every risk signal must be traceable to specific inputs. `[REPO]`
- Not a free/zero-cost operation in its claims ("Never claim this is a free operation").
  `[REPO]`
- Not "28 emotions", "the ring", "a customized website", or "an AI chatbot" as its moat (SWOT).
  `[REPO]`
- Not a replacement for clinical judgment. `[REPO]`

---

## 8. Difference from conventional mental-health apps / generic AI chatbots

- **Clinical, not consumer:** clinician-controlled decision support vs direct-to-consumer
  mood/chat apps. The SWOT's competitor table positions against BetterHelp/Talkspace,
  Headspace/Calm/Woebot, Lyra/Spring, Eleos Health, Oura/Samsung Galaxy Ring. `[REPO]`
- **Multimodal longitudinal synthesis, not single-signal scoring:** both subjective text and
  objective physiology, over time, with cross-modal discrepancy. "The industry default: collect
  everything → send to cloud → generate a score." Sentinel: "Patient signals → local processing
  → contextual analysis → explainable outputs → clinician review → human decision". `[REPO]`
- **Deterministic, explainable safety path:** the discrepancy engine is rule-based "for
  explainability and auditability"; "A false negative in a triage pipeline is lethal"; the
  high-risk escalation path is not gated on learned confidence ("The Deterministic Backstop").
  `[REPO]`
- **Local-first / on-premises privacy** vs cloud-first apps. `[REPO][HISTORICAL variant]`
- **Honest evidence discipline:** "Engineering and simulated evaluations; not evidence of
  clinical efficacy"; "rule-fidelity consistency check rather than a generalization result".
  `[REPO]`
- The paper claims: "We are not aware of any prior system combining on-premises deployment,
  consumer-wearable integration via a hardware abstraction layer, deterministic discrepancy
  triage, defense-in-depth security hardening, and a distribution-shift-aware reliability
  methodology in a single publicly available package." `[REPO]`

---

## 9. Local AI vs hosted AI — a preserved historical disagreement `[CONFLICT]`

Three incompatible states of the AI-locality story exist across the corpus; all are kept:

1. `docs/pitch.md` §4 "Honest, local AI": "Ollama runs on the premises".
2. `docs/new_pitch.md` §4 "Honest, local-by-design AI": "Our own model is still in training, so
   right now Sentinel runs on a hosted model, wearing our prompt, our guardrails, and our safety
   rules"; `docs/executive_summary.md`: "the running build uses a hosted model (GPT-5.4)";
   `docs/TECHNICAL_DESIGN.md`/proposals: "the AI runs fully offline via Ollama… cloud AI is
   disabled by default".
3. `concerns.md` Issue 32: sending raw journal text to Groq as fallback "kills the 'local AI'
   pitch". `[REPO]`

In working sessions the running configuration was `ALLOW_CLOUD_AI=false`, `GROQ_API_KEY` blank
(env vars left for the co-founder to fill later), with graceful offline/rule-based fallback —
`/api/agent/status` returning `agent_client_ready:false` when Ollama/Groq were not configured
was considered acceptable. `[SESSION]`

---

## 10. Confidence / gaps `[UNKNOWN]`

- The precise original conversation in which the idea was first articulated is not archived
  verbatim; the earliest recoverable statements are the `ENGINEERING_LOGBOOK.md` "Late 2025"
  entry and the `archive/FOUNDERS_GUIDE.md` Streamlit-era vision. `[UNKNOWN]`
- The "three practicing clinical psychologists" consultations and "one medical doctor and one
  additional clinical psychologist" endorsement are stated in the paper's Declarations but the
  underlying records are not in the accessible corpus. `[UNKNOWN]`
- The exact date and content of the founder's shift from "teen / mental-health assistant" to
  "clinician-support / clinical-intelligence platform" is not recorded; only the artifacts
  showing both states survive. `[INFERRED]`
