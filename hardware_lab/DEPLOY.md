# How a real patient wears the ring and gets data into the UI

## The honest gap

BLE range is ~10 m. Today the chain is:

    R30 PRO (on finger) --BLE--> THIS WINDOWS LAPTOP (collector.py) --HTTP--> localhost:8000 --> DB --> UI

That works in a lab. It does NOT work for a patient who leaves the room.
Something must act as a **gateway** that stays near the patient.

## Three real deployment options

| Option | How it works | Good for | Cost |
| --- | --- | --- | --- |
| **A. "Connect ring" button in the hosted UI (BUILT)** | Patient opens the hosted app in Chrome/Edge, clicks **Connect ring**, browser's Web Bluetooth picker shows the nearby ring, syncs stored history into the DB, UI refreshes. No separate gateway needed. | Single-patient pilot, "opens app and it connects" | zero |
| **B. Once-a-day history sync via laptop** | `sync_history.py` / `collector.py` pull stored history and push to Sentinel. | Lab / fallback | zero |
| **C. Always-on bridge** | Raspberry Pi / mini PC / ESP32-with-WiFi runs `collector.py` 24/7 near the patient. | Continuous monitoring | ~$35–80 |
| **D. Phone companion** | Custom BLE app (NOT HealthWear, no subscription) as gateway. | Real-world mobility | app dev |

## Option A in detail (the "someone opens the app and it connects" path)

**Yes, this can work — but the connection happens in the PATIENT'S BROWSER,
not on the hosted server.** A Render server has no Bluetooth radio. Web
Bluetooth runs client-side.

Built files:
- `frontend/src/ring/ycbt.ts` — CRC16/CCITT-FALSE, frame builder/parser,
  vendor Get tags, HR (`0515`) and combined (`0518`) record decoders.
- `frontend/src/ring/webBluetooth.ts` — `connectAndSync()`: browser device
  picker → GATT connect → subscribe → handshake → pull `05 06` / `05 09` →
  mandatory `05 80` terminal ACK → decode.
- `frontend/src/components/RingConnect.tsx` — "Connect ring" button; pushes
  **only measured fields** to `/api/ring/data` with deterministic idempotent
  `seq`, temperature via `/api/sensor-readings`, then refreshes the Dashboard.
- Wired into `Dashboard.tsx`.

Verified: `tsc -b` passes, `vite build` passes, and the CRC builder reproduces
the vendor's known frame `02 00 08 00 47 43 6F EC` exactly.

### "Tab closed" / "Render free tier asleep" — resolved (2026-11-15)

Two distinct concerns, only one was a real data-loss risk:

1. **Tab closed** — NOT a data-loss problem. The ring keeps logging internally;
   the next Connect pulls everything recorded in between. No background BLE
   needed.
2. **Render free tier cold start** — WAS a real problem. Measured live:
   backend `/health` timed out at 45–60 s while the frontend answered in 0.4 s,
   and the UptimeRobot backend monitor was flagged DOWN. A push made during that
   window would have failed.

Fixes now in the client:

- **`frontend/src/ring/ringQueue.ts`** — durable IndexedDB queue. Records are
  persisted BEFORE any network call and removed ONLY after confirmed 2xx.
  Deterministic `seq` makes replays idempotent (no duplicates). Auto-flushes on
  app boot, on `online`, every 60 s, and after each sync, with backoff
  (1.5/4/9/15 s) tuned for a 30–60 s cold start.
- **`frontend/src/api/client.ts`** — `request()` retries 502/503/504 and
  network failures for GET + login (the first call that fails on a sleeping
  backend). Writes are NOT blindly retried; ring pushes go through the durable
  queue instead.
- **`frontend/src/components/RingConnect.tsx`** — enqueue-first, then flush;
  shows "N measurements waiting to upload — retrying automatically".
- **`frontend/src/main.tsx`** — flush on boot and on connectivity return.
- **Ultimate safety net:** the ring itself retains history until a successful
  sync. Even total, repeated push failure loses nothing.

Also triggered a **service restart** via the Render API (HTTP 200) after finding
the backend unresponsive. Service was `not_suspended`; last good deploy
`c0af377` is live; a Nov 5 README-only deploy shows `update_failed` but is not
the active deploy.

Remaining honest caveat: a free-tier instance WILL sleep again. The pings
reduce it and the queue makes it harmless, but for guaranteed always-on during
the 2-day pilot either keep the UptimeRobot backend monitor healthy or move to a
paid instance. Cold starts cannot be eliminated on the free plan, only survived.

### Hard constraints (be honest about these)

1. **Chrome or Edge only.** Safari and Firefox do not implement Web Bluetooth.
2. **HTTPS required** (or localhost). Render gives HTTPS.
3. **A user gesture is required** — browsers forbid silent auto-discovery. So
   it is "open app → click Connect ring → pick the device", NOT fully automatic.
4. **The ring must be within ~10 m of THAT laptop/phone**, not near the server.
5. **Only while the tab is open.** Web Bluetooth cannot collect in the
   background. This is fine *because the ring stores history internally* —
   the patient wears it all day, opens the app once a day, clicks Connect, and
   the app pulls everything recorded since the last sync. Proven: `05 06`
   returned 89/85/83/74 bpm matching live readings.
6. **Browser picker filter is `namePrefix: 'R30 PRO'`.** The ring advertises
   `R30 PRO F085`. If a unit uses a different name, widen the filter.
7. **Advertising is intermittent** and can stop after an interrupted session.
   Fix: reseat in the charging case 10 s, rewear, retry.

### For a single patient over 2 days

- Day: patient wears the ring normally (one finger). Ring logs internally.
- Once or twice a day: open the hosted app on a Chrome/Edge laptop near the
  ring → click **Connect ring** → records sync → Dashboard shows real values.
- No need to keep the tab open, no need for a phone app, no subscription.

### Still required for the LIVE app

The button code is in `sentinel3`. The live Render app deploys from the
separate `sentinel-mental-health` repo with its own DB. To make this work on
the hosted app:
1. Port `frontend/src/ring/*`, `RingConnect.tsx`, and the Dashboard change.
2. Port the backend changes (nullable sensor schema, `/me/wellness` ring
   payload, `ring-vitals-risk` fix) so pushes land correctly.
3. Serve over HTTPS (already true on Render).

Option A is viable **because we proved the ring stores history**: `05 06`
returned real records (89 / 85 / 83 / 74 bpm), and they matched the live
readings exactly. So the patient does not need to be tethered.

## What "send it to UI" actually requires

The UI never talks to the ring. It reads the **database**:

    collector / sync --> POST /api/ring/data --> RingSensorLog + SensorReading
                                                   |
                                    GET /patients/me/wellness
                                                   |
                                          Dashboard vitals card

So "send to UI" = get real rows into the DB. Already verified:
`seed_recorded.py` pushed real readings and the UI showed them.

For a real deployment, three things must be true:

1. **Point at the right backend.** `--base-url https://sentinelpsytech.com`
   (currently it defaults to `http://127.0.0.1:8000`, which only this laptop sees).
2. **Pair once per patient.** `/api/ring/pair` is called while logged in as that
   patient, and the returned device token is stored on the gateway. The token
   is what lets hardware pushes land under the right patient. Never share one
   serial/token across patients.
3. **Port the code to the live repo.** The live Render app deploys from the
   separate `sentinel-mental-health` repo. Our changes (nullable sensor schema,
   `/me/wellness` ring payload, vitals card, `ring-vitals-risk` fix) are local to
   `sentinel3` until ported. The live DB is separate too — pushing to localhost
   shows only in the localhost UI.

## Exact steps for Option A (pilot)

1. Patient wears ring all day (normal, one finger). Ring logs internally.
2. Evening: patient sits near the gateway laptop.
3. Gateway runs:
   ```powershell
   cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
   python sync_history.py --enable-writes \
       --base-url http://127.0.0.1:8000 \
       --username alaya --password 4321 \
       --serial VIAKING-R30PRO-ALAYA
   ```
4. Script pulls `05 06` (+ `05 09` combined), decodes real bpm/SpO₂/HRV/temp,
   and pushes only measured fields with idempotent `seq`.
5. Open UI → login as that patient → Dashboard shows latest real reading.

`sync_history.py --from-log` runs offline against captured frames to verify
the decoder without needing the ring.

## Option B (continuous)

Run `collector.py --enable-writes --base-url <live-url> --cycles 0` on an
always-on bridge near the patient. It reconnects through advertising gaps,
logs missing readings instead of inventing them, and always releases the ring
with a paired stop command.

## Non-negotiables

- Only measured values are pushed. Unmeasured fields stay NULL; dashes in UI.
- No derived HRV/sdnn, no hardcoded temperature, no simulated stress.
- Raw frames preserved in `out/collector_frames.jsonl`.
- Experimental wearable data is labelled and is not a clinical assessment.
- Device tokens are per-patient secrets; do not commit them.
