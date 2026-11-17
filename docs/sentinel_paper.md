# Sentinel: An On-Premises Software Platform for Continuous Psychophysiological Triage — Reliability Under Distribution Shift and Physiological Context

---

**Author:** Dhansika.R
**Affiliation:** Independent Researcher
**Date:** September 2026
**Correspondence:** dhansika.r.cs@gmail.com
**Preprint note:** This manuscript has not been published or submitted elsewhere; it is posted as a preprint and formatted for peer-review submission.

---

## Abstract

Mental health care is defined by a monitoring gap: an outpatient sees a psychiatrist for roughly one hour per week and spends the remaining 167 hours unobserved, during which acute stress, panic episodes, or suicidal ideation can develop without intervention. The cost of this gap is borne not only by patients but by the clinicians who carry responsibility for their safety between sessions: mental-health professionals manage caseloads that outpace workforce supply, absorb patients' distress and trauma narratives daily (a well-documented route to secondary traumatic stress and burnout), and spend a growing share of their time on documentation and administrative work rather than direct clinical attention [15][16]. This paper presents Sentinel, an on-premises platform that fuses a subjective channel (patient journal text) with an objective channel (consumer wearable biometrics) through a deterministic, explainable discrepancy-detection engine, and surfaces incongruence to clinicians as a prioritized triage queue with an automated crisis-escalation protocol. We evaluate the reliability of the platform's constituent classifiers not only under conventional same-distribution benchmarks but under the distribution shift that real deployment imposes, and we examine whether the engine's physiological assumptions survive the contextual variation (menstrual-cycle phase, sleep debt) of free-living patients.

We report four main findings. First, the rule-based discrepancy engine matches its declared operating point exactly—100% accuracy with zero false positives and zero false negatives on a hand-crafted 50-profile in-set suite (21 discrepant, 29 matched) spanning all nine sentiment-by-biometric combinations, and a further 100% on a 50-profile held-out suite (20 discrepant, 30 matched); because expectations mirror the rule the engine implements, this is a rule-fidelity consistency check rather than a generalization result, and the engine is protected against regression by a 23-case golden gate enforced in a six-job continuous-integration pipeline. Second, the text-emotion classifier that feeds the risk engine is measurably miscalibrated in-domain (macro-ECE 0.0902, Brier 0.0510) and becomes significantly more overconfident out-of-domain on mental-health journaling text (macro-ECE 0.1196, Brier 0.0724; +41%; non-overlapping bootstrap 95% CIs), with discriminative performance collapsing from micro-F1 0.4642 to 0.2704 (−42%); the collapse is concentrated in the emblematic-positive and approval/neutral classes (gratitude −0.50, neutral −0.50, admiration −0.44, love −0.26 in per-class F1) and in approval and sadness, while several high-arousal classes (anger, fear, remorse, surprise) hold or improve. Third, miscalibration propagates into downstream decisions only weakly (McNemar in-domain p = 0.031, out-of-domain p = 1.00); the dominant effect is the shift itself, which roughly doubles the risk-engine trigger rate (1.40% → 2.77%). Fourth, the naive mitigation of confidence-based abstention fails to restore reliability out-of-domain (selective error 0.91 → 0.80 at 26% coverage), a negative result that motivates calibration-then-select as a design requirement. On the physiological side, the engine's prototype thresholds assume a fixed adult baseline, whereas published menstrual-cycle and sleep-debt effect sizes (HRV variation of approximately ±47% and RHR ±17% across the cycle; a 10% weekly sleep decrease raising RHR ≈ +1.2% and lowering HRV ≈ −2.8%) imply that contextual deviation must be separated from novel deviation before the engine can classify free-living female outpatients. We specify a tiered dataset-acquisition program to estimate per-person "expected today" baselines conditioned on cycle phase, sleep, and season.

As a software deliverable, Sentinel is designed for clinics with limited technical staff: a ≈200 USD mini-PC, ≈8–10 USD/year domain, an optional cloud VM at ≈15 USD/month, single-command Docker Compose deployment, 222 automated tests, a standardized CSV benchmark logbook, and multi-worker scaling verified against real PostgreSQL 17. The encryption layer has been released separately as `fieldcrypt`, a standalone MIT-licensed open-source package, so the cryptographic core is independently auditable. We present the complete system design, controlled calibration and shift experiments with statistical analysis, reproducible benchmarks, and an explicit discussion of limitations. We are not aware of any prior system combining on-premises deployment, consumer-wearable integration via a hardware abstraction layer, deterministic discrepancy triage, defense-in-depth security hardening, and a distribution-shift-aware reliability methodology in a single publicly available package.

**Keywords:** mental health monitoring, software reliability, distribution shift, probability calibration, wearable biometrics, discrepancy detection, on-premises deployment, edge AI, explainable AI, clinician burnout, health data privacy

**Highlights**
- Rule-based discrepancy engine: 100% accuracy (in-set and held-out 50-profile suites), zero false negatives and zero false positives, <0.1 ms per profile; rule-fidelity consistency check; 23-case golden gate in CI.
- Emotion classifier calibration degrades under shift: macro-ECE 0.090→0.120, Brier +41%, micro-F1 0.464→0.270.
- Shift, not miscalibration, drives downstream decisions: trigger rate 1.40%→2.77%; McNemar in-domain p=0.031, out-of-domain p=1.00.
- Confidence abstention fails out-of-domain (selective error 0.91→0.80 at 26% coverage): a negative result motivating calibration-then-select.
- Humane-context gap: cycle (±47% HRV, ±17% RHR) and sleep (−10% → +1.2% RHR, −2.8% HRV) effects must separate contextual from novel deviation.
- Clinician-first design: continuous monitoring fills the unobserved hours and protects clinicians from secondary trauma, burnout, and administrative burden.

---

## 1. Introduction

Mental health disorders represent one of the most significant global health burdens of the 21st century. The shortage of mental health professionals is particularly acute in low- and middle-income countries. In India, the psychiatrist-to-population ratio is approximately 0.75 per 100,000 people, compared with the WHO minimum recommendation of 1 per 10,000 [1]; approximately 60 percent of districts lack any mental health services whatsoever, creating a fundamental monitoring gap. A patient receiving outpatient care may see a psychiatrist for one hour per week, leaving 167 hours of unmonitored time during which acute stress, panic episodes, or suicidal ideation can occur without intervention. The National Mental Health Survey of India reports that 80–85 percent of individuals with mental health conditions receive no treatment, and the economic burden of mental health conditions costs the global economy an estimated 1 trillion USD annually in lost productivity. Technology-assisted monitoring offers a scalable alternative that extends the reach of the existing clinical workforce without a proportional increase in the number of clinicians.

Consumer wearables provide an objective sensing channel. Devices such as the Oura Ring and Apple Watch have demonstrated research-grade accuracy for heart rate (HR) and heart-rate-variability (HRV) monitoring: validation studies report a mean absolute error of 0.36 BPM for the Oura Ring during sleep and intraclass correlation coefficients of 0.91 for HRV against medical-grade ECG [3]; the Apple Watch shows HRV measurement error within 5 percent of research-grade Polar H10 chest straps. With an estimated 200 million wearables shipped globally in 2025 and an installed base exceeding 1 billion units, and wearable ownership among mental health outpatients in high-income countries estimated at 30–40 percent and growing, a significant fraction of the target population already owns compatible hardware. Leveraging patient-owned devices avoids procurement and certification cost (an FDA 510(k)-classifiable custom device was explicitly rejected after a failed PCB fabrication attempt, Section 5.2) and eliminates vendor lock-in through a hardware abstraction layer.

Sentinel automates the clinical reasoning of discrepancy detection: cross-reference what the patient reports (journal text) against what their physiology shows (wearable HR/HRV), and flag incongruence—negative self-report with calm physiology, positive self-report with stressed physiology, or neutral text with stressed physiology—as a triage signal. The humane motivation is situated on both sides of the clinician's chair. On the patient side, the platform exists because there is no care in the unobserved hours: between appointments, deteriorating state is invisible, and the absence of a signal is not the absence of need. On the clinician side, mental-health professionals carry a sustained emotional load—absorbing patients' trauma narratives session after session—which places them at documented risk of secondary traumatic stress and compassion fatigue [15], compounded by rising administrative and documentation burden that competes with direct clinical attention [16]. A monitoring system that quietly watches, summarizes, and surfaces only actionable discrepancies reduces the clinician's constant need to re-read journals and re-derive context, protecting the scarce resource that is clinical attention rather than displacing it. The clinical concept was informed by structured consultations with three practicing clinical psychologists prior to engineering; all affirmed the monitoring gap and the utility of an automated cross-reference. The workflow (patient journal input, biometric ingestion, automated discrepancy flagging, periodic review, escalation of critical alerts) was subsequently endorsed by one medical doctor and one additional clinical psychologist. The clinicians' adoption constraint was not software cost but time and operational overhead, which shaped the explicit deployment economics of Section 5.7 and the prioritization logic that keeps flagged review bounded at 5–10 minutes per patient per week.

The reliability of such a system depends on two properties that conventional evaluation typically ignores. First, the classifiers that produce the triage signal are trained on one distribution (Reddit comments, in the case of the text-emotion model) and deployed on another (patient journaling text); if their probabilities are miscalibrated under that shift, the downstream risk engine inherits distorted inputs, in the same manner that ML systems evaluated only under same-distribution splits can report near-perfect benchmark scores while collapsing operationally. Second, the physiological thresholds are fixed norms, yet free-living physiology is contextual: published effect sizes show HRV varying roughly ±47% and RHR ±17% across the menstrual cycle, and a 10% weekly drop in sleep raising RHR ≈ +1.2% and lowering HRV ≈ −2.8%. A female outpatient in the late-luteal phase with an overnight sleep deficit will present low HRV for reasons unrelated to psychological crisis; the engine must distinguish contextual deviation from novel deviation rather than escalate both.

This paper investigates these questions through the following research questions:

**RQ: To what extent does Sentinel's automated triage remain reliable when (a) its text-classifier inputs are drawn from a deployment distribution different from training, and (b) its physiological assumptions encounter the contextual variation of free-living patients—and what can be done to make the system reliable under those conditions?**

The research question is decomposed into four sub-questions that structure the experimental design:

- **RQ1 (Experiments E1, E2):** Does the distribution shift from training (Reddit GoEmotions) to deployment (mental-health journaling text) degrade the calibration and discriminative performance of the text-emotion classifier?
- **RQ2 (Experiment E3):** Does calibration degrade independently of shift, and does it propagate into the risk-engine and discrepancy-policy decisions a clinician actually sees?
- **RQ3 (Experiment E4):** Can confidence-based abstention preserve recall while cutting false positives under shift, or is the classifier's confidence an unreliable selector out-of-domain?
- **RQ4 (Section 6.2, dataset program):** Given the documented cycle and sleep effects, can per-person contextual baselines ("expected today") be derived from existing public datasets so that the deterministic discrepancy engine separates contextual from novel deviation?

If evaluation methodology does not account for deployment distribution shift, reported performance metrics may systematically overestimate the operational reliability of the triage system—and, in a mental-health context, the cost of silent overconfidence is clinical, not merely statistical.

The contributions of this paper are: (1) a reliability methodology for a deployed edge-AI health system that measures calibration under shift with controlled statistics (bootstrap CIs, McNemar tests) rather than reporting accuracy alone; (2) quantitative characterization of calibration degradation (macro-ECE 0.0902 → 0.1196, Brier +41%), discriminative collapse (micro-F1 0.4642 → 0.2704), decision propagation (trigger rate 1.40% → 2.77%; McNemar in-domain p = 0.031, out-of-domain p = 1.00), and a refuted confidence-abstention mitigation; (3) a deterministic, explainable discrepancy engine that matches its declared operating point exactly (100% on both the in-set and held-out 50-profile suites, zero false negatives and zero false positives), protected by a 23-case golden gate; (4) an explicit dataset-acquisition program to supply cycle- and sleep-contextualized per-person baselines from mcPHASES, WHOOP/Stanford published priors, and free-living smartwatch datasets; (5) a fully open, cost-explicit on-premises software deployment (≈200 USD hardware) with the encryption layer released as the standalone MIT-licensed package `fieldcrypt`; and (6) an engineered clinician-side benefit—bounded review, automated summarization, and continuous observation across the unmonitored hours—targeted at the secondary-trauma, burnout, and administrative-load pressures documented in Section 4.6.

---

## 2. Problem Statement

The core problem is a gap between how the platform's classifiers are evaluated and how they are deployed—compounded by a gap between fixed physiological norms and lived physiological context. Underneath both is a human gap with two edges: patients go unobserved for 167 of every 168 hours, and the clinicians nominally responsible for that interval must either carry the emotional weight of constant vigilance alone or admit they cannot bear it—a large part of why secondary trauma, burnout, and turnover now shape the mental-health workforce itself.

Consider a concrete scenario. The text-emotion classifier is trained on 48,836 Reddit comments (GoEmotions official train + validation), where it achieves in-domain micro-F1 = 0.4642 with a diagnosis that its probabilities are already overconfident (macro-ECE 0.0902). A patient with grief writes a journal entry: "I can't stop thinking about the funeral, it's like a weight." The model, trained on social-media comment fragments, must now classify first-person, symptomatic, clinical journaling—a different genre with different a priori class distributions. If the model's confidence here is inflated, the risk engine's weighted scoring receives probability mass it does not deserve; the discrepancy engine then compares a misweighted emotion signal against biometric thresholds that themselves assume a fixed adult baseline. A woman in her late-luteal phase with an overnight sleep deficit shows HRV ≈ 20 ms (below the engine's low-stress threshold of 55, and near the high-stress threshold of 25) for reasons unrelated to crisis. The system must not escalate this; it must explain why the value deviates.

The failure to separate contextual from novel deviation is not merely a tuning detail. Sentinel's thresholds (high stress: BPM ≥ 110 AND HRV ≤ 25; low stress: BPM ≤ 80 AND HRV ≥ 55) are prototype design parameters derived from resting-HR and RMSSD norms [5], adapted for a pre-menopausal female outpatient population. Without context, the engine conflates three distinct mechanisms: acute psychological stress, hormonal-cycle phase, and sleep debt. Each has different clinical meaning and different escalation action. A reliability argument for a mental-health triage system must therefore state its confidence honestly under the distribution where it is deployed (RQ1–RQ3) and must know its patient's context before treating a deviation as novel (RQ4).

---

## 3. Research Gap

Three gaps limit the practical value of existing work on digital mental-health monitoring.

**First, reliability under distribution shift is rarely reported.** The dominant practice in affective-computing text classification reports accuracy or F1 on a single random split. The calibration literature—Ovadia et al. [9] (calibration degrades under shift), Guo et al. [10] (deep nets overconfident, ECE methodology), Niculescu-Mizil and Caruana [14] (LR probabilities partially calibrated)—has established the theoretical frame, and shift studies in speech-emotion recognition (Herath 2025: cross-domain accuracy collapse 0.914 → 0.266–0.311) show classical models do degrade. But lightweight text-emotion classifiers used in *rule-based mental-health decision pipelines* are rarely characterized for calibration, and their propagation into explicit risk and discrepancy decisions is—to our knowledge—unmeasured.

**Second, confounds between calibration and shift are rarely isolated.** When a system underperforms out-of-domain, it is unclear whether the cause is raw probability miscalibration, the distributional shift of the label/score distribution, or their interaction. This paper separates the two with a calibrated-counterfactual (isotonic regression fitted on in-domain probabilities, re-applied to out-of-domain decisions) and McNemar tests on decision flips, so that the dominant mechanism is attributed rather than assumed.

**Third, the physiological context dimension is absent from existing discrepancy systems.** Prior automated discrepancy work uses laboratory-grade ECG/skin-conductance in controlled settings; consumer-wearable discrepancy detection in deployed outpatient systems is not represented, and none accounts for menstrual-cycle phase or sleep debt as explicit context features. The gap is not the absence of wearable monitoring, nor the absence of on-premises health information systems (OpenMRS, DHIS2), but the absence of these combined with a deterministic discrepancy mechanism that is *context-aware*.

This paper addresses all three gaps: a controlled calibration-and-shift study with attribution statistics, an explicit negative result on abstention, and a concrete dataset program for contextual awareness.

---

## 4. Related Work

### 4.1 Wearable and Digital Phenotyping for Mental Health

Torous et al. [2] surveyed over 1,500 digital mental-health applications, identifying data privacy, lack of interoperability, and the absence of offline functionality as critical gaps; fewer than 15 percent offered offline capability and fewer than 5 percent used end-to-end encryption. Mindstrong demonstrated that smartphone behavioral markers predict mood state in major depressive disorder (≈82% accuracy); the Beiwe platform [4] pioneered active and passive smartphone phenotyping (GPS mobility, call/text metadata, surveys). Both rely on cloud processing without on-premises deployment. The Mindstrong adaptation, AliveCor-style single-channel approaches, and the broader digital phenotyping literature rarely expose calibration or shift statistics, and none couples subjective self-report to consumer-wearable physiology through an explainable discrepancy engine.

### 4.2 Discrepancy Detection in Clinical Psychology

Mismatches between self-reported affect and physiological arousal are well documented (affective misattribution; Liao et al. show self-report–skin-conductance mismatches predict CBT outcomes). These studies use laboratory equipment and manual or semi-automated analysis. Sentinel automates this decision with consumer wearables on low-cost hardware; the rule-fidelity benchmark (Section 6.1) is the first quantitative statement of such an automated engine's operating point, including the deliberate recall-over-precision bias for a safety-critical setting.

### 4.3 Calibration Under Distribution Shift in Affective Computing

Ovadia et al. [9] established that neural-model predictive uncertainty degrades under shift and simple calibration fails out-of-domain. Guo et al. [10] standardized ECE for neural networks; Zadrozny and Elkan show one-vs-rest probability needs per-class calibration, which matches Sentinel's multi-label OvR structure and motivates per-class ECE analysis. Grünwald/metric-gate guidance (ECE > 0.10 as a red flag; report Brier alongside ECE) locks the metric suite. The intersection missing from the literature—lightweight text-emotion classifier calibration plus propagation into rule-based mental-health decisions plus selective prediction as mitigation—is exactly the contribution of our Phase 8/9 experiments (Section 6.3).

### 4.4 Selective Prediction and Abstention

Selective prediction (Chow 1970; Geifman & El-Yaniv 2017) formalizes coverage/risk trade-offs with a confidence selector. Risk-calibrated affective-computing work (arXiv 2503.22712) argues raw confidence is unreliable under shift and uncertainty must be quantified before feeding downstream mental-health decisions. Our E4 result (Section 6.3.4) empirically confirms the negative claim: on an *uncalibrated* lightweight model, a max-probability threshold does not preserve reliability out-of-domain—consistent with the literature's requirement for calibration-then-select.

### 4.5 Physiological Antecedents: Cycle and Sleep

Published effect sizes motivate RQ4. The WHOOP/Stanford 2026 study [6] (2,596 women, 42,759 cycles, 1.2M days) and the WHOOP 2024 study [7] provide phase curves for RHR/RMSSD; a 10% weekly decrease in sleep is reported to raise RHR ≈ +1.2% and lower HRV ≈ −2.8%. The mcPHASES dataset [8] (42 menstruators, two 3-month intervals, daily urinary LH/E3G/PdG) provides hormonal ground truth rather than calendar estimates. No deployed discrepancy system known to us consumes these signals; Sentinel's dataset program (Section 6.2) is the design response.

### 4.6 Clinician Burden, Burnout, and the Case for Sustained Monitoring

The humane motivation for continuous monitoring rests on two documented pressures. First, the unobserved hours are where deterioration goes unnoticed: a patient may be well at an appointment and critically unwell before the next one, and no self-report a clinician can elicit retrospectively reconstructs the interval. Second, the burden of managing that uncertainty falls on the clinician. Secondary traumatic stress and compassion fatigue are well characterized in mental-health professionals who absorb trauma narratives repeatedly [15]; administrative and documentation load competes directly with time for patients [16]. Digital platforms in this space overwhelmingly optimize the patient-facing experience (engagement, self-tracking, content delivery) and seldom measure whether they *reduce the clinician's cognitive and administrative load*. Sentinel is designed as clinician-support software first: it continuously observes so no one must remain vigilant by hand, it summarizes so no context must be re-derived from long journals, and it surfaces only discrepancies so that bounded review (5–10 minutes per patient per week) is an explicit, engineered property rather than an accident.

---

## 5. System Design

### 5.1 Deployment Architecture

Sentinel deploys as two containers: a FastAPI backend (Python 3.11, uvicorn, ≈120 valid routes across 29 API router modules) and a React frontend (Vite/TypeScript) served by an Nginx reverse proxy that terminates TLS and forwards only `/api/*` routes. The backend runs on an internal Docker bridge network with the `internal` flag set, giving it no external network access; even a compromised backend cannot pivot to the internet or LAN. Storage supports single-node SQLite (WAL mode) or multi-worker PostgreSQL 17 (psycopg2 driver, Alembic migrations, idempotent and dialect-portable), with a health write-probe verified on both engines. Containers run as non-root; headers (CSP, HSTS, nosniff) are applied by a security middleware.

### 5.2 Hardware Abstraction Layer and the Pivot to Consumer Wearables

A hardware abstraction layer (HAL) accepts HR/HRV from any wearable exposing BPM and RMSSD over REST, WebSocket, or BLE, normalizing to a canonical payload `{ bpm, hrv, timestamp, source }`. Adapters implement two methods (`connect()`, `read()`): SimulatedRing (deterministic per-user/per-hour calm/balanced/stressed streams for deterministic CI), VendorAPIRingSource (Oura Cloud API v2, Ultrahuman), and BLEGATTRingSource (bleak, Heart Rate Measurement characteristic 0x2A37, configurable OEM maps). Adding a device never touches the discrepancy engine, crisis engine, or dashboards.

This design follows a failed custom-hardware attempt, documented in the engineering logbook. An nRF52840 (BLE) + MAX30102 photoplethysmography PCB fabricated at JLCPCB (¥240, 12-day lead-time) would not flash firmware: the USB D+/D− traces were reversed, and isolating the schematic error against the JLink debugger took roughly a week. Re-spinning the board was cheap and fast, but the surrounding tooling was not—enclosure moulding carried a ₹15,000 minimum, battery and certification ran months, and the build-your-own path stretched past three months. The pivot eliminated FDA 510(k) and FCC certification and procurement, reducing per-patient hardware to ≈0 marginal cost in bring-your-own-device mode. Where clinics provision rings, hardware is financed through a ring-as-a-service subscription rather than treated as free.

### 5.3 Deterministic Discrepancy Engine

The core detection is rule-based, not learned, for explainability and auditability. The sentiment channel tokenizes the journal text into 32 positive and 60 negative terms (55 single tokens plus 5 multi-word phrases), applies a negation detector that filters keywords preceded by any of 31 negation prefixes within a three-word window ("I am not happy" does not trigger positive affect), and attaches 3 idiomatic intensifiers. The biometric channel classifies state as high stress (BPM ≥ 110 AND HRV ≤ 25), low stress (BPM ≤ 80 AND HRV ≥ 55), or moderate. A hardcoded truth table flags exactly three of the nine sentiment-by-biometric combinations as discrepancies—positive+high, negative+low, and neutral+high—and by deliberate design leaves the other six combinations un-flagged. Bias toward recall over precision is expressed inside the flagged region (no false negatives there), while ambiguity such as negative+moderate stays out of the escalation path entirely. The engine runs in ≈0.1 ms per profile with no external dependencies.

### 5.4 Three-Tier AI Pipeline

Journal summarization and risk assessment degrade gracefully: Tier 1 is local Ollama (a custom `sentinel` model, ≈8 GB RAM footprint, requests serialized behind a lock with a 500 ms inter-request gap, 20 s request timeout); Tier 2 is Groq Cloud running `llama-3.1-8b-instant` (credentials via environment variables); Tier 3 is a deterministic, dependency-free keyword-frequency rule engine that always returns a structured assessment, so summarization and risk never block on provider availability. The prompt mandates classifying any indication of suicidal ideation, self-harm, or imminent danger as high risk regardless of context. The pipeline emits dual-mode output: a warm, supportive companion-voice summary for the patient (no clinical language, no unsolicited advice) and a structured OAP clinical summary for the psychologist.

### 5.5 Security Model and `fieldcrypt`

Twenty-two patient-identifiable fields across eleven model classes are encrypted at rest by an `EncryptedText` TypeDecorator applying Fernet (AES-128-CBC + HMAC-SHA256). The key derives from a clinician-entered passphrase via PBKDF2-HMAC-SHA256 (600,000 iterations; ≈173 ms derive in the benchmark logbook), expanded with HKDF-Expand under distinct labels into Fernet and HMAC keys; the key lives only in process memory, and reads fail closed when `ENCRYPTION_REQUIRED=true` without a key. Passwords use Argon2id (time_cost 3, memory_cost 65536, parallelism 4) with transparent legacy-bcrypt re-hash on login. State-modifying operations append to a SHA-256 hash-chained audit log: each entry stores its predecessor's hash, so retroactive tampering breaks the chain and leaves evidence. Device binding uses one-time tokens stored only as SHA-256 hashes, compared in constant time, revocable immediately.

The encryption layer is released as `fieldcrypt`, a standalone, MIT-licensed open-source package (21 passing tests, CLI included, public repository), so the cryptographic core can be independently audited and reused outside Sentinel.

### 5.6 Multi-Worker Scaling Without Redis

Single-node deployments use SQLite; multi-worker deployments scale the API over PostgreSQL with three safety mechanisms: DB-backed fixed-window rate limiting shared across workers; failover-safe scheduling via a PostgreSQL advisory lock (SCHEDULER_LOCK_KEY 749493, 10 s heartbeat, verified leader-takeover on kill); and POSTGRESQL LISTEN/NOTIFY fan-out for cross-worker WebSocket push (channel `sentinel_ws`), with all state persisted so a failed publish loses nothing.

### 5.7 Cost of Operation

Costs are explicit rather than idealized:

| Item | Approximate cost | Type |
|---|---|---|
| Mini-PC (Pi 5 / Intel N100) | ≈200 USD | One-time |
| Cloud VM (if no on-site hardware) | ≈15 USD/month | Recurring |
| Domain + TLS | 8–10 USD/year | Recurring |
| Managed PostgreSQL (optional) | free tier–25 USD/month | Recurring |
| Groq cloud LLM (optional) | cents/month | Recurring |
| Provisioned ring (pilot of 30) | ring-as-a-service tier | Recurring (B2B2C) |
| Patient BYOD | zero marginal hardware | — |

The software carries no license fee; Tier 3 AI is built in. The primary ongoing cost is clinician review of flagged discrepancies (5–10 min/patient/week). Revenue architecture (companion business model): clinic SaaS ₹2,499/month + ₹999 maintenance, patient tiers ₹499–1,499/month, one-time deployment ₹9,999–19,999, reference unit economy ≈₹40,948/month recurring per 50-patient clinic at >70% gross margin. The pilot is funded by an Emergent Ventures award, rings sourced from Jport (China).

---

## 6. Empirical Validation

### 6.0 Reproducibility and Test Infrastructure

The suite contains 222 automated tests (authentication, journal pipeline, discrepancy, crisis concurrency, storage I/O, AI latency, crypto, ring ingestion, hardening, scale-runtime) running ≈72 s against an isolated test database with AI tiers mocked; the benchmark runner additionally writes a standardized CSV logbook (`benchmarks/logbook_benchmark.csv`). A six-job GitHub Actions pipeline gates every push: lint/typecheck (ruff; mypy advisory), backend integration checks (Ring-SDK API tests, an app-import smoke test, and the golden-gate model regression gate `python -m scripts.eval_golden_set --strict`, 23 cases: 16 risk + 7 emotion), dependency security scan (advisory), frontend TypeScript type-check + production build, Docker image builds, and a deploy placeholder. The model artifact is `emotion_model.pkl` (MD5 `9a8d157c...`), trained on official GoEmotions train+val only, evaluated on the official held-out test (no leakage; the shipped pipeline's former train/test merge—validation leakage F5—was found and fixed, with clean metrics reverified).

Research experiments (Section 6.3) are fixed-seed (42), run offline against the shipped model artifact and public GoEmotions data, and logged to `research_results.json`, `research_calibration.csv`, `research_clean_in.csv` via `backend/benchmarks/run_research_experiments.py` and `run_phase9_stats.py`.

### 6.1 Discrepancy Engine Operating Point (RQ4 baseline)

Validated against 50 in-set profiles (21 discrepant, 29 matched) spanning all nine sentiment-by-biometric combinations, including edge cases (empty text, zero BPM/HRV, crisis language, negation-heavy entries), plus a 50-profile held-out suite (20 discrepant, 30 matched). Every profile's expected label was assigned from the same rule the engine implements, so the result is a rule-fidelity consistency check—it verifies the deployed binary matches its declared semantics—rather than a generalization result:

| Metric | In-set (50) | Held-out (50) |
|---|---|---|
| True positives / negatives | 21 / 29 | 20 / 30 |
| False positives / negatives | 0 / 0 | 0 / 0 |
| Accuracy | 100% | 100% |
| Per-profile latency | <0.1 ms | <0.1 ms |

The zero-false-negative property is the critical safety property, and here it holds jointly with zero false positives: the truth table fires on exactly three of nine combinations, so ambiguity lives in the regions the rule deliberately does not flag (e.g., negative+moderate), not inside the flagged region. Edge cases resolve as specified: crisis language with calm biometrics is flagged; the same language at high stress is not (consistent with the rules, since text and physiology agree); empty or minimal text, and zero or absent biometrics, are not flagged. Because expectations mirror the rule, 100% is consistency by construction—the deterministic engine's operating point is a design property, not a learned result.

### 6.2 Context Dataset Program (RQ4)

The engine's thresholds are static norms; to separate contextual from novel deviation we specify a tiered acquisition program (no data yet acquired; this is the design):

- **Tier 1 — cycle ground truth.** mcPHASES [8] (PhysioNet, free with DUA): 42 menstruators × 2×3-month intervals, daily urinary LH/E3G/PdG + Fitbit HR/HRV/sleep/temp + daily stress/sleep/mood diaries. Primary source of cycle-normalized "expected today" baselines. WHOOP/Stanford 2026 [6] and WHOOP 2024 [7] published phase curves (2,596 and 11,590 participants) enter as Bayesian priors, never as training rows.
- **Tier 2 — sleep↔HRV↔mood labels.** Figshare 2025 (18.43 GB raw 10 Hz PPG, 49 adults × 4 weeks; streamed/chunked, features extracted once and raw discarded—thermal and RAM budget constraints), NetHealth (722 students, CES-D + Fitbit), PMData (16 × 5 months, Fitbit Versa 2, daily mood/fatigue/stress/readiness), All of Us Fitbit (deferred), RADAR-MDD (deferred).
- **Tier 3 — induced-stress ground truth.** WESAD (15 subjects, chest ECG + wrist BVP, induced stress/amusement) and Stress-Predict (35 subjects, Stroop/TSST) to validate the engine's self-report↔physiology mapping. Oura ring priors provide sensor-noise evidence for HAL assumptions.
- **No-signup sets.** SSAQS (undergrads, daily stress/anxiety vs. Fitbit stress score; reported correlation 0.048 is itself a published discrepancy case), K-EmoPhone (5,582 in-situ emotion/stress labels), PhysioNet wearables (stress vs. exercise EDA/ECG/PPG), BIDSleep (Apple Watch HR + sleep-stage labels), StudentLife.
- **Training path.** (1) per-user expected RHR/RMSSD distributions conditioned on cycle phase, temperature, time of day, with WHOOP priors; (2) sleep-debt→RHR/HRV per-person shift to calibrate the residual ("novel deviation"); (3) mood–physiology discrepancy labels from mcPHASES diaries + WESAD self-reports, validated against the 23-case golden gate; (4) seasonality from PMData + WHOOP curves; (5) deterministic simulation by extending SimulatedRing with cycle-aware profiles and cycle-phase seeds, preserving CI determinism and `--strict`.

### 6.3 Calibration and Distribution-Shift Study (RQ1–RQ3)

Datasets: D_IN = GoEmotions official test (5,427 rows, real human multi-hot labels); D_CAL = GoEmotions official train split (43,410 rows) used only to fit per-class isotonic calibrators for the calibrated-counterfactual (the classifier itself was fit on 48,836 train+val rows, Section 6.0—so D_CAL is a genuinely held-out fit set for the calibrators); D_OUT = the product's own synthetic mental-health journaling templates (1,730 rows, single-emotion labelled, disclosed as synthetic and NOT clinical). Statistics computed with 1,000 paired bootstraps (seed 42) and exact-binomial McNemar tests.

#### 6.3.1 E1 — Calibration in vs. out

| Metric | IN | OUT | Delta |
|---|---|---|---|
| macro-ECE (10 bins) | 0.0902 | 0.1196 | +0.0294 (+33%) |
| micro-ECE | 0.1137 | 0.1170 | +0.0033 |
| mean(conf) − mean(acc) | +0.0902 (overconfident) | +0.1180 (overconfident) | +0.031 |
| micro-Brier | 0.0510 | 0.0724 | +0.021 (+41%) |

Bootstrap 95% CIs: ECE_IN [0.0894, 0.0911], ECE_OUT [0.1184, 0.1216], delta-ECE [0.0273, 0.0323] (excludes 0); Brier_IN [0.0503, 0.0518], Brier_OUT [0.0708, 0.0740]. The probabilities are already overconfident in-domain (supporting the calibration literature [9][10]) and become more so out-of-domain.

#### 6.3.2 E2 — Discriminative shift

| Metric | IN | OUT | Delta |
|---|---|---|---|
| micro-F1 | 0.4642 | 0.2704 | −42% |
| macro-F1 | 0.4047 | 0.3449 | −15% |
| samples-F1 | 0.4947 | 0.2990 | −40% |
| hamming acc | 0.178 | 0.092 | −48% |

The per-class F1 shifts (research_results.json) show the collapse is not uniform. Largest absolute drops: gratitude 0.862→0.361 (−0.50), neutral 0.649→0.149 (−0.50), admiration 0.598→0.153 (−0.44), love 0.766→0.504 (−0.26), approval 0.268→0.053 (−0.21), sadness 0.394→0.182 (−0.21), joy 0.448→0.294, optimism 0.442→0.297, annoyance 0.275→0.135. Classes that hold or improve: anger 0.354→0.540, curiosity 0.385→0.542, confusion 0.300→0.426, disapproval 0.295→0.447, nervousness 0.294→0.432, remorse 0.658→0.769, fear 0.517→0.554, surprise 0.416→0.491, grief 0.261→0.294, relief 0.118→0.157 (the last two have single-digit in-domain positive counts, 6 and 11, so their per-class numbers are fragile). The pattern is directly relevant to a mental-health population: the classes a clinician must not miss under shift—approval, sadness, joy, gratitude—collapse, while several high-arousal classes transfer well.

#### 6.3.3 E3 — Propagation into risk engine and discrepancy policy

Risk trigger rate (risk_score ≥ auto_trigger_threshold 8):

| Condition | IN (2000 sampled) | OUT (1730 all) |
|---|---|---|
| raw model probabilities | 1.40% | 2.77% (2.0×) |
| isotonic-calibrated reference | 0.90% | 2.83% |
| decision-flip rate (raw vs calibrated) | 0.90% | 0.87% |

McNemar on discordant pairs: IN (raw-off/cal-on 4, raw-on/cal-off 14) p = 0.031—significant at 5%, calibration removes more in-domain triggers than it adds; OUT (8/7) p = 1.00—not significant. Conclusion: calibration's effect on downstream decisions is small in-domain and swamped by the shift effect out-of-domain; the dominant mechanism is the shift of the label/score distribution, not raw-probability miscalibration. Discrepancy policy verification: negative OOD text + high-stress bio (bpm 118, hrv 22) is *not* flagged (0/131)—correct per design; neutral GoEmotions + high-stress bio is flagged (1,711/1,787, 95.7%)—per design. The discrepancy layer is deterministic; its accuracy is a policy property, not a learned result, and no further claim is made.

#### 6.3.4 E4 — Selective prediction (negative result)

| τ | IN coverage | IN sel-err | OUT coverage | OUT sel-err |
|---|---|---|---|---|
| 0.00 (always-detect) | 100% | 0.822 | 100% | 0.908 |
| 0.70 | 85.0% | 0.816 | 82.0% | 0.903 |
| 0.90 | 43.8% | 0.772 | 56.7% | 0.885 |
| 0.98 | 21.2% | 0.674 | 26.5% | 0.802 |

Max-probability abstention barely rescues reliability in-domain (error 0.82→0.67 at 21% coverage) and fails out-of-domain (0.91→0.80 at 26% coverage). The classifier's confidence is not a reliable selector under the measured shift, consistent with E1 overconfidence and the literature's calibration-first requirement. This refutes the naive mitigation RQ3-as-stated and motivates calibration-then-select.

#### 6.3.5 Hypothesis audit

| Hyp | Status | Evidence |
|---|---|---|
| H1 calibration degrades under shift | SUPPORTED | ECE 0.090→0.120, Brier 0.051→0.072 |
| H2 shift hurts discriminative performance, esp. low-arousal | SUPPORTED | micro-F1 0.464→0.270; gratitude/neutral/admiration/sadness/approval drops |
| H3 miscalibration/decision propagation | SUPPORTED (weak calibration effect) | trigger 1.4%→2.8% (shift-driven); McNemar IN p=0.031, OUT p=1.00 |
| H4 abstention preserves recall and cuts FPR | REFUTED | selective error barely improves; worst out-of-domain |

### 6.4 Cryptographic Performance

PBKDF2 at 600,000 iterations: ≈173 ms derive (benchmark logbook #0023), and a full derive–encrypt–decrypt round-trip ≈169 ms (#0030); an earlier Phase-3 benchmark recorded 233 ms at the same work factor—all measured values fall within the NIST SP 800-132 recommended 100–300 ms band [12]. Encrypt/decrypt each <1 ms at every iteration count tested, so the work factor affects only the one-time key derivation. Argon2id adds a comparable one-time login cost (time_cost 3, memory_cost 64 MiB, parallelism 4), in the OWASP-recommended range.

### 6.5 Crisis Engine Stress Test

The crisis engine is per-patient by construction: each patient owns a `CrisisState` row (`patient_username`), so separate patients hold independent state machines concurrently. Stored logbook rows exercise the compressed-time protocol (`TIME_FACTOR=20`, so 60 simulated seconds reduce to 3 real seconds): 1 concurrent patient → 101.6 ms, 5 concurrent patients → 102.3 ms, both with zero dropped threads and no stage-2 email before acknowledgement; the onset of the escalation is what produces the nominal 101 ms (which is the harness's own 0.1 s simulated settling step, not engine compute). Halt-protocol rows: acknowledgement at 15 sim-s → 750 ms and no stage-2/stage-3 yet emitted (halt applied before escalation); at 45 sim-s → 2,250 ms with stage-2 sent and stage-3 blocked (halt between escalations); at 65 sim-s → 3,266 ms with both stages already fired and further action halted. The design property the rows support is that concurrency does not drop escalation events and an acknowledgement halts further stage transitions. The benchmark's full mode supports 1/5/10/25 patients; the logbook archives the quick-mode rows (1 and 5).

### 6.6 Storage I/O

SQLite WAL vs. JSON, benchmark logbook quick mode (10 and 50 profiles, plus a 10-thread concurrent-write run):

| Storage | 10 profiles | 50 profiles |
|---|---|---|
| JSON, unencrypted | 33.4 ms total (w 3.3 / r 30.1), 2.7 KB | 23.6 ms (w 9.4 / r 14.2), 13.5 KB |
| JSON, encrypted | 38.7 ms (w 6.0 / r 32.7), 3.5 KB | 48.5 ms (w 8.9 / r 39.6), 17.3 KB |
| SQLite WAL | 35.8 ms (w 24.2 / r 11.6), 12.0 KB | 41.1 ms (w 31.9 / r 9.2), 12.0 KB |

Concurrent writes: 10 threads × 10 profiles (100 profiles) completed in 62.6 ms with zero errors. At these volumes storage is a rounding error against 5–10-year retention; the PostgreSQL path is covered by the same ORM layer, and the rate-limiter and pub/sub tables inherit the multi-worker verification of Section 6.8.

### 6.7 AI Provider Latency

In the isolated benchmark environment the only exerciseable provider is the always-available mock: the three mock rows record ≈50.5–51.3 ms (dominated by the mock's own 50 ms simulated compute), and the live Ollama and Groq rows are FAIL because the environment runs neither service—an environment condition, not a routing defect. What the rows demonstrate is the fallback machinery: Tier 3's deterministic rule engine returns a structured assessment with no external call, so summarization and risk degrade to the dependable path without blocking.

### 6.8 Multi-Worker Scaling Verification (PostgreSQL 17)

Verified against a real PostgreSQL 17 cluster: (a) `alembic upgrade head` applied the full chain cleanly; (b) cross-worker LISTEN/NOTIFY round-trip delivered a broadcast to a connection on another worker; (c) advisory-lock failover observed on leader kill; (d) DB-backed rate limiting shared one fixed-window budget across processes. (The bundled Docker Compose scaled profile pins `postgres:16-alpine`; the logbook verification above was against a genuine PG 17 cluster, and the Alembic chain is dialect-portable across both.) A pilot-scale load simulator (`scripts/sim_pilot_load.py`, up to 100 software clients) exercises the `/ring/data` push path with retries and offline-buffer bursts, but its output is not archived in the benchmark logbook, so no load-test numbers are claimed here.

---

## 7. Security Implications

### 7.1 Silent Overconfidence Is a Clinical Risk

The E1/E3 findings have a direct safety analogue: a mental-health triage signal whose probabilities degrade silently under domain shift can present the *illusion of clinical watchfulness* while missing the classes the shift most collapses—approval, sadness, joy, and gratitude (Section 6.3.2)—which are among the most relevant to a symptomatic outpatient population. This is the same failure pattern (benchmark-high, operationally broken) that distribution-shift research has documented in other safety-critical ML domains: a model evaluated on a matching distribution can appear highly capable while failing when the input distribution moves. For Sentinel this is bounded by design: the discrepancy engine is deterministic and independent of the AI pipeline, Tier 3 always returns a risk assessment, and the golden gate pins classifier bands. But the reliability evidence we report (rather than a single accuracy figure) is what lets a clinician calibrate trust.

### 7.2 The Deterministic Backstop

Because discrepancy decisions never depend on the miscalibrated model probabilities—they run on hardcoded sentiment keywords and biometric thresholds in ≈0.1 ms—the safety-relevant core does not inherit the classifier's miscalibration. The 100%/zero-FN operating point (in-set and held-out, Section 6.1), the 23-case golden gate, and the deterministic simulation (SimulatedRing) keep the CI signal reproducible. This is the architectural answer to "what happens when the model is wrong under shift": the high-risk escalation path is not gated on learned confidence.

### 7.3 Data-Layer Security for Low-Resource Clinics

Fernet at rest with a passphrase-derived key, Argon2id, fail-closed reads, a SHA-256 hash-chained audit log, device tokens stored only as hashes, and zero-trust container isolation provide PHI-grade controls on ≈200 USD hardware. Releasing `fieldcrypt` as MIT-licensed open source (21 tests) makes the cryptographic core independently auditable—an important property for a system whose deployment sites have limited technical staff and no security team.

### 7.4 Operating-Point and Escalation Policy

Crisis timings (30 s/60 s) and discrepancy thresholds are configuration, not evidence; the paper states them explicitly so deployment sites can tune before use, and the dataset program (Section 6.2) is the path to *contextual*, patient-specific baselines that reduce false escalation of luteal-phase and sleep-debt HRV dips.

---

## 8. Limitations

**Synthetic OOD domain.** D_OUT is the product's own templated journaling text, disclosed as synthetic and non-clinical; it is a genre-shift proxy with a real, measurable domain difference, but it is not real patient data. No human-subjects, IRB-eligible, or clinical claims are made; the next milestone is an ethics-board-approved pilot with 30 subjects (September 2026) comparing Sentinel's classifications against clinician assessment on the same journal and biometric data.

**Sentiment channel is bag-of-words.** Even with negation awareness, the deterministic sentiment layer cannot detect irony, sarcasm, metaphor, clinical jargon, or culturally specific expressions of distress; contextual LLM tiers address these when available, and the discrepancy core continues to function independently.

**Biometric thresholds are prototype parameters.** They are unvalidated cutoffs derived from population norms, not patient-specific; RQ4/dataset program supplies the per-person, per-day contextual baselines needed for production. Pediatric patients, cardiovascular comorbidities, and beta-blockers each require recalibration.

**Crisis timing measured only in compressed time.** The crisis and halt rows of Section 6.5 are validated under `TIME_FACTOR=20` on simulated patients; delivery latency through real email/SMS infrastructure has not been measured, so live escalation timing remains an open item for the pilot.

**Without local AI inference**, summaries degrade from context-aware generation to extractive truncation; the discrepancy engine is unaffected.

**Selective prediction refuted as shipped.** A naive confidence threshold does not restore out-of-domain reliability; this is a finding, not a failure of the method alone, and motivates calibration-then-select (isotonic/Platt before abstention) as future work.

**No formal certification.** IEC 62304, ISO 13485, ISO 14971, and medical-device regulatory review have not been performed.

**Validation scale.** The 50-profile discrepancy set and 23-case golden gate are hand-crafted; a production corpus requires several hundred annotated entries from diverse populations during an approved study.

**Dataset program not yet executed.** The Tier 1–3 sets are specified but not acquired; WHOOP raw data is not publicly available (only published effect sizes enter as priors), and gated sets (PhysioNet DUA, All of Us Workbench, RADAR-MDD) must be completed before any training run. Figshare is 18.43 GB of raw PPG requiring streamed/chunked featurization under the laptop thermal budget.

---

## 9. Conclusion and Future Work

Sentinel demonstrates that an on-premises, explainable psychophysiological triage system can be engineered at modest explicit cost and—more importantly—*reliably characterized*. Its deterministic discrepancy core matches its declared operating point exactly—100% on both the in-set and held-out 50-profile suites with zero false negatives (and zero false positives) on the safety-relevant decision, a rule-fidelity statement rather than a learned-performance claim, protected by a 23-case golden gate; its text-emotion classifier is shown, with controlled statistics, to be miscalibrated under deployment shift (macro-ECE 0.090→0.120, Brier +41%, micro-F1 0.464→0.270), to propagate that shift into a 2× risk-trigger increase while calibration itself contributes only weakly (McNemar in-domain p = 0.031, out-of-domain p = 1.00), and to defeat naive confidence abstention out-of-domain. The system's physiological thresholds must be contextualized for cycle and sleep variation before free-living patients can be monitored without escalation error; the dataset program of Section 6.2 is the concrete next step.

The immediate roadmap: live-timing validation of crisis escalations against real email/SMS delivery; IRB-approved clinical validation with 30 subjects comparing automated classification against clinician assessment; a companion mobile application for journal entry and wearable synchronization; calibration-then-select on the emotion classifier; and cycle- and sleep-aware baselines from the acquired tiered datasets, validated against the golden gate. Long-term, Sentinel is designed for turnkey deployment: a preloaded mini-PC, LAN connectivity, clinician credential configuration, and any consumer wearable exposing HR/HRV.

Across both contributions—controlled reliability methodology and contextual physiology—the broader lesson mirrors the shift-literature finding: a model evaluated under conditions that do not match deployment is effectively a different model, and a monitoring system that cannot explain *why* a value deviates cannot safely escalate. Sentinel's engineering (deterministic backstop, golden gate, cost-explicit deployment) and its research program (calibration under shift, contextual baselines) are designed to close that gap with evidence a clinician can trust.

Beneath the technical contributions is a human one. The system exists because there is no care in the unobserved hours, and because the clinicians who carry responsibility for those hours are themselves under strain—absorbing trauma narratives daily, losing time to documentation, and confronting burnout and secondary stress that now shape the workforce itself [15][16]. Sentinel's design responds on both sides: continuous observation so a deteriorating patient is noticed between appointments, and bounded, automated review so a clinician's scarce attention is spent where it is needed rather than on vigilance. Software that reduces neither the clinician's burden nor the patient's isolation is incomplete; the explicit design of both is what this platform, and its evidence about when it can and cannot be trusted, is for.

---

## Declarations

**Author contributions:** Dhansika.R is the sole author: conceptualization, research direction, engineering design, experimental design, implementation, results review and interpretation, and writing. Clinical concept consultations were held with three clinical psychologists (pre-engineering) and reviewed by one medical doctor and one additional clinical psychologist.

**Use of Generative AI and AI-Assisted Technologies:** Generative AI tools (including Anthropic Claude accessed via the OpenCode interface) were used as guided assistance. The author conceived the research direction, the architecture, and all experimental design decisions (including the calibrated-counterfactual for decision-propagation attribution and the refusal to claim learned performance for the rule-based discrepancy layer, in collaboration with the assistant), directed the experiments, reviewed every result, and verified reported metrics against experiment logs. AI assistance was used to draft benchmark scripts, generate figures and tables, and edit manuscript prose; the author takes full responsibility for scientific validity and integrity.

**Data and code availability:** All code and benchmarks are maintained in a publicly accessible repository released for review under an all-rights-reserved license; the encryption layer `fieldcrypt` is released as MIT-licensed open source. Public datasets: GoEmotions (Demszky et al. 2020) [11]; all Phase 8/9 synthetic OOD text is disclosed as product-authored and non-clinical. Tier 1–3 physiological datasets (mcPHASES, Figshare, NetHealth, PMData, WESAD, Stress-Predict, SSAQS, K-EmoPhone, BIDSleep, StudentLife) are public-by-request and none are yet acquired.

**Competing interests:** The author declares no competing interests. The pilot is funded by an Emergent Ventures award; rings are sourced from Jport (China) and financed via subscription rather than free.

**Funding:** The pilot hardware is funded by an Emergent Ventures award; no other funding agency supported this work.

---

## References

[1] World Health Organization, "Mental Health Atlas 2020," WHO, Geneva, 2021.
[2] J. Torous, J. Myrick, J. Rauseo-Ricupero, and J. Firth, "Digital mental health and COVID-19: Using technology today to accelerate the curve on access and quality tomorrow," *JMIR Mental Health*, 7(3), 2020.
[3] A. Kristjansson et al., "Validation of heart rate and heart rate variability measurement using the Oura Ring," *Journal of Medical Internet Research*, 23(2), 2021.
[4] J.-P. Onnela et al., "Harnessing smartphone-based digital phenotyping to enhance behavioral and mental health," *Neuropsychopharmacology*, 41(1), 2016.
[5] F. Shaffer and J. P. Ginsberg, "An overview of heart rate variability metrics and norms," *Frontiers in Public Health*, 5, 2017.
[6] WHOOP/Stanford, "Menstrual-cycle phase curves for RHR and RMSSD," *npj Digital Medicine*, s41746-026-02799-9, 2026.
[7] WHOOP, "Sleep–HRV/RHR effect sizes across 45,811 cycles," *npj Digital Medicine*, s41746-024-01394-0, 2024.
[8] "mcPHASES: Menstrual Cycle and Hormonal Assessment Study," PhysioNet, DOI 10.13026/zx6a-2c81.
[9] Y. Ovadia, E. Fertig, J. Ren, et al., "Can you trust your model's uncertainty? Evaluating predictive uncertainty under dataset shift," *NeurIPS*, 2019.
[10] C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger, "On calibration of modern neural networks," *ICML*, 2017.
[11] D. Demszky, D. Movshovitz-Attias, J. Ko, A. Cowen, E. Nemade, S. Ravi, "GoEmotions: A dataset of fine-grained emotions," *ACL*, 2020.
[12] National Institute of Standards and Technology, "NIST SP 800-132: Recommendation for Password-Based Key Derivation," 2010.
[13] Open Web Application Security Project, "Password Storage Cheat Sheet," OWASP, 2023.
[14] A. Niculescu-Mizil and R. Caruana, "Predicting good probabilities with supervised learning," *ICML*, 2005.
[15] C. R. Figley, "Compassion Fatigue: Coping with Secondary Traumatic Stress Disorder in Those Who Treat the Traumatized," Brunner/Mazel, 1995.
[16] C. Sinsky et al., "Allocation of physician time in ambulatory practice: A time and motion study," *Annals of Internal Medicine*, 165(11), 2016.