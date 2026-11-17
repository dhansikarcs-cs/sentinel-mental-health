# Sentinel — Executive summary

**A clinic-runs-it-itself mental-health triage tool that reads journals and physiology together, with a human doctor always in the loop.**

---

**The problem.** India has around 0.75 psychiatrists for every 100,000 people — roughly a tenth of the density the WHO says is a minimum. That leaves clinicians rationing their time: a few minutes per patient, no real view of what happens between visits, and crisis risk guessed from a single self-report.

**What Sentinel is.** Software a clinic installs on its own machines. A patient writes a journal entry and wears a ring; the data lands on clinic hardware and stays there. Our deterministic discrepancy engine — plain rules, zero machine learning — flag when what someone says and what their body shows disagree (e.g., a patient writing "I'm fine" while stress readings stay high for hours). A rule-based crisis engine escalates through a human chain — patient → psychologist → trusted contact → helpline — and nothing is ever sent before a person decides. A live WebSocket feed keeps the psychologist watching in real time.

**Where the AI honestly sits right now.** Our own model is still being trained, so the running build uses a hosted model (GPT-5.4) wrapped in our prompts, guardrails, and safety rules. It always paraphrases — never pastes raw journal text or raw biometrics. The design stays local-first: the day our tuned model is ready, it drops straight onto the clinic's own hardware. What's already fully ours and runs on-premises is a 28-class emotion classifier, trained in-repo on 48,836 GoEmotions entries under a leak-free train/test split. Every entry produces two views: a warm, motivating message for the patient, and a structured clinical summary (OAP format) for the psychologist. If the hosted model is down, we fall back host→local→deterministic rules so the system never just dies.

**Where we're at.** 222 tests passing (~72 seconds) across a 6-job CI pipeline. The discrepancy rules hold 100% rule-consistency across in-set and held-out scenarios — deterministic fidelity, explicitly not generalisation, we don't oversell it. Crisis benchmarks ran with zero dropped events. Journals are encrypted at rest (PBKDF2-600k + HKDF + Fernet) with hash-chained audit logging; sessions are HttpOnly JWT; ring tokens are hashed and checked in constant time.

**Demo status.** [OUTDATED — corrected Nov 2026] The line below originally described simulated ring data; that is no longer true. All simulated physiology was removed. The demo now uses genuinely measured data from a physical Viaking R30 PRO over Web Bluetooth (live `06 01` frames, CRC-validated); unmeasured signals stay NULL. This ring does not retain stored history, so readings are captured live while a browser tab stays open. Adapter SDK: BLE-GATT (real hardware path), vendor API (optional). No deterministic simulator is used.

**Demo status (historical text, retained for provenance).** The demo today runs on simulated ring data driving the real engine end-to-end. Oura, Ultrahuman, and BLE-GATT adapters are already built and tested for live hardware.

**Roadmap.** A 30-participant pilot in September 2026, a gated dataset-acquisition program for menstrual-cycle and sleep context, and clinic subscription pricing.

**In one sentence.** Sentinel gives every clinician a privacy-preserving second pair of eyes — continuous, honest, and built for the clinics that need it most.