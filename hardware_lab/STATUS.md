# Everything working? Honest status (2026-11-15)

## YES — working and verified live

| Area | Status | Evidence |
| --- | --- | --- |
| Backend API | ✅ | `/health` 200 |
| Frontend UI | ✅ | http://127.0.0.1:5173, vite build passes |
| Login (alaya/4321, cel/1234) | ✅ | both return tokens |
| UI vitals card | ✅ | HR 83, SpO₂ 96, HRV 37, Temp 35.86, dashes for unmeasured |
| Psychological comparison `/discrepancy/check` | ✅ | 200, positive/negative sentiment both handled |
| `/agents/ring-vitals-risk` | ✅ **FIXED** | now returns bpm 83 / spo2 96 (was `unknown`/null) |
| `/agents/compliance-radar` | ✅ | ring_readings_7d: 3 |
| `/agents/relapse-indicators` | ✅ | 200, low risk |
| Timeline / plain-insights | ✅ | 200 |
| Data integrity | ✅ | only measured fields stored; no fabricated defaults/derived values |
| CI | ✅ | 222 pytest pass; ruff check + format pass |
| Ring → Sentinel pipeline | ✅ | real readings pushed via `/api/ring/data`, 13 rows in DB |

## The psychological comparison (`/discrepancy/check`)

Compares **journal text sentiment** against **biometrics** (bpm + hrv) and
flags a mismatch, e.g. "I feel great" while vitals show high stress
(bpm>=110 and hrv<=25), or "I feel awful" while vitals are calm
(bpm<=80 and hrv>=55). With our real values (bpm 83, hrv 37) it returns
`moderate` / no discrepancy — correct, not fabricated. When a mismatch is
detected it broadcasts `discrepancy_alert` to the psychologist and writes a
HIGH-severity audit entry. This is the "comparing psychological stuff" layer
and it is working.

**Bug fixed:** `ring-vitals-risk` filtered `RingSensorLog.patient_username ==
user.username`, but the caller is a psychologist (`cel`), so it always found
nothing. Now it defaults to the latest reading among the psychologist's
assigned patients, and accepts an optional `username` with an assignment check.

## Stress / fatigue ❌ NOT AVAILABLE — nothing to do

- `05 33` (body-data record: stress @8-9, fatigue @10-11) returns `0xFC`
  = **Unsupported Key**, confirmed on fresh connections. Genuinely absent
  from this firmware, not a session artefact.
- The Nordic UART debug console never printed a stress/fatigue/pressure value
  in any of the 11 captured frame logs.
- No `01 xx` stress monitor exists in the vendor constants.
- Tagged Get commands (`47 43` etc.) fixed the `0xFE` "Data error" problem,
  but `0xFC` is a different code (unsupported command) and is not fixed by tags.

This needs vendor firmware support. We are NOT inventing a stress number from
HRV — that would be fabrication, which was explicitly removed.

## Sleep ⏳ needs overnight wear

`05 04` works but returns `0000` (empty). Sleep staging requires a full night
of wear + a night rollover. Wear it to bed, query next morning.

## "Make sure the ring collects always" — DONE (`collector.py`)

A continuous collector service with:
- infinite discover → connect → collect → push → sleep → repeat loop
- **reconnection**: waits through advertising gaps (10 retries/cycle)
- **idempotency**: monotonic `seq`, safe on `(device_id, seq)` replay
- **no fabrication**: only real `0601` HR frames with plausible bpm are pushed;
  missing readings are logged as gaps, never invented
- **raw preservation**: every frame verbatim in `out/collector_frames.jsonl`
- **guaranteed cleanup**: paired stop command in `finally`, so the ring is
  never stranded in measurement mode (the cause of earlier hangs)
- **disconnect/error tracking**: `out/collector_status.json` with
  cycles / measurements / pushes / errors / gaps

Run it:
```powershell
cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
python collector.py --enable-writes            # run forever
python collector.py --enable-writes --cycles 3 # bounded test
```

Note: it needs the ring actually worn and advertising. When the ring is in
its case / stuck, the collector logs a gap and retries rather than failing or
fabricating. That is the correct "always collecting" behaviour.

## ECG ✅ captured earlier

245 `0605` waveform frames, 21,315 samples (~72 s), all CRC-valid —
`out/ecg_waveform.csv`. Single-finger wear. To capture again safely use
`probe_ecg_final.py` (stops in a `finally` block).

## Scope note

All of this is the local `sentinel3` repo. The live Render app deploys from
the separate `sentinel-mental-health` repo and is unaffected until ported.


---

## Addendum: "how does a patient actually wear it and get data into the UI?"

**Honest gap:** BLE range is ~10 m. Today the gateway is THIS laptop running
a Python script. A patient who leaves the room is out of range. See
`DEPLOY.md` for the three real options.

**Recommended pilot model (Option A): once-a-day history sync.** The ring logs
internally all day; the patient sits near the gateway once a day and we pull
the stored records. Viable because we PROVED the ring stores history
(`05 06` returned 89/85/83/74 bpm, matching live readings exactly).

New script `sync_history.py`:
- pulls `05 06` HR history and `05 09` combined records
- decodes real bpm / SpO2 / HRV / temperature using the vendor layout
- **dedupes** records seen across multiple syncs
- pushes only measured fields with idempotent `seq`
- `--from-log` verifies the decoder offline with no ring and no HTTP
- never sends delete opcodes; only the mandatory `05 80` terminal ACK

Offline verification: 4 unique HR records (89/85/83/74), 2 unique combined
records (SpO2 98/96, HRV 37, temp 36.3 C).

The ring's 4-byte timestamp bytes are NOT valid epoch-2000 seconds (they
decode to years 2040-2099), so they are treated as opaque IDs for dedupe only;
records are stamped with the sync time. No invented timestamps.

**What "send to UI" really means:** the UI reads the DB, not the ring.
`POST /api/ring/data` -> RingSensorLog/SensorReading ->
`GET /patients/me/wellness` -> Dashboard vitals card. Already verified.

Three requirements for a real deployment (in DEPLOY.md):
1. point at the right backend (`--base-url`, currently localhost only)
2. pair once per patient (`/api/ring/pair`) and store that patient's token
3. port the code changes to the live `sentinel-mental-health` repo — the live
   Render app has a separate DB and is unaffected until ported

CI after all edits: ruff check pass, ruff format pass, 222 pytest pass.


---

## Final session: live ring sync + cleanup (15 Nov 2026, ~13:54 UTC)

**The full loop ran live with the physical ring:**

    python sync_history.py --enable-writes
    -> connected to ' F085' (C1:75:21:86:F0:85)
    -> decoded 6 HR records (89/85/83/74/81/...) + 5 combined records
    -> auto-paired device
    -> 11 x POST /api/ring/data, ALL HTTP 200

Note the advertised name was just `' F085'`, not `R30 PRO F085`. The Web
Bluetooth picker filter was therefore widened to also match `F085` and the
standard `heart_rate` service (0x180D) so the ring always appears.

### Bugs found and fixed live

1. **`/me/wellness` and `ring-vitals-risk` used only the newest row.** A sync
   pushes partial rows (e.g. SpO2/HRV with no bpm), so the UI showed
   `bpm: None` and lost the heart rate. Fixed: report the most recent genuinely
   measured value PER signal across the last 50 rows. Never a default.
2. **Fake seeded vitals leaked back in.** The "latest per signal" scan picked
   up `stress: 40` / `sleep: 8.6` from 10 old `ring_alaya` rows created by
   `seed_demo.py`. Deleted those 10 rows only (accounts/journals/moods kept).
   Remaining 14 rows are all real hardware rows; zero non-null stress/sleep,
   which is correct because the ring never measures them -> UI shows dashes.
3. **`collector.py` only subscribed to `be940001`.** Real `0601` HR frames
   arrive on `be940003` (stream). Fixed: subscribes to both. A live-HR cycle
   with the ring unworn correctly produced no data (nothing fabricated).
4. **`sync_history.py` used a different device_id** (`viaking_<serial>`) than
   `collector.py`. Aligned both to `viaking_r30pro_F085` so idempotent `seq`
   keys are consistent.
5. `sync_history.py` now auto-pairs (login -> /ring/pair, handling 409) so the
   whole sync is one command.

### Current UI state (verified live)

    bpm 81 | spo2 98.0 | hrv 41 | temperature 35.86 | stress — | sleep —
    discrepancy: positive / moderate | detected False
    ring-vitals-risk: low | bpm 81 | spo2 98.0
    compliance-radar: 14 ring readings

### How to connect the ring "for now" (before hosting)

One command, ring within ~10 m, worn or just taken off (history is stored):

    cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
    python sync_history.py --enable-writes

Then open http://127.0.0.1:5173 (alaya / 4321) -> Dashboard.
For continuous live HR: `python collector.py --enable-writes --cycles 0`
(needs the ring actually worn and still).

After hosting, the browser's **Connect ring** button does the same thing
client-side (Chrome/Edge, HTTPS, one click) with a durable retry queue.

### CI after all edits
ruff check pass | ruff format pass | 222 pytest pass | tsc -b pass | vite build pass


---

## Final: comparison wired into the UI (no API-only endpoints)

### What "the comparison" is
`/api/discrepancy/check` compares a patient's **journal sentiment** against
their **biometrics** (bpm + hrv) and flags a mismatch, e.g. "I feel great" while
bpm>=110 & hrv<=25 (high stress), or "I feel awful" while calm. A mismatch
broadcasts `discrepancy_alert` to the psychologist + HIGH-severity audit entry.

### Problems cleared
1. **No page called it** -> now on BOTH:
   - `PsychTriagePage.tsx` -> "🧠 Compare journal vs wearable vitals" per patient.
   - `Dashboard.tsx` -> "🧠 Journal ↔ Vitals Comparison" card for the patient.
2. **Client could supply fake bpm/hrv** -> added server-side
   `POST /api/discrepancy/check-patient` which reads the real stored journal and
   real wearable rows from the DB. The caller cannot inject numbers.
   - RBAC: patient can compare only themselves; psychologist only assigned patients.
   - Missing data -> `insufficient_data`, never invented.
3. **`/api/agents/ring-vitals-risk` also unused in UI** -> kept as API; the two
   comparison panels now surface the same real vitals to both roles.

Verified live:
    patient own comparison: 200, bpm 81, hrv 41, neutral/moderate, no mismatch
    psych assigned patient : 200, same real values
    psych unassigned       : 404 (RBAC)
    patient someone else   : 404 (RBAC)
    wellness               : bpm 81 / spo2 98 / hrv 41 / temp 35.86 / stress — / sleep —

### CI (final)
ruff check pass | ruff format pass | 222 pytest pass | tsc -b pass | vite build pass
