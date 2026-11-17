# 06 — RESEARCH AND INTELLECTUAL DEVELOPMENT

*Preserves the research thinking behind Sentinel: questions, formulations, hypotheses,
literature, gaps, experiments, findings, negative results, uncertainties, papers and the
evolution of our thinking. Deep detail; `10_VALIDATION_AND_EVIDENCE.md` holds the evidence
classification.*

---

## 1. Research programme overview `[REPO]`

Two overlapping numbering systems exist (kept):
- **Repository research phases** in `docs/research/`: Phase 1&2 (audit + evidence map,
  2026-09-01), Phase 3&4 (gap analysis + candidate questions), Phase 5 (formal question spec),
  Phase 6&7 (literature matrix + experimental design), Phase 8&9 (results + statistics).
  There is **no separate PHASE2 / PHASE4 / PHASE10 / PHASE11 file** in that folder — phases are
  combined.
- **IRIS research-writeup phases 10–13** in `IRIS/`: `manuscript_phase10.md` (Output A,
  ~8,271 words, full academic manuscript), `manuscript_phase11_iris.md` (Output B, 1,490 words,
  anonymised IRIS submission), `phase12_adversarial_review.md` (5 adversarial reviewers),
  `phase13_claim_audit.md` (16 headline claims, evidence classes [R]/[L]/[P]/[S]).

**Classification legend** (`PHASE1_REPO_AUDIT.md` §1): `[IMPLEMENTED]`, `[EXPERIMENTALLY
TESTED]`, `[SIMULATED]`, `[EXTERNALLY VALIDATED]`, `[PARTIALLY IMPLEMENTED]`, `[PLANNED]`,
`[UNSUPPORTED]`.

---

## 2. Research questions and problem formulations `[REPO]`

**The decisive scientific finding (Phase 1&2 audit §9):** the discrepancy detector is "a purely
rule-based, deterministic function — no learned component"; agreement is "circular by
construction (~100% once labels are aligned)"; "**It cannot, on its own, answer a meaningful
research question.**" The **emotion classifier** is "**the ONE component with**" a real label
source (GoEmotions, 48,836 human-labelled training examples), non-circular reproducible
evaluation, and measurable risk implications. "=> The most defensible research question will
center on the LEARNED emotion model…"

**Identified gaps (Phase 3&4 §2.2):** **G1** no result for lightweight TF-IDF+LR on mental-health
journaling (most shift studies in speech); **G2** whether raw OvR sigmoid probabilities are
well-calibrated in/out-of-domain; **G3** whether selective prediction / confidence abstention
improves crisis-tier/discrepancy reliability; **G4** emotion-class prior/taxonomy (28
fine-grained vs reduced valence-stress). Also: "**There is no distribution-shift / cross-domain
evaluation anywhere in the repo — this is the open gap** (addressed in Phases 6–9)."

**Candidate questions Q1–Q8** scored 0–3 on novelty/feasibility/no-overclaim/IRIS (max 12):
Q1 distribution-shift robustness **10/12**; Q2 calibration **10/12**; Q3 confidence abstention
**9/12**; Q4 taxonomy 8; Q5 shallow-NLP sufficiency 9; Q6 on-device model choice 9; Q7
discrepancy policy as engineering artefact 8 ("cannot be the empirical core"); Q8 selective
prediction as safeguard "**Too close to Q3; merge**". **Ranked shortlist: Q2 primary**, Q1 as the
distribution-shift characterisation, Q3 as practical arm — "one coherent experiment programme:
*'Calibration and distribution shift in a lightweight emotion classifier feeding a rule-based
mental-health risk / discrepancy policy, and the case for selective prediction.'*"

**Formal RQ (Phase 5), verbatim:**
> "Are the raw one-vs-rest sigmoid probabilities emitted by a lightweight (TF-IDF + Logistic Regression) multi-label emotion classifier — trained on social-media comments (GoEmotions) — calibrated, both in-domain and under a mental-health-journaling-style domain shift; and does any miscalibration propagate into the product's deterministic risk-tier and discrepancy decisions?"

**RQ-appl:** "Does confidence-based selective prediction (thresholding emotion predictions) reduce
false crisis-tier / discrepancy flags without sacrificing true positives, compared to the
current always-detect policy?"

**Paper RQ:** "To what extent does Sentinel's automated triage remain reliable when (a) its
text-classifier inputs are drawn from a deployment distribution different from training, and
(b) its physiological assumptions encounter the contextual variation of free-living patients —
and what can be done to make the system reliable under those conditions?" Sub-questions
**RQ1** (shift), **RQ2** (propagation), **RQ3** (abstention), **RQ4** (context dataset
programme).

---

## 3. Hypotheses and nulls `[REPO]`

| | Hypothesis | Null | Verdict (Phase 8&9) |
|---|---|---|---|
| H1 | ECE(OUT) > ECE(IN), overconfidence on negative emotions in journaling domain | H0_1 ECE(OUT) ≤ ECE(IN) | **SUPPORTED** |
| H2 | micro-F1(OUT) < micro-F1(IN), largest drop in low-arousal/subtle emotions | H0_2 micro-F1(OUT) ≥ micro-F1(IN) | **SUPPORTED** |
| H3 | decision-flip rate > 0, concentrated at borderline scores | H0_3 flip rate = 0 | **SUPPORTED (weak calibration effect)** |
| H4 | exists tau such that selective prediction reduces false flags while preserving ≥ recall (McNemar) | H0_4 no tau improves FPR without reducing TPR | **REFUTED — negative result, important and honest** |

Variables: IV = text domain [IN official held-out GoEmotions test | OUT synthetic templated
journaling sentences]; DVs = ECE (10 bins), Brier, reliability diagrams, per-class confidence,
micro/macro/samples-F1, decision propagation, selective precision/recall/#flags vs tau,
coverage. Controlled: single shipped `emotion_model.pkl` (MD5 pinned), fixed TF-IDF (10k
features, ngram 1–3, sublinear), fixed rule thresholds, **fixed seed 42** ("documented, not
re-run").

---

## 4. Literature exploration `[REPO]`

**Matrix L1–L13 (anchored 2020–2026):**
- **L1** Demszky et al., 2020, *GoEmotions* (arXiv:2005.00547): 58k Reddit comments, 28 labels,
  BERT-base micro-F1 0.46 / macro 0.43, annotator kappa 0.33–0.44.
- **L2** Alvarez-Gonzalez et al., 2021 (TF-IDF+LR): ~0.53 micro-F1 — Sentinel's 0.464 "in the
  normal range… a genuinely deployable lightweight alternative to Transformers on CPU/edge".
- **L3** Herath, 2025 (IJCA 187/63), *Managing Distribution Shift in Speech Emotion
  Recognition*: cross-domain collapse **0.914 → 0.266–0.311**, confidence filtering — "Direct
  template for our E4."
- **L4** arXiv 2503.22712 (2025) risk-calibrated conformal affective: raw confidence unreliable
  under shift.
- **L5** Ovadia et al., 2019 (NeurIPS) *Can you trust your model's uncertainty?* — theoretical
  anchor.
- **L6** Guo et al., 2017 (ICML) *On Calibration of Modern Neural Networks* — ECE, temperature
  scaling.
- **L7** Niculescu-Mizil & Caruana, 2005 (ICML) *Predicting Good Probabilities* — LR
  probabilities partially calibrated.
- **L8** Zadrozny & Elkan, 2002 (ICML) — OvR requires per-class calibration.
- **L9** metricgate/statstest (2026) + sklearn — "ECE > 0.10 'red flag'"; report Brier too.
- **L10** Selective prediction (Geifman & El-Yaniv 2017; Chow 1970; arXiv 2505.15008 2025) —
  selector `g(x)=1[s(x)>tau]`.
- **L11** Sci. Rep. 2024 (Rainio et al.) / MLmetrics — imbalanced multi-label metrics.
- **L12** Multiple mental-health NLP works (PMC11730989, Sci.Rep 2020, CDC/LLM crisis-transfer)
  — transformers dominate, classical lightweight rarely characterised for calibration.
- **L13** WHO / RDoC continuum framing (2024) — risk on a continuum.

**"Gap the matrix confirms" (quote):**
> "The literature contains (a) calibration-of-classical-ML, (b) shift-in-SER, and (c) selective prediction separately — but **no** study that measures *lightweight text-emotion classifier probability calibration* AND *its propagation into rule-based mental-health risk/discrepancy decisions* with *selective prediction as mitigation*. That intersection is our contribution."

**Related work (paper §4):** Torous et al. [2] ">1,500 digital mental-health applications",
"fewer than 15 percent offered offline capability and fewer than 5 percent used end-to-end
encryption"; Mindstrong "≈82% accuracy" mood prediction; Beiwe [4]; MONARCA (2012), BRiTE
(2015) — research prototypes requiring custom hardware; Liao et al. self-report–skin-conductance
mismatches predict CBT outcomes.

---

## 5. Confirmed flaws and fixes F1–F5 `[REPO]` (a core part of the intellectual history)

- **F1** (FIXED): the "96% discrepancy accuracy" benchmark tested a **divergent local copy**
  (`test_discrepancy.py:_detect_discrepancy`) with an extra `negative + moderate → True` rule the
  server lacks → "**The 96% figure does NOT characterize the deployed detector.**" Fix: import
  real `app.api.discrepancy._detect`.
- **F2** (FIXED): held-out labels derived from the same frozen rules → circular; reframed as
  *consistency*, not generalisation. Held-out labels realigned to authoritative rule
  (`negative+moderate → False`).
- **F3** (NOTED, not changed): "Mock" AI provider = fixed 50 ms sleep; "do not present mock
  latency as system latency."
- **F4** (FIXED Sep 2026): prose overstated figures (96%, 30s/60s as clinical protocol) across
  `JUDGE_QA`, `TECHNICAL_DESIGN`, `proposal_500`, `ENGINEERING_LOGBOOK`; 96% reframed as rule
  consistency; 30s/60s tagged product policy. `phase13` notes prep PDFs still quote the OLD
  framing and "PDFs need regeneration".
- **F5** (FIXED, the biggest): **validation leakage**. `train_goemotions.py` merged all three
  official splits then re-split 80/20 (seed 42), sweeping **~80% of official test rows (4,346
  of 5,427)** into training → inflated in-domain micro-F1 **0.610**. Fix: train on official
  train+validation (**48,836**) only, evaluate official test (**5,427**). Retrained
  `emotion_model.pkl` (new MD5 `9a8d157c6e42706c43b354df6d1025fc`), registry updated. Leak-free
  = micro-F1 **0.4642** / macro-F1 **0.4047** / samples-F1 **0.4947** — "matches the old
  registry numbers, confirming the model was NOT overfitting to leaked rows and the registry
  figure was honest by chance." All research experiments re-run from the clean artifact.

---

## 6. Experimental design (locked, Phase 6&7) `[REPO]`

Location `backend/benchmarks/`; fixed seed 42; all via real public API
(`EmotionClassifier.predict_proba`, `risk_engine.assess_risk_with_explainability`,
`discrepancy._detect`).
- **D_IN** = GoEmotions official test (5,427) [design originally planned test+validation =
  10,853 — a documented design-vs-execution difference]; **D_CALIB** = train split (43,410) /
  executed train+val (48,836) to fit per-class isotonic; **D_OUT** = `crisis_emotion_templates`
  (fear/sadness/grief/anger/admiration/amusement) + neutral, single-emotion labelled,
  **1,730 rows**, "disclosed as synthetic and NOT clinical", OOD proxy.
- **E1** per-class binary ECE (10 uniform bins), Brier (micro/macro), over/under-confidence.
- **E2** micro/macro/samples-F1, precision/recall (threshold 0.5), per-class largest-drop.
- **E3** feed to risk engine + discrepancy; measure % crossing `auto_trigger_threshold`;
  **calibrated-counterfactual** = per-class isotonic on D_CALIB → remap → re-run → count decision
  flips; McNemar.
- **E4** `s(x) = max over class of OvR sigmoid`; sweep tau ∈ [0,1]; coverage, selective risk,
  precision/recall, FPR/TPR; vs always-detect (tau=0).
- **Statistics:** ECE/MCE/Brier + Wilson 95% CI via **1,000 paired bootstrap resamples**;
  McNemar exact binomial; paired bootstrap difference tests.
- **Ethics:** synthetic OOD only, no real human journal data, no IRB, "never clinical".
- **Figures/tables:** F1 reliability diagrams, F2 per-class delta-F1, F3 risk-score distribution
  + decision-flip Sankey, F4 precision-recall vs coverage; T1 model card, T2 reliability table,
  T3 decision-flip matrix.

---

## 7. Research findings (Phase 8&9, paper §6.3) `[REPO]`

**E1 Calibration (raw OvR sigmoid):**
| Metric | IN | OUT | Delta |
|---|---|---|---|
| macro-ECE (10 bins) | 0.0902 | 0.1196 (0.1200 in Phase 9 stats) | +0.0294 (+33%) |
| micro-ECE | 0.1137 | 0.1170 | +0.0033 |
| mean(conf)−mean(acc) | +0.0902 | +0.1180 | +0.031 |
| micro-Brier | 0.0510 | 0.0724 | +0.021 (+41%) |

"already overconfident in-domain (ECE ~0.09 well above the ~0.02 'well-calibrated' reference)
… become more overconfident out-of-domain". Supports H1.

**E2 Discriminative shift:**
| Metric | IN | OUT | Delta |
|---|---|---|---|
| micro-F1 | 0.464 | 0.270 (0.2704) | −42% |
| macro-F1 | 0.405 | 0.345 (0.3449) | −15% |
| samples-F1 | 0.495 | 0.299 (0.2990) | −40% |
| hamming acc | 0.178 | 0.092 | −48% |

Largest per-class drops: gratitude −0.50, neutral −0.50, admiration −0.44, love −0.26,
approval 0.46→0.04, sadness 0.56→0.16, grief, optimism, joy. Preserved/improved: anger, fear,
remorse, surprise, curiosity, confusion, disapproval, nervousness ("high-arousal/emblematic
emotions survive; subtle/clinical-emotion words degrade"). Supports H2. Note: two different
per-class tables exist between `PHASE8_9_RESULTS.md` and paper §6.3.2 — `[CONFLICT]`, both kept.

**E3 Propagation:** risk trigger rate raw **1.40% → 2.77% (2.0×)**; calibrated reference
0.90% → 2.83%; decision-flip rate 0.90% / 0.87%. "the dominant effect is **domain shift on the
label/score distribution**, not raw probability calibration." McNemar IN (b=4,c=14) **p=0.031
(SIGNIFICANT)**; OUT (b=8,c=7) **p=1.00 (NOT significant)**. Discrepancy verification
(`bpm=118, hrv=22`): negative OOD texts **0/131 flagged**; neutral GoEmotions **1,711/1,787
(95.7%) flagged** — "deterministic and its 'accuracy' is a policy property, NOT a learned
result".

**E4 Selective prediction — NEGATIVE RESULT:**
| tau | IN coverage / sel err | OUT coverage / sel err |
|---|---|---|
| 0.00 | 100% / 0.822 | 100% / 0.908 |
| 0.70 | 89.7% / 0.817 | 87.7% / 0.888 |
| 0.90 | 47.3% / 0.787 | 56.1% / 0.840 |
| 0.98 | 21.2% / 0.674 | 26.5% / 0.802 |

> "**NEGATIVE RESULT — important and honest**": "max-probability confidence abstention barely rescues reliability in-domain … and **fails out-of-domain** (0.91→0.80 at 26% coverage). The classifier's confidence is *not* a reliable selector under the shift we measured". "This **REFUTES the naive mitigation H4(as-stated)**… It motivates **calibration-then-select** (Phase 10 recommendations section)." "Selective prediction NEGATIVE result is a finding, not a failure of the method alone."

**Phase 9 statistics (1,000 paired bootstraps, seed 42):** ECE_IN 0.0902
[0.0894, 0.0911], ECE_OUT 0.1200 [0.1184, 0.1216]; micro-F1_IN 0.4644 [0.4558, 0.4725],
micro-F1_OUT 0.2703 [0.2566, 0.2841]; Brier_IN 0.0510 [0.0503, 0.0518], Brier_OUT 0.0724
[0.0708, 0.0740]; delta-ECE [0.0273, 0.0323], delta-micro-F1 [0.1717, 0.2158], both exclude 0.

---

## 8. Dataset acquisition / training plan (RESEARCH — no data downloaded, no code written) `[REPO]`

`docs/research/DATASETS_TRAINING_PLAN.md`: purpose "Train Sentinel to answer *why* a biometric
reading is anomalous — cycle phase, sleep debt, and mood–physiology discrepancy — without
reading a luteal-phase HRV dip as a crisis escalation." Published priors: **HRV ±47% and RHR
±17% across the menstrual cycle**; **10% weekly sleep drop → RHR +1.2% / HRV −2.8%**. Goal:
per-person, per-day "**expected today**" baselines and "**novel deviation**".

- **Tier 1:** T1-1 **mcPHASES** (PhysioNet `mcphases/1.0.0`, DOI 10.13026/zx6a-2c81; 42
  menstruators, 2×3-month intervals, urinary LH/E3G/PdG + Fitbit + diary); T1-2 WHOOP/Stanford
  papers (Stanford 2026 `npj Digit Med` s41746-026-02799-9: 2,596 women / 42,759 cycles / 1.2M
  days; WHOOP 2024 s41746-024-01394-0: 11,590 people / 45,811 cycles) — "encode as Bayesian
  priors, never as training rows".
- **Tier 2:** T2-1 Figshare 10.6084/m9.figshare.28509740 (Sci Data 2025, **18.43 GB, 10 Hz raw
  PPG, 49 adults × 4 weeks**), T2-2 NetHealth (722 students), T2-3 PMData (16 people × 5
  months), T2-4 All of Us Fitbit (59,000+, gated), T2-5 RADAR-MDD (614, gated).
- **Tier 3:** T3-1 WESAD (15 subjects), T3-2 Stress-Predict (35), T3-3 Oura ring research
  priors ("Oura HRV ICC 0.91 vs ECG").
- **No-signup:** N-1 SSAQS (Sci Data 2026, "**reported correlation 0.048, a ready-made
  *discrepancy* validation case**"), N-2 K-EmoPhone (77 students, 5,582 ESM labels), N-3
  PhysioNet wearable stress/exercise dataset, N-4 BIDSleep (47 subjects), N-5 StudentLife.
- **Training path (5 steps):** per-user expected-today distributions → sleep-debt residual
  calibration → mood–physiology discrepancy validated against the **23-case golden set** →
  seasonality → extend `SimulatedRing` with cycle-aware profiles (keep golden `--strict`).
- **Constraints:** no dataset downloaded; gated access incomplete; WHOOP raw never training
  rows; **thermal budget (laptop heat)** for the 18.43 GB raw PPG; synthetic templates remain
  disclosed non-clinical.

**Physiological context limitation (paper §8/§6.2):** "Biometric thresholds are prototype
parameters … unvalidated cutoffs derived from population norms, not patient-specific"; pediatric
patients, cardiovascular comorbidities, beta-blockers each require recalibration; "the engine's
prototype thresholds assume a fixed adult baseline".

---

## 9. Papers, drafts and research documents `[REPO]`

- `docs/sentinel_paper.md` — **"Sentinel: An On-Premises Software Platform for Continuous
  Psychophysiological Triage — Reliability Under Distribution Shift and Physiological Context"**,
  Dhansika.R, Independent Researcher, **September 2026**, preprint not published/submitted;
  ~8,271 words / 21 pp PDF. Sections: Abstract, Keywords, Highlights, 1 Introduction,
  2 Problem Statement, 3 Research Gap, 4 Related Work (4.1–4.6), 5 System Design (5.1–5.7),
  6 Empirical Validation (6.0–6.8), 7 Security Implications (7.1–7.4), 8 Limitations,
  9 Conclusion and Future Work, Declarations, References [1]–[16].
- `IRIS/manuscript_phase10.md` (Output A), `manuscript_phase11_iris.md` (Output B),
  `phase12_adversarial_review.md` (5 reviewer personas: Calibration Methodology,
  Distribution-Shift/ML Robustness, NLP Systems/Production, Statistics/Reproducibility,
  Ethics/Safety — "All five reviewers' substantive objections are either resolved … No claim in
  the paper remains unqualified"), `phase13_claim_audit.md` (16 claims tagged [R]/[L]/[P]/[S],
  "Research-quality gate: PASS").
- `docs/research/PHASE*.md`, `docs/research/DATASETS_TRAINING_PLAN.md`,
  `IRIS_2026_SENTINEL/04_EXPERIMENTS/Experimental_Results.md`,
  `IRIS_2026_SENTINEL/09_COMPLIANCE/*` (Evidence_Classification, Medical_Claim_Audit,
  Redaction_Audit, Submission_Checklist), `kiot/02_Research_Paper.pdf`,
  `kiot/03_White_Paper.pdf`, `kiot/04_Validation_and_Timing_Report.pdf`,
  `docs/TECHNICAL_DESIGN.md`, `docs/JUDGE_QA.md`, `docs/hosting-plan.md`, `concerns.md`.
- `fieldcrypt` (separate MIT repo, extracted from Sentinel's field-level AEAD encryption,
  1 commit 2026-09-20, "21 passing tests" per paper §5.5).
- A separate related research repo `C:\Users\dhans\Desktop\research\ids-distribution-shift\`
  (IDS concept-drift paper) — related thinking on distribution shift, not part of Sentinel.
  `[REPO][INFERRED]`

---

## 10. Explicit uncertainty, disagreement, and non-claims (preserved) `[REPO]`

- "**no clinical-grade physiological validation**"; "no distribution-shift / cross-domain
  evaluation anywhere in the repo — this is the open gap"; "nothing here is clinical evidence;
  no experiment in this pipeline involves human participants"; OOD is "a proxy…
  upper-bound-optimistic"; "no human-subjects claim"; BERT comparison "literature-anchored, not
  re-run, to avoid importing unlicensed weights"; "no hardware claim"; "Lightweight = CPU-friendly,
  not necessarily best".
- Paper §8 Limitations: no clinical/IRB claims; bag-of-words limits (no irony/sarcasm/metaphor/
  clinical jargon); prototype thresholds; crisis timing measured only in compressed time
  (TIME_FACTOR=20); "no formal certification. **IEC 62304, ISO 13485, ISO 14971**, and
  medical-device regulatory review have not been performed"; validation scale (50-profile +
  23-case hand-crafted, need several hundred annotated entries); dataset programme "none are yet
  acquired".
- **Disagreements / inconsistencies kept** (also in `00` §6): discrepancy accuracy 96% vs
  100% rule-consistency; engine constants (32/60/31/3 vs 18/22/26/4); two per-class E2 tables;
  two E4 tau tables; ECE_OUT 0.1196 vs 0.1200; D_IN/D_CAL design vs execution; golden set
  10+4 vs 16+7; test counts 99 → 222; Python 3.11 vs 3.12-slim; PostgreSQL rejected vs
  verified; security finding counts 4/8/8/3 vs 4/8/7/3; storage I/O numbers; PBKDF2 latency
  154.8 / ~173 / ~169 / 233 ms.

---

## 11. Why ideas were pursued or abandoned `[REPO]`

- **Pursued:** learned emotion classifier (only non-circular component), calibration (Q2 primary),
  distribution shift (Q1), selective prediction (Q3 practical arm), physiological context
  (RQ4) because "without context, the engine conflates three distinct mechanisms: acute
  psychological stress, hormonal-cycle phase, and sleep debt", each with different clinical
  meaning and escalation action; a reliability argument "must state its confidence honestly under
  the distribution where it is deployed and must know its patient's context before treating a
  deviation as novel".
- **Abandoned / merged:** Q8 merged into Q3; Q7 discrepancy-policy relegated to position paper;
  naive confidence abstention refuted → calibration-then-select proposed; TF-IDF+LR rejected
  *for discrepancy detection* (kept for emotion tagging); custom hardware abandoned;
  "96% accuracy" reframed as rule-consistency; "100% generalization" removed claim.

---

## 12. Future research directions `[REPO]`

Live-timing validation of crisis escalations against real email/SMS delivery; **IRB-approved
clinical validation with 30 subjects** comparing automated classification against clinician
assessment; **calibration-then-select**; **cycle- and sleep-aware baselines** from acquired
tiered datasets; companion mobile app; governed longitudinal dataset; clinician feedback
learning loop; "four-model experiment" (M1–M4, SWOT); "Evidence-based escalation — transform
'AI says risk' into 'AI surfaces evidence-governed signal with context and uncertainty'".
Full roadmap: `11_FUTURE_VISION_AND_ROADMAP.md`.

---

## 13. Gaps in this archive's research coverage `[UNKNOWN]`

- Phase 2, 4, 10, 11 files do not exist as standalone files in `docs/research/` (phases are
  combined or live in `IRIS/`). `[REPO][UNKNOWN]`
- The actual CSV research result files (`research_results.json`, `research_calibration.csv`,
  `research_clean_in.csv`) under `backend/benchmarks/` were not individually opened during
  archiving; the numbers preserved here come from the phase documents and the paper. `[UNKNOWN]`
- The Phase 5 readiness gate's last item ("can the experiment script load GoEmotions test split
  locally? — Phase 6/7 setup will confirm") has no recorded completion. `[UNKNOWN]`
- Whether any IRIS/ISEF/Samsung submission was actually made, or any outcome received, is not
  in the accessible corpus. `[UNKNOWN]`
