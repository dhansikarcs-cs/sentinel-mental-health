# 15 — UNRESOLVED QUESTIONS, OPEN ITEMS AND ARCHIVE GAPS

*Everything the project has not settled, plus everything this archive could not recover. Nothing
is invented to fill a gap.*

---

## PART A — OPEN ITEMS IN THE PROJECT ITSELF

### A.1 Explicitly OPEN in the engineering decisions doc `[REPO]`
- **Refresh tokens** with HttpOnly cookie — OPEN.
- **Per-patient crisis states** — listed OPEN ("critical path for the pilot"), yet commit
  `f75600b` (2026-08-30) shipped per-patient crisis rows. This is a **documentation/code lag**,
  unresolved in the record.
- **Chart.js / D3 biometric trends** — OPEN.
- **Rate limiting** — PARTIAL (memory|db shipped; "Redis unnecessary for the target scale").
- ~8 open TODOs (logbook Stats).

### A.2 Research programme `[REPO]`
- **Phase 5 readiness gate, last item unchecked:** "can the experiment script load GoEmotions
  test split locally (network/disk)? — Phase 6/7 setup will confirm."
- **Dataset acquisition programme not executed:** "no data downloaded, no code written"
  (`DATASETS_TRAINING_PLAN.md`); paper §6.2 "**no data yet acquired; this is the design**";
  "none are yet acquired". Gated access incomplete (PhysioNet DUA, All of Us Researcher
  Workbench, RADAR-MDD consortium).
- **BRIGHTEN 271-phone study and DA Adler 2022 dataset** are "not publicly downloadable (paper
  results only)".
- **Jport spec sheet pending** (M1 blocker). "Full UUID map or only vendor app"; "raw signals vs
  aggregated wellness scores"; "bridge location (clinic LAN gateway vs user's phone" — 4 open
  questions before M1.
- **Calibration-then-select** proposed, not built. **Cycle-/sleep-aware baselines** proposed,
  not built.
- **Validation scale:** 50-profile + 23-case hand-crafted; "need several hundred annotated
  entries".
- **No formal certification:** IEC 62304, ISO 13485, ISO 14971, medical-device regulatory
  review not performed.
- **IRIS pack remaining action items:** generate PDFs, record 90-second video, add 4–6
  screenshots/graphs, convert to portal format; `phase13` notes "Prep materials still quote the
  OLD pre-audit '96%' framing … PDFs need regeneration".

### A.3 Clinical / ethical `[REPO]`
- **IRB-approved clinical validation with 30 subjects (September 2026)** — specified as the next
  milestone; no record of execution or outcome.
- **Live-timing validation of crisis escalations against real email/SMS delivery** — not done
  (only compressed-time, TIME_FACTOR=20).
- Red-team `concerns.md` 43 issues: 11 🔴 must-fix-before-pilot, 20 🟠 before psychologist
  deployment, 8 🟡 before public release — most are explicitly unresolved design/policy gaps:
  clinician-in-the-loop crisis, uncalibrated risk score with manufactured floor, SMTP silent
  failure, silent rule-mode degradation, PHI in cloud, non-durable backups, raw PHI to Groq
  without consent/DPA, no IRB, no ethical exit, no dynamic consent, English-only bias, alarm
  fatigue, no declared data controller / incident-response / breach-notification plan, no
  terms/privacy notice/minors policy, no statement of residual risk.
- **"Decide whether physiology adds value — If no → kill ring. If yes → continue."** (SWOT
  Action Plan) — not recorded as decided.
- **DB-file-level encryption** (SQLCipher / volume encryption) "Must be in place before any real
  pilot data".

### A.4 Hardware / firmware `[REPO][SESSION]`
- **Stress / fatigue unsupported** (`05 33` → `0xFC`) — needs vendor firmware support; not
  invented. **Sleep** requires overnight wear + night rollover; no instant sleepiness score.
- **BP byte layout INFERRED** — never validated clinically.
- **ECG wire format** originally unpublished; recovered from disassembled SDK. No clinical ECG
  interpretation.
- **`probe_ecg_report.json`, `probe_ecg_final_report.json`, `probe_ecg_final_frames.jsonl`**
  do not exist (interrupted run).
- **Referenced-but-absent artifacts:** `out/gatt_map.json`, `out/gatt_report.txt`,
  `out/notifications.jsonl`, `out/notify_summary.json`, `out/probe_deep_spo2_frames.jsonl`,
  `out/seq.json`, `out/collector_seq.json`, `local_secrets.json`.
- **`device_info_decoded.json` reports `battery_percent: 0`** while its own hex and all docs say
  100 % — stale artifact, unresolved.
- **No recorded successful live BLE handshake from a hosted browser.** Browser Web Bluetooth is
  built, type-checked, and bundle-verified, but the physical ring connection has only been proven
  via the native Windows/bleak path. `[SESSION]`
- **`probe_ecg_final.py` built with paired stops in `finally` but never run live.** `[SESSION]`

### A.5 Deployment / operations `[SESSION][REPO]`
- **All November 2026 changes are local/uncommitted in `sentinel3`** — nothing pushed. The live
  Render app deploys from the separate `sentinel-mental-health` repo; all local changes still
  need porting before that app benefits.
- **`c0af377` crisis-loophole fixes** live in the inaccessible repo — their exact content is
  only known from the conversation record.
- **Live VPS region not recorded** — Malaysia/Indonesia recommended for India + New Zealand
  audience, but "Boston 2" appeared in the panel earlier; `[CONFLICT]` remains unresolved.
- **UptimeRobot backend monitor status 9 (down)** and Render free-tier cold starts were observed;
  a restart returned HTTP 200 but full health after restart was not confirmed. `[HISTORICAL]`
- **Nov 5 deploy `f89cf10` `update_failed`** but inactive; last good deploy `c0af377` live.
  `[HISTORICAL]`
- **Free-tier cold starts** (45–60 s backend timeouts) remain a characteristic of the old Render
  deployment; the new VPS removes them.
- **Hostinger account-holder 18+ rule** — a parent/guardian or co-founder should be the account
  holder; not recorded as formally resolved.
- **Demo account passwords are weak** (direct DB seeds bypassing the public password policy) —
  acceptable for a demo, flagged for change if the app ever holds real data.
- **`ENCRYPTION_REQUIRED=false` on live pilot** — explicitly temporary.

### A.6 Product / positioning `[REPO]`
- **"Too many strategic identities — needs one core sentence"** (SWOT weakness).
- **Three conflicting AI-locality stories** (local Ollama now / hosted model now / Groq fallback
  "kills the local AI pitch") — unresolved `[CONFLICT]`.
- **"Human decides first" vs "auto-escalate at 30s/60s"** crisis framing — unresolved
  `[CONFLICT]`. The red team sides with the auto-escalate reading.
- **Licensing conflicts** (root All Rights Reserved vs `kiot/` MIT + Apache 2.0 footers vs
  README "Educational project" vs hosting-plan "open source (no licensing cost)").
- **Repo identity conflicts** (README says `Sentinel_V_1_` is the milestone prototype and active
  work is `sentinel-mental-health`; `kiot/00_DOCUMENT_INDEX.md` names a different main repo).
- **Statistic inconsistencies** — WHO benchmark "1 per 10,000" vs "at least 3 per 100,000";
  test counts 98/99/121/222 across generations; "96%" vs "100% rule-consistency"; pre-audit
  `0.465 / 54,263` vs leak-free `0.4642 / 48,836`.

---

## PART B — GAPS IN THIS ARCHIVE (information not accessible at compile time) `[UNKNOWN]`

1. **The actual earliest conversation** in which Sentinel was conceived is not archived verbatim.
   Earliest recoverable statements: `ENGINEERING_LOGBOOK.md` "Late 2025" hardware-dream entry and
   `archive/FOUNDERS_GUIDE.md` Streamlit-era vision. `[UNKNOWN]`
2. **The failed Jan 2026 KiCad 7.0 PCB source** (37 vias, nRF52840+MAX30102) were not found on
   disk. Only the logbook, paper §5.2, and the near-empty May 2026 `Sentinel__/` stubs survive.
3. **No STL / 3D model / CAD mesh** for the ring casing was found; the 3D work exists only as
   prose in `boost/research_paper.md` §II.A. The founder asked to preserve "every filed attempt
   of 3d to pcb how we gave up" — the give-up decision is preserved in full; per-attempt 3D
   iteration details were not recoverable. `[UNKNOWN]`
4. **Private / redacted material deliberately not reproduced:** root `.env`,
   `SECURITY_AUDIT.md` credential values, `README.md`/`SENTINEL_CODEBOOK.md` demo passwords,
   `archive/software/ACCOUNTS.md`, `.encryption_key`, personal phone number in
   `proposal.md` / `docs/proposal_sports_psychologist.md`, founder contact email in pitch deck /
   LICENSE / video script, the paper author's correspondence email. Their **existence and
   location** are noted in `16_ARCHIVE_INDEX.md` §source inventory. `[UNKNOWN]`
5. **`archive/thoughts/`** — private chat transcript (`sentinel.txt` contains apparent login
   credentials, session token/hash, "Mnemonic for login (keep it secret)"), personal reflective
   writing (`30,08,2026.txt`), and 14 WhatsApp images — intentionally not quoted. `[UNKNOWN]`
6. **PDF artifacts not opened:** `kiot/*.pdf` (11 PDFs), `docs/*.pdf`,
   `MindRise_Hub_Administrative_Project_Paper.pdf`, `test.pdf`. Indexed by filename/size only.
7. **Root ZIP artifacts not inspected:** `.docker.zip` (~594 MB), `compliance.zip`, `link.zip`,
   `tested.zip`, `IRIS_2026_SENTINEL.zip`. A possible prior/parallel identity ("MindRise Hub")
   is flagged but not interpreted. `[UNKNOWN]`
8. **`docs - Copy/`** is an undated snapshot of an older docs generation; its exact date and
   relationship to `docs/` is not recorded. `[UNKNOWN]`
9. **The `sentinel-mental-health` repository is not on this disk.** Its git history, the exact
   `c0af377` contents, and its deploy configuration could not be inspected. `[UNKNOWN]`
10. **Other sibling Desktop folders** (`boards/`, `derive/`, `TKS/`, `portfolio/`, `10-b/`,
    `Association Team/`, `noted/`, `un policy/`, `research os/`, `github/` networking repos,
    `dhka log/`) were surveyed by filename only; only `boost/`, `fieldcrypt`, and
    `research/ids-distribution-shift` were identified as Sentinel-relevant. `[UNKNOWN][INFERRED]`
11. **Competition outcomes** — whether IRIS / ISEF / Samsung Solve for Tomorrow submissions were
    made, and any results, are not in the accessible corpus. `[UNKNOWN]`
12. **The three clinical-psychologist consultations** and the "one medical doctor and one
    additional clinical psychologist" endorsement (paper Declarations) have no underlying
    records. `[UNKNOWN]`
13. **Research result CSV/JSON files** in `backend/benchmarks/` (`research_results.json`,
    `research_calibration.csv`, `research_clean_in.csv`) were not individually opened; numbers
    in this archive come from the phase documents and the paper. `[UNKNOWN]`
14. **Full enumerated architecture constitution** text is referenced (#5, #6, #8) but not present
    in the accessible docs. `[UNKNOWN]`
15. **Exact dates for November 2026 working-session events** are inferred from file timestamps and
    the conversation record, not git commits. `[INFERRED]`
16. **`Sentinel_V_1_/` Azure deployment files** (`Dockerfile.azure`, `azure-startup.sh`,
    `build-azure-deploy.sh`, `docs/DEPLOY_AZURE.md`) were listed but not read in full; whether
    Azure was ever used is not recorded. `[UNKNOWN]`
17. **`boost/` other documents** (`patent.md`, `policy.md`, `CAIDP.md`, `ITU.md`, `SAT.md`,
    `10th_90.md`, `12th_90.md`, `cover.md`, `if_needed_git.md`, `boost_mun.md`) were not read;
    only `research_paper.md` (3D/PCB section) was cited. `[UNKNOWN]`
18. **An earlier, possibly separate project identity** "MindRise Hub" / "MindRise*" files
    (`MindRise_Hub_Administrative_Project_Paper.pdf`, `.gitignore` MindRise* entry,
    `IRIS/` acronym). Flagged, not interpreted. `[UNKNOWN]`

---

## PART C — HOW TO EXTEND THIS ARCHIVE

- If `sentinel-mental-health` becomes accessible, port its git history and crisis-loophole commit
  `c0af377`.
- If the Jan 2026 KiCad project or STL files surface, add them to `08_HARDWARE_AND_EXPERIMENTS.md`
  §A.
- If a live hosted-browser BLE handshake succeeds, record the evidence in
  `10_VALIDATION_AND_EVIDENCE.md` and update the "implemented, not hardware-verified" status in
  `05_TECHNICAL_IMPLEMENTATION.md` §10.
- If the 30-subject IRB pilot occurs, update `11_FUTURE_VISION_AND_ROADMAP.md` and
  `10_VALIDATION_AND_EVIDENCE.md`.
- When the founder resolves any `[CONFLICT]` (AI locality, crisis framing, licensing, region),
  **keep both versions** — the archive's rule is to mark, not delete.
