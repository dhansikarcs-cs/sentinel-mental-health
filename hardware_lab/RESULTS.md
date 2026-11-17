# FINAL RESULTS — Viaking R30 PRO → Sentinel

> Short version for a tired human. Take the ring off. This is the answer.

## What actually works (measured, CRC-validated, real values)

| Signal | Real values we got | Where it came from |
| --- | --- | --- |
| **Heart rate** | 89 / 85 / 83 bpm live; 4 stored history records 89/85/83/74 | `0601` live frame + `0506/0515` history |
| **SpO₂** | 96 % (intermediates 98/97/97/96), then 89 % in a later run | `0602` frame + Nordic UART ASCII debug + `0509` combined record |
| **Blood pressure (candidate)** | 98/69 and 108/73 (+ pulse 74, 100) | `0508/0517` history — appeared only after a measurement |
| **Raw PPG** | 33+ samples of G/R/IR ADC values | Nordic UART debug console (`6e400003`) |
| **Temperature (live)** | body 35.84–35.88 °C (mean 35.86), ambient 30.51–30.66 °C, 19 samples | Nordic UART debug `Env:/Skin:/BT:` after enabling `01 20` |
| **Temperature (stored)** | 36.3 °C | combined record `@13/@14` = 36.3 |
| **HRV** | 37 ms | combined record `@11` |
| **ECG waveform** | 245 frames / 21,315 samples (~72 s) | `0605` Real_UploadECG, CRC-valid |
| **Battery** | 100 % (`0x64`) | standard `0x2A19` |
| **Body sensor location** | Finger (`0x03`) | `0x2A38` |
| **Steps channel** | 0 (channel present, nothing logged) | WeChat `0xFEA1` |
| **Stored history** | HR 4 records, BP 2, combined all-day 3 | YCBT `05 xx` queries |

BP byte layout is **inferred, not documented** — candidate only, never clinical data.

## What we could NOT get, and the honest reason

| Signal | Why |
| --- | --- |
| **ECG waveform** | **CONFIRMED** — 245 `0605` frames, 21,315 int16 samples, 44,100 bytes, ~72 s continuous, all CRC-valid. `out/ecg_waveform.csv`. Single-finger wear is correct. |
| **Temperature** | ~~not exposed~~ → **WRONG, now works.** Live body temp streams on the Nordic UART debug console once `01 20` is enabled. 36.3 °C was also sitting in the combined record all along — we lacked the byte layout. Only the dedicated `051e` *history log* is rejected `0xFC`. |
| **HRV** | ~~not exposed~~ → **WRONG, partly works.** 37 ms in the combined record `@11`. The dedicated `01 45` monitor and `05 33` body-data log are rejected `0xFC`, but HRV values do appear in `05 09`. |
| **Sleep stages** | `0504` empty — needs **overnight wear and a night rollover**. Cannot be produced in a live session. |
| **Stress / fatigue** | `05 33` rejected `0xFC` (Unsupported Key) on fresh connections — genuinely absent from this firmware. No stress value ever printed on the debug console. |
| Standard `0x2A37` | Decoy — always `0400` (bpm 0, contact not detected), even worn. |

`0xFC` = "this command does not exist in this firmware" (confirmed on fresh
connections, so not a session artefact). `0xFE` = stub capability reply.

## Why "not working" kept turning out to be wrong

Three separate misdiagnoses, all corrected:

1. **SpO₂** — needed 30–60 s to converge, not 18–20 s.
2. **Temperature / HRV / SpO₂ history** — the values were in the `05 09`
   combined record the whole time. We didn't have the vendor byte layout
   (`@6` HR, `@7/@8` BP, `@9` SpO₂, `@11` HRV, `@13/@14` temp). Once
   decoded: SpO₂ 98/96/89, HRV 37 ms, temp 36.3 °C.
3. **`0xFE` stub replies** — our info queries were missing the vendor's
   required 2-byte payload tags (`02 00`→`47 43`, `02 01`→`47 46`,
   `02 03`→`47 50`). `0xFE` = "Data error", not "unsupported".

The capability sweep also mapped the real command surface: 14 `01 xx`
monitors accepted (`01 20` temperature among them), 112 rejected `0xFC`.
Enabling `01 20` produced live temperature on the debug console.


My first probes waited 18–20 s. The debug console showed the SpO₂ algorithm
needs **26+ iterations / 30–60 s** to converge:
```
No: 0 ... SpO2: 0          <- 26 iterations of no valid reading
Maybe is on finger now...
0 - SpO2: 98%,  R: 0.783, VPP: 153
3 - SpO2: 96%
algo_monitor over:1
```
A 90 s single-measurement window with a 20 s cooldown produced a valid
`0602` frame. So: **timing, not firmware**.

## Sentinel side (done)

- Removed all fake physiology: deleted `SimulatedRing`, removed `mockHistory`,
  removed hardcoded defaults (`bpm=72, stress=35, spo2=98, hrv=50,
  temperature=36.5`), stopped deriving `sdnn = hrv*0.8`.
- Verified: **222 tests pass**, ruff format clean.
- Real push through the actual API:
  ```
  POST /api/ring/data {bpm:83, spo2:96.0, seq:1} -> 200
  RingSensorLog: bpm=83 spo2=96.0 stress=None hrv=None sleep=None
  ```
  Only measured fields stored. No fabrication.

## Still open / not done

- Final capability sweep (`probe_discover.py`) was running when this was
  written — see `out/probe_discover_report.json` if it completed.
- Protocol research subagent was asked for an ECG opcode, bind/auth command,
  and the combined-record byte layout. No ECG opcode has been found publicly.
- **All changes are local to this `sentinel3` repo**, not the live Render app
  (which deploys from the separate `sentinel-mental-health` repo).
- The 10 seeded fake vitals rows in `backend/data/sentinel.db` were left in
  place, per the "keep demo accounts" choice.

## If you want to keep going later (no 4-hour wear needed)

1. ~~ECG~~ — DONE. `03 0b {01,01}` + `03 02 {02}` produced a real waveform.
2. ~~Temperature~~ — DONE. `01 20` enabled, 19 live body-temp samples decoded.
3. Sleep: wear overnight once, then query `0504`.
4. Port the cleanup to the live repo and push a real reading there.

Scripts: `scan.py`, `gatt.py`, `notify.py`, `measure.py`, `ycbt.py`,
`probe_all.py`, `probe_modes.py`, `probe_history.py`, `probe_deep.py`,
`probe_passive.py`, `probe_monitors.py`, `probe_discover.py`,
`decode_*.py`, `bridge.py`.

Safety throughout: documented opcodes only. No DFU, no deletes, no resets,
no OTA, no guessed proprietary command sequences.
