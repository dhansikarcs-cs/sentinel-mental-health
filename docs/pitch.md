# Sentinel — 180-Second Pitch

Six sections, roughly thirty seconds each. Read them like you're telling a story, not presenting slides.

**Say the numbers like this:**
- `0.75` → "point seven five"
- `100,000` → "a hundred thousand"
- `222` → "two hundred and twenty two"
- `~72s` → "about a minute and a quarter"
- `28` → "twenty eight"
- `48,836` → "forty eight thousand, eight hundred and thirty six"
- `100%` → "a hundred percent"
- `30` → "thirty"

---

## Section 1 — The gap (0:00–0:30)

India has just point seven five psychiatrists for every hundred thousand people, which is one tenth of what the World Health Organization recommends. A working psychiatrist gets only a few minutes with each patient, and in between visits they see nothing at all. The people who need help the most are the ones nobody sees, right up until it becomes a crisis.

## Section 2 — The fix (0:30–1:00)

Sentinel closes that gap by pairing a patient's journal with wearable data: the heart rate, the heart rate variability, the stress score, and sleep. We check those two signals against each other and give the clinician one continuous view. Everything is customised per clinic and per patient: the thresholds, the tone, the cadence. It runs on the clinic's own premises, so patient data never leaves the building, and if a clinic has no hardware yet, cloud is also an option.

## Section 3 — What it does (1:00–1:30)

Underneath it sit three engines, and every one of them is deterministic and explainable. The discrepancy engine notices when the text says fine but the body disagrees. The crisis engine escalates quietly through the chain, patient to psychologist to trusted contact to helpline, and it always waits for a human to decide first. The summariser then produces a warm message for the patient and a clinical note for the psychologist, never raw text, always paraphrased.

## Section 4 — Honest, local AI (1:30–2:00)

The AI is local and honest. Ollama runs on the premises beside a twenty eight class emotion model that I trained myself, in this repo, on forty eight thousand, eight hundred and thirty six examples. Privacy is the default setting: everything is encrypted at rest, every action lands in a hash-chained audit log, and if the AI ever goes down, deterministic rules keep the whole system alive.

## Section 5 — Evidence (2:00–2:30)

When we test it, two hundred and twenty two tests pass in about a minute and a quarter across six automated jobs. The discrepancy engine shows a hundred percent rule consistency even on held out scenarios. Is that real world generalization? No, and we say that out loud. Crisis benchmarks ran with zero dropped events. This is a demonstrated prototype, and we would rather be honest about where we are than oversell it.

Thank you.