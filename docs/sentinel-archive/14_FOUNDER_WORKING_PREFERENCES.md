# 14 — FOUNDER'S THINKING AND WORKING PHILOSOPHY

*Only project-relevant thinking and preferences, drawn from the working-conversation record and
the founder's own documents. This is NOT a personality profile. Provenance: `[SESSION]` from
working sessions, `[REPO]` from project documents.*

---

## 1. How the founder approaches problems `[SESSION][REPO]`

- **Start from the real thing, not a mock.** The whole project pivoted from simulated ring data
  to a physically reverse-engineered Viaking R30 PRO. When the Wellness tab showed no biodata,
  the founder asked whether it was "bcz no ring or just ui changed" — i.e. verify the actual
  data before assuming a UI explanation. `[SESSION]`
- **Ask "why" down to root cause.** Repeatedly pushed past the surface answer: "what's it???",
  "sure it'll work???", "is it completely global?", "well it can host my full thing??".
  Dislikes reassurance without verification. `[SESSION]`
- **End-to-end, not fragments.** "host sentinel whole", "it can host my full thing??", "one
  process....for both", "give them space" — wants the complete flow working, not isolated pieces.
  `[SESSION]`
- **Self-critique as a method.** Commissioned/wrote `concerns.md` with "Panel mindset: reject
  Sentinel", 43 findings, and an overall 3.8/10 deployment score; supported the IRIS claim
  audits and the F5 leakage fix. `[REPO]`

---

## 2. How technical decisions are made `[SESSION]`

- **Decisive, one answer.** "just gimme final", "nope i just want one thing", "gimme straight",
  "only one best for each". Strongly dislikes long comparison tables and repeated options. Give
  ONE recommendation with the reason, not a menu. `[SESSION]`
- **Verify before claiming.** Wants proof: "sure it'll work???", "bro u remember everything and
  stuff". When told something works, expects an actual check (bundle strings, live HTTP, tests).
  `[SESSION]`
- **No unnecessary redesign / no shortcuts.** Repeatedly corrected scope drift: "nope not a
  bundle", "nope i asked hostinger any other option", "u r forgetting quite stuffs", "u r
  mentioning spec patient to a psych not happens". Fix the actual thing; don't rebuild around it.
  `[SESSION]`
- **Constraints first.** UPI-only, global reach, minor account-holder rule, one patient / one
  month, low ops because the co-founder is inactive. `[SESSION]`
- **Honest trade-offs accepted.** Accepted "globally reachable but single-origin, not
  multi-region edge" when stated plainly; accepted "no background BLE via PWA" as a browser
  limit rather than asking for a workaround. `[SESSION]`

---

## 3. Expectations for architecture `[SESSION][REPO]`

- One place, one process, no bundle: "i don't want one hosting other managing and all only one"
  (later refined to two separate best picks, no bundle). `[SESSION]`
- Real data flowing into the real UI; BLE collection separated from clinical processing;
  `hardware_lab/` kept outside `backend/`. `[REPO][SESSION]`
- Shared implementations rather than duplicated logic (one `syncRingNow`, one `RingVitalsCard`,
  one source of truth). `[SESSION]`
- Low ops burden: "co-founder is inactive, working on AI"; AI keys left as blank env vars so he
  can fill them later without touching deploy config. `[SESSION]`
- Production config must be explicit and reproducible: prod compose, Caddyfile, bootstrap
  script, runbook. `[SESSION]`

---

## 4. Approach to research `[REPO]`

- **Evidence discipline over impressive numbers.** Chose the learned emotion classifier as the
  research subject because the discrepancy detector was circular; retracted "96% accuracy" as
  generalisation; fixed validation leakage; published the H4 negative result; "we would rather
  be honest about where we are than oversell it". `[REPO][SESSION]`
- **Formal structure:** phased programme (Phase 1&2 audit → 3&4 gaps → 5 question spec → 6&7
  lit matrix/design → 8&9 results → IRIS 10–13 manuscripts/claim audit), explicit hypotheses
  and nulls, fixed seeds, bootstrap CIs, McNemar, evidence classes [R]/[L]/[P]/[S]. `[REPO]`
- **Non-claims written down.** 7 explicit NON-claims in Phase 5; prohibited-claims table;
  required disclaimers; "no claim may exceed its evidence". `[REPO]`
- **Clinical humility.** No human-subjects/IRB/clinical-efficacy claims; thresholds labelled
  prototype parameters; dataset programme specified but not executed. `[REPO]`

---

## 5. Preferences for implementation `[SESSION][REPO]`

- **No simulations / no fabricated values** (the supreme rule — see `13`). `[SESSION]`
- **Unmeasured → NULL/dash, never invented.** "don't calculate stuff like hrv from bpm".
  `[SESSION]`
- **State must be visible.** Wants every button/state to "say" what's happening, including all
  failure reasons: "if not connecting it should say". `[SESSION]`
- **Both roles treated as people.** "first thing it's abt taking care of themself too" — the
  psychologist gets their own ring/self-care space, not a view into a patient. `[SESSION]`
- **Keep working integrations intact.** "Do not modify application code or alter working
  integrations" (archiving instruction). `[SESSION]`
- **Incremental fixes, verified.** After each change: ruff / pytest / tsc / build / live HTTP
  checks. `[SESSION]`
- **Document everything.** `hardware_lab/` docs updated multiple times; `deploy/DEPLOY.md`
  maintained as a live runbook; wants "permanent memory … outside any AI agent's memory". `[SESSION]`

---

## 6. Attitude towards AI-assisted development `[REPO][SESSION]`

- Uses AI as a **tool that must show its work**: expects the assistant to verify (read files, run
  tests, check live endpoints), not assert. `[SESSION]`
- The paper's Declarations state Generative AI ("Anthropic Claude accessed via the OpenCode
  interface") was used "to draft benchmark scripts, generate figures and tables, and edit
  manuscript prose", with the author retaining responsibility — an explicit, honest disclosure.
  `[REPO]`
- AI in the product must be **advisory, auditable, degradable, local-first**; persona fixes live
  in `scripts/sentinel_prompt.md`, not in model weights ("NEVER do a full model training run for
  behavior fixes"). `[REPO]`
- Rejects AI that "talks to distressed people" as the primary product; AI should organise
  information for clinicians. `[REPO]`

---

## 7. Expectations around explanations and reasoning `[SESSION]`

- **Short, plain, decisive.** "bro.....", "gimme straight", "just gimme final", "????" when a
  screen is unclear. Long answers and option lists cause frustration. `[SESSION]`
- **Explain what something IS before asking for a decision** (e.g. "what's it???" about a
  firewall field, "what's this ms???" about latency). Wants the concept, then the exact clicks.
  `[SESSION]`
- **Preserve reasoning, not just conclusions** — explicit instruction in the archive request:
  "Preserve reasoning, not just conclusions", "Preserve the original reasoning and nuances, not
  merely the polished description", "mark outdated information rather than silently deleting it",
  "keep conflicting historical versions when relevant". `[SESSION]`
- **Correct misreadings directly.** "u r mentioning spec patient to a psych not happens",
  "single finger", "not teen". `[SESSION]`
- Wants the assistant to **remember the whole project**, not just the current task: "bro u
  remember everything and stuff", "everything u remembered we did and then changed every filed
  attempt of 3d to pcb how we gave up and all too.... and all repo not just one". `[SESSION]`

---

## 8. Concerns about shortcuts and unnecessary redesign `[SESSION][REPO]`

- Rejected workarounds that hide problems (fake `bpm:0/hrv:0` client call was removed by the
  assistant itself for violating the no-fabrication rule). `[SESSION]`
- Rejected "workaround" framing for the minor/18+ constraint — wanted the straight legitimate
  path. `[SESSION]`
- Rejected re-architecting: wanted the existing Hostinger/VPS plan, not a new platform.
  `[SESSION]`
- Red team's verdict the founder preserved: "excellent engineering discipline aimed at the wrong
  acceptance criteria" — a self-aware critique of polish-over-validation. `[REPO]`
- "Do not simplify it into a short project summary. Do not focus only on the current
  implementation." `[SESSION]`
- "Never invent conversations, dates, results or achievements." `[SESSION]`

---

## 9. Priorities regarding ethics, privacy and quality `[SESSION][REPO]`

- **Ethics:** human authority, no diagnosis/prescription, clinician-in-the-loop, informed
  consent concerns, bias (English-only), therapeutic dependence, ethical exit (all raised in the
  founder's own `concerns.md`). `[REPO]`
- **Privacy:** local-first, "Patient data + free LLM = no", fail-closed encryption, no credentials
  committed, active redaction audits. `[REPO][SESSION]`
- **Quality:** 222 tests, 6-job CI, golden gate, ruff/tsc/build gates, live verification after
  each deploy. `[REPO][SESSION]`
- **Judge-proof honesty:** the phrase used throughout — no simulated physiology, no invented
  values, no overclaiming, no "$0 operation" claim, no "100% generalisation". `[SESSION][REPO]`
- **Completeness over brevity** for documentation: this archive exists because the founder wants
  institutional memory preserved with depth and accuracy. `[SESSION]`

---

## 10. Working-style quotes preserved `[SESSION]`

> "take all simulations away" · "don't calculate stuff like hrv from bpm" · "just gimme final" ·
> "gimme straight" · "one best for each" · "nope not a bundle and stuff" · "is it completely
> global?" · "well it can host my full thing??" · "if not connecting it should say" · "she has it
> close to her only she has it" · "sure it'll work???" · "bro u remember everything and stuff" ·
> "everything u remembered we did and then changed every filed attempt of 3d to pcb how we gave
> up and all too.... and all repo not just one" · "u r mentioning spec patient to a psych not
> happens" · "first thing it's abt taking care of themself too"

---

## 11. Confidence / gaps `[UNKNOWN]`

- This file summarises project-relevant preferences only; it intentionally omits personal
  biographical detail beyond what appears in the project's own documents (e.g. the 15-year-old /
  10th-grade self-description in `proposal.md` / `kiot/11_Team_and_Credentials.md`). `[REPO]`
- The founder's private reflective writing (`archive/thoughts/`) was deliberately not used.
  `[UNKNOWN]`
