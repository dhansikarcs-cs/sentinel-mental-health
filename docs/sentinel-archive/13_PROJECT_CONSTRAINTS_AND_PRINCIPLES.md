# 13 — PROJECT CONSTRAINTS AND PRINCIPLES

*The non-negotiable rules of Sentinel. These override convenience, demo polish, and "it looks
better". Preserved verbatim where the founder stated them.*

---

## 1. The supreme constraint: NO FABRICATED PHYSIOLOGY `[SESSION][REPO]`

> "don't calculate stuff like hrv from bpm"
> "take all simulations away now..... take this......"
> "bro....... gimme straight" — and repeatedly: real data or nothing.

Rules:
- Every number shown must be a **real measurement from a physical wearable**.
- Nothing is invented, derived, defaulted, hardcoded, or simulated.
- Unmeasured signals stay **NULL** in the DB and render as a **dash** `—`.
- No invented `stress`, `sleep`, HRV, SpO₂, temperature, BP.
- No `sdnn = hrv * 0.8`; no `temperature = 36.5`; no `bpm = 72` fallback.
- A bpm-only push must NOT silently store four fabricated clinical values (this was found as a
  blocking data-integrity bug and fixed by making all physiological schema/model fields
  nullable with no defaults).
- Fake seeded vitals rows (10 `ring_alaya` rows with `stress:40` / `sleep:8.6`) were **deleted**;
  the remaining 14 rows are real hardware with zero non-null stress/sleep.
- The journal↔vitals comparison must read **real stored DB rows** on the server; the client may
  not supply bpm/hrv (a caller could inject fake numbers into a clinical result).
- `insufficient_data` is the correct result when a journal or vitals are missing — "Nothing is
  estimated".
- The UI must always show the vitals space (dashes + "No readings yet"), never hide it, so an
  empty account reads as a state, not a bug.

**Consequence:** `SimulatedRing` deleted, `mockHistory` removed, `hardcoded defaults` removed,
`frontend/src/constants.ts` cleaned, `backend/app/services/ring/simulated.py` deleted.

---

## 2. No clinical conclusions from unvalidated wearable measurements `[SESSION][REPO]`

- Experimental wearable data is **labelled** (`viaking_r30pro_experimental`) and "is not a
  clinical assessment".
- **No clinical ECG interpretation** — the 21,315-sample waveform is raw ADC.
- BP byte layout is an **INFERRED candidate**, never clinical.
- Stress/fatigue are **unsupported by firmware** (`05 33` → `0xFC`); sleep requires overnight
  wear. Do not promise them as live metrics.
- "Biometric thresholds are prototype parameters … unvalidated cutoffs derived from population
  norms, not patient-specific."
- Crisis timings (30s/60s) and discrepancy thresholds are **configuration / engineering policy,
  not a validated clinical protocol**.
- Canonical safety copy: "Sentinel assists monitoring. It never determines whether you are safe.
  If you feel unsafe, seek help immediately regardless of Sentinel's assessment."
- "These readings assist monitoring; they are not a clinical assessment." (Wearable Vitals card).

---

## 3. BLE / hardware constraints `[REPO][SESSION]`

- **Direct Windows BLE → Python → Sentinel.** No phone, no HealthWear app, no vendor cloud, no
  subscription, no undocumented third-party API.
- **Do not guess proprietary BLE commands.** Only documented/verified YCBT opcodes recovered
  from the vendor SDK / open-source PulseLoop.
- **Forbidden writes:** Nordic Secure DFU `0xFE59`, reset, DFU/firmware update, OTA, pairing
  changes, history deletes `05 40 … 05 4E`, any unknown/guessed characteristic write.
- The `05 80 {00}` terminal ACK is mandatory and does **not** erase ring history.
- Preserve raw packets. `hardware_lab/out/` holds verbatim frame logs (`.jsonl`), all with
  `ts_utc`, direction/channel, `raw_hex`, parsed opcode/payload/crc.
- **Separate BLE collection from clinical processing.** `hardware_lab/` is deliberately outside
  `backend/`, excluded from CI/Render deploy/clinical pipeline, marked NON-PRODUCTION.
- Normalise timestamps/units: ring 4-byte timestamps are opaque IDs (decode to years
  2040–2099), used for dedupe only; records stamped with sync time. **No invented timestamps.**
- Single-finger ECG wear — the founder corrected: "it is meant to measure with single finger";
  the vendor's two-electrode note does NOT apply to this unit. Do not repeat the two-contact
  claim.
- Browser Web Bluetooth requires HTTPS + user gesture + Chrome/Edge; **no background BLE**; a
  PWA/service worker cannot keep BLE alive.

---

## 4. Privacy-first principles `[REPO][SESSION]`

- "**Patient data + free LLM = no.** Keep AI on the local Ollama/sklearn path for the pilot, or
  pay for Groq. Free tiers may train on data."
- `ALLOW_CLOUD_AI=false` default; cloud AI is an **operator opt-in**, not an automatic fallback.
- `ENCRYPTION_REQUIRED=true` fail-closed in design; read-path hard-fail
  (`EncryptionNotReadyError`) rather than ciphertext leakage.
- Field-level Fernet encryption (22 patient-identifiable fields across 11 model classes);
  SHA-256 hash-chained audit log; HttpOnly JWT cookies; hashed ring device tokens with
  constant-time compare; HMAC-signed trustee links.
- **Never expose credentials, API keys, tokens, or sensitive patient information.** The project
  self-audits this (`SECURITY_AUDIT.md`, `Redaction_Audit.md`, video script rules). This archive
  follows the same rule — values are noted by existence/location only.
- No real patient data was used in research; all benchmark/journal data synthetic; no
  human-subjects research.
- `ENCRYPTION_REQUIRED=false` on the live pilot is an **explicit temporary exception** because
  the migrated local DB contains plaintext journals; for real patient data a fresh DB + fixed
  passphrase + fixed salt is required (the salt must never change or old journals are
  unrecoverable).
- DB-file-level encryption (SQLCipher / volume encryption) "**Must be in place before any real
  pilot data**" because numeric physiology/risk/emotion floats remain plaintext for queryability.

---

## 5. Human-authority and safety principles `[REPO]`

- "**The system flags; people decide.**" / "Nothing AI produces is authoritative until a
  clinician approves it."
- "The AI summarizes, triages, and alerts — **it never diagnoses, prescribes, or overrides
  judgment**."
- "**A false negative in a triage pipeline is lethal**" — bias toward recall inside the flagged
  region; deterministic backstop, not learned confidence, gates high-risk escalation.
- "**Nothing that runs on AI output can take autonomous clinical action — that is the
  `CrisisPolicy` boundary.**"
- AI prompt guardrails: never diagnose/prescribe/reassure clinically, never claim to be a
  therapist, never reproduce raw data (paraphrase), never invent facts, "**Safety language
  outranks tone**", two voices never mixed, JSON-only output, "NEVER do a full model training
  run for behavior fixes — persona fixes live in this prompt".
- Prohibited claims: diagnoses, treats/prevents, improved outcomes, clinically validated, "no
  existing system", improves/reliably detects, 100% generalisation.
- No formal certification (IEC 62304, ISO 13485, ISO 14971); "the system is an adjunct, not a
  monitor of record".

---

## 6. Honesty / evidence principles `[REPO][SESSION]`

- "we would rather be honest about where we are than oversell it"; "Is that real world
  generalization? No, and we say that out loud."
- Rule-consistency ≠ generalisation; circular benchmarks flagged (F1/F2/F4); validation leakage
  fixed (F5); negative results published (H4 refuted).
- "Engineering and simulated evaluations; not evidence of clinical efficacy."
- "**Never claim this is a free operation.**" / "Deployment is low-cost but never free."
- Never describe an unverified implementation as working or validated. Partially implemented,
  proposed, abandoned, and experimental work must be labelled.
- Experimental wearable data labelled; no clinical conclusions.
- Distinguish confirmed, historical, inferred and unknown information (the archive's own
  provenance rule).

---

## 7. Architecture / quality constraints `[REPO]`

- "every file has exactly one home, and every value has exactly one owner (Constitution #6). A
  change that needs the same value in two places is a bug in the architecture, not an
  opportunity."
- `api → services → repositories → models`; a route handler never touches a model directly.
- "The frontend renders, it does not orchestrate."
- One shared implementation, not two: `RingConnect`/`RingConnectButton` both call
  `syncRingNow()` from `ring/syncRing.ts`; `RingVitalsCard` is shared between patient Dashboard
  and psych Triage.
- No unnecessary redesign / no shortcuts: the founder repeatedly asked to keep the working
  stack and fix the actual problem, not rebuild. `[SESSION]`
- CI gates before committing: ruff check, ruff format --check, pytest 222, `tsc -b`, `vite build`
  from `frontend/`. Revert `backend/app/ml/model_registry.json` if dirty.
- `RING` ingestion contract: `POST /api/ring/pair` → `X-Device-Serial` + `X-Device-Token`;
  `POST /api/ring/data` with optional measured fields + `seq` + `timestamp`; idempotent on
  `(device_id, seq)`; validation ranges bpm 30–250, stress 0–100, sleep 0–24, spo2 50–100,
  hrv 0–300.

---

## 8. Operational constraints (live deployment) `[SESSION][REPO]`

- UPI-only payment; founder is a minor → 18+ account holder required (parent/guardian/
  co-founder).
- One patient, one month pilot → one VPS, SQLite, single origin; no Postgres/CloudFront needed.
- Key-only SSH; managed firewall Accept TCP 22/80/443 + default DROP (SSH rule first or lockout);
  never expose internal Docker ports (8000, 10000, 2019).
- Keep `JWT_SECRET` stable across restarts (regenerating invalidates logins).
- DNS A record before Caddy TLS; clear staging-cert state after long failed-attempt history.
- LF line endings for Linux shell scripts; exclude secrets/venv/node_modules/DB temps from deploy
  tarballs.
- Co-founder's AI keys stay as blank env vars so he can fill them later without touching deploy
  config.
- Do not push `sentinel3` to the wrong origin; the live Render app deploys from the separate
  `sentinel-mental-health` repo.

---

## 9. Licensing / legal constraint `[REPO]`

Root `LICENSE`: **All Rights Reserved** — "made available for demonstration and review purposes
only. Access to the repository does not grant any license to use, copy, or build upon the work."
`1bd8573` corrected the wording "released for review (All Rights Reserved), not open source".
Conflicts with MIT/Apache statements in `kiot/` are preserved as historical, not resolved.
`fieldcrypt` is MIT (separate repo).

---

## 10. Confidence / gaps `[UNKNOWN]`

- The full enumerated architecture constitution text is not in the accessible docs. `[UNKNOWN]`
- The founder's exact earliest wording of the no-fabrication rule is preserved from the working
  conversation, not from a file. `[SESSION]`
