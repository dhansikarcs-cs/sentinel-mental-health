# 08 — HARDWARE AND EXPERIMENTAL RECORDS

*The custom-hardware attempt (3D → PCB → give up), the OEM pivot, the Viaking R30 PRO BLE lab,
all raw evidence, errors, limitations, and the first successful live hardware integration.
Actual measurements vs simulated/fabricated data vs assumptions/interpretations are explicitly
separated. No credentials reproduced.*

---

## PART A — THE CUSTOM-HARDWARE ATTEMPT AND ITS ABANDONMENT

### A.1 Origin: "build a custom smart ring" `[REPO][GIT]`

`docs/ENGINEERING_LOGBOOK.md` §"Pre-Git — Hardware Prototyping":

- **Late 2025:** "Started with a dream: build a custom smart ring for emotion detection. Ordered
  **MAX30102 PPG sensors**. Prototyped on **Arduino Nano**. Got heart rate readings after a week
  of I2C register hacking."
- **Early 2026:** "HRV was a nightmare on raw sensor data. Peak detection, inter-beat intervals,
  frequency-domain analysis — spent weeks getting a rolling 5-minute HRV window that didn't
  crash."

### A.2 The 3D / casing design (planned, never completed) `[REPO][INFERRED]`

`C:\Users\dhans\Desktop\boost\research_paper.md` (a *draft template* with "Your Draft Expansion
Space" placeholders) §"II. Hardware Co-Design & Digital Signal Processing" §A:

> "Map out the **3D casing file logic** and the tight spatial tolerances required to fit a
> low-power Bluetooth Low Energy (BLE) antenna, a curved lithium-polymer battery, and
> surface-mount sensor arrays (PPG and Electrodermal Activity) inside a **rigid-flex PCB
> layout**."

§B asks for "Hardware-in-the-Loop (HIL) simulation methodology … raw PPG reflections from
gold-standard clinical reference datasets (PhysioNet WESAD logs) … extract clean, mathematical
Heart Rate Variability (RMSSD) metrics." These are **planned narrative sections**, not evidence
of a completed 3D model. The founder's instruction to preserve "every failed attempt of 3D to
PCB how we gave up" is honoured here by recording that the 3D/casing work existed as design
intent and was abandoned with the rest of the custom-hardware path. `[REPO][UNKNOWN — no STL/3D
model file was found in the accessible corpus]`

### A.3 The PCB attempt (Jan 2026) — full failure record `[REPO][GIT]`

- "Designed a custom **2-layer PCB in KiCad 7.0** — **nRF52840 BLE + MAX30102**, **37 vias**.
  Sent to **JLCPCB (¥240, 12-day lead)**."
- **Failure verbatim:**
  ```
  JLinkARM.dll: Could not connect to target
  ```
  "PCB arrived. Soldered it. nRF52840 wouldn't flash. Root cause: **USB D+/D− traces were
  reversed**. Took a week to trace the schematic error."
- Paper §5.2 restates: "An nRF52840 (BLE) + MAX30102 photoplethysmography PCB fabricated at
  JLCPCB (¥240, 12-day lead-time) would not flash firmware: the USB D+/D− traces were reversed,
  and isolating the schematic error against the JLink debugger took roughly a week."

### A.4 The decision to give up (Feb 2026) — the OEM pivot `[REPO][GIT]`

Verbatim from the logbook:

> "**OEM Pivot:** Did the math. PCB rev2 = ¥240 + 12 days. **Enclosure molding = ₹15,000
> minimum**. Battery certification = months. Time = 3+ months.
> **Decision: Stop building hardware. Use consumer smart rings (Oura, Ultrahuman, Apple Watch).
> Sentinel becomes a software platform. Any device exposing HR/HRV via API is compatible.**"

Paper §5.2 adds the eliminated burdens: "**FDA 510(k)** and **FCC certification** and
procurement", reducing per-patient hardware to "≈0 marginal cost in bring-your-own-device mode";
where clinics provision rings, "hardware is financed through a **ring-as-a-service
subscription** rather than treated as free". The paper's §1 states "an **FDA 510(k)-classifiable
custom device was explicitly rejected after a failed PCB fabrication attempt**".

**Trade-off reasoning preserved:** re-spinning the board was cheap and fast (¥240, 12 days), but
the *surrounding tooling* (moulding minimum, battery certification, 3+ months) was not. This is
why the pivot happened despite the board fix being easy.

### A.5 Later KiCad artifact (May 2026) — evidence of an attempted restart `[REPO][INFERRED]`

`C:\Users\dhans\Desktop\Sentinel__\` (separate folder, not a git repo except its `.history`):
- `Sentinel__.kicad_pcb` — **79 bytes**, `(kicad_pcb (version 20260206) (generator "pcbnew")
  (generator_version "10.0")`.
- `Sentinel__.kicad_sch` — **230 bytes**, `(version 20260306) (generator "eeschema")
  (generator_version "10.0")`.
- `Sentinel__.kicad_pro` (9,736 bytes), `Sentinel__.kicad_prl` (2,636 bytes).
- LastWriteTime **2026-05-24**.

These are **near-empty stubs** — not a finished board. Interpretation: a later, short-lived
attempt to restart a KiCad design after the Feb 2026 pivot, which did not proceed. `[INFERRED]`
No schematic components, nets, or traces are present in the PCB/schematic files. `[REPO]`

### A.6 Why this matters to the product `[REPO]`

The pivot is the origin of the **Hardware Abstraction Layer (HAL)** in `docs/TECHNICAL_DESIGN.md`
§13 / paper §5.2: canonical payload `{ bpm, hrv, timestamp, source }`, adapters
`connect()`/`read()` — `SimulatedRing`, `VendorAPIRingSource` (Oura Cloud API v2, Ultrahuman),
`BLEGATTRingSource` (bleak, HRM `0x2A37`, configurable OEM maps). "Adding a device never touches
the discrepancy engine, crisis engine, or dashboards." Milestones M0 (done, 2026-08-03), M1–M3
(`docs/ROADMAP_HARDWARE.md`) follow from this pivot. **Funding:** Emergent Ventures grant
(2026-07-31); **OEM ring sourced from Jport (China)** — vendor SDK/API + BLE interface, spec
sheet pending.

---

## PART B — THE VIAKING R30 PRO BLE LAB (2026-11-15)

**Root:** `C:\Users\dhans\Desktop\sentinel3\hardware_lab\` — deliberately outside `backend/`,
excluded from CI/Render deploy/clinical pipeline, marked EXPERIMENTAL / NON-PRODUCTION.
**Environment:** Windows, native Python 3.11.9, bleak 3.1.0 + WinRT, Realtek BT adapter.
**Data label everywhere:** `viaking_r30pro_experimental`, "not clinically validated", "no
clinical conclusions". `[REPO]`

### B.1 Device identity — box claims vs measured `[REPO]`

**Box/marketing claims (NOT independently verified):** `VI AKING R30 PRO`; Bluetooth 5.3;
Nordic **nRF52832**; ECG sensor **Goodix 3228T**; PPG Goodix 3228T + 2 × SFH2703; motion
**STK8321**; NTC temp; 512 KB flash / 64 KB RAM; ring/case battery 18 mAh / 400 mAh; companion
app **HealthWear** (AliExpress calls it "Smart Health"); IP68; 4–6 days use / 10–15 days standby;
sizes 7#–13#. JSmax product page matches verbatim; no BLE/UUID/SDK info on either. Vendor
identification **LIKELY / not proven**: OEM/ODM JSmax / Jing Shin Technologies (Taiwan);
firmware+app+SDK Shenzhen Yucheng / 玉成创新 (`ycinnovate.com`); "BL" likely an ODM code.

**Actually measured over BLE:**
| Field | Observed |
|---|---|
| Advertised name | `R30 PRO F085` (also just ` F085`; YCBT device name `R30PRO`) |
| BLE MAC | `C1:75:21:86:F0:85` |
| RSSI | −32 … −76 dBm; ~4 s advertising bursts, intermittent |
| Advertised services | `0x180D` Heart Rate, `0xFEE7` WeChat pedometer |
| Manufacturer data | company id `0x7811`, payload `00000001010d000000000000000000000000640000c1752186f085` (last 6 bytes = own MAC) |
| `0x2A00` Device Name | `R30 PRO F085` |
| `0x2A01` Appearance | `0x0000` |
| `0x2A29` Manufacturer | `BL` (`424c`) — only Device Info char present |
| `0x2A19` Battery | `0x64` = **100 %** |
| `0x2A38` Body Sensor Location | `0x03` = **Finger** |
| `0x2A37` HR Measurement | **decoy** — always `0400` (bpm 0, contact not detected) even while worn |
| WeChat `0xFEA1` | `07 00 00…` (0 steps) |

**GATT map = 9 services:** `0x1800`, `0x1801`, `0x180D`, `0x180F`, `0x180A`, Nordic UART
`6e400001-…`, Nordic Secure DFU `0000fe59-…` (⚠️ DO NOT WRITE), **YCBT
`be940000-7333-be46-b7ae-689e71722bd5`**, WeChat `0000fee7-…`. YCBT channels:
`be940001` = command write + indicate; `be940002` = secondary write; `be940003` = indicate
(live `06 xx` vitals + all history data). No `0x2A39` HRCP; no `AE00` JieLi RCSP auth.

### B.2 YCBT protocol (recovered, not guessed) `[REPO]`

Sources: vendor SDK `ycbtsdk-release-4.0.11.aar`, DOCX, demo app, open-source PulseLoop.
Unencrypted, **no auth / no bonding / no subscription / no cloud / no account**.

```
[type:1][cmd:1][len:2 LE][payload:N][crc16:2 LE]
len = TOTAL frame length
CRC = CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection), little-endian
Epoch = seconds since 2000-01-01, ring's LOCAL wall-clock
```
Proof: unsolicited `ffff0600a6aa` → `CRC16(ffff0600)=0xAAA6` → bytes `a6 aa` exact match.
Vendor frame `02 00 08 00 47 43 6F EC` reproduces exactly (self-check `0xEC6F` MATCH).

**Vendor Get tags (the `0xFE` fix):** `02 00`→`4743`, `02 01`→`4746`, `02 03`→`4750`,
`02 28`→`4746`. Empty Gets returned `0xFE` "Data error"; with tags the ring returned real data.

**Opcode table (documented/verified):**
| Opcode | Meaning |
|---|---|
| `01 00 <epoch>` | SetTime |
| `02 00/01/03/28/26/1b/27` | GetDeviceInfo / GetSupportFunction / GetDeviceName / GetMeasurementFunction / keep-alive / chip scheme / GetEcgMode |
| `03 09` | broadcast_enable |
| `03 2f {01,type}` / `{00,type}` | start/stop spot measurement (`00` HR, `01` BP, `02` SpO₂, `0a` HRV) |
| `03 0b {01,01}` / `{00,01}` | AppControlWave — start/stop ECG waveform upload |
| `03 02 {02}` / `{00}` | appEcgTestStart / appEcgTestEnd |
| `03 0a {01}` | query ECG sample rate (→ `fa00` = 250 Hz) |
| `03 14` | AppECGPPGStatus (→ `fc`) |
| `07 00/01/02/06/07/10/30` | ECG/PPG raw-file history query (read-only) |
| `06 00/01/02/03/05/06/15/f0/f1` | steps / HR / SpO₂ / BP / Real_UploadECG / completion / battery / ECG HRV / RR |
| `04 0e` / `04 0b` | measurement_complete / DeviceEndECG |
| `05 02/04/06/08/09/1a/1e/2f/33` | history: activity, sleep, HR, BP, combined all-day, SpO₂, temp, comprehensive, stress/fatigue |
| `05 15/17/18` | paired data records HR/BP/combined |
| `05 80 {00}` | history terminal ACK (mandatory, does NOT erase) |

**Official return codes:** `0x00` success, `0x01` failed, `0xFB` unsupported command ID,
`0xFC` unsupported Key, `0xFD` length error, `0xFE` Data error, `0xFF` CRC error.
**Combined all-day record (`05 09`/`0518`), 20-byte stride — CONFIRMED:** `@0 ts:u32 LE`,
`@4 steps:u16`, `@6 heartRate`, `@7 systolic`, `@8 diastolic`, `@9 spo2`, `@10 respRate`,
`@11 hrv(ms)`, `@12 cvrr`, `@13 tempInt`, `@14 tempFrac`, `@15/16 bodyFat`, `@17 bloodSugar`,
`@18-19 reserved`. Temperature = `float(f"{int}.{frac}")`; filler when int==0 or frac==15.
`01 xx` monitor constants: `01 0c` HR, `01 1c` BP, `01 20` temperature, `01 26` SpO₂,
`01 45` HRV, `01 49` measurement function, `01 28` ambient. Capability sweep: **14 monitors
accepted, 112 rejected `0xFC`**.

### B.3 Every measured signal — ACTUAL values `[REPO]`

| Signal | Actual observed values | Counts |
|---|---|---|
| HR (live) | **89 / 85 / 83** (first genuine = **83 bpm**, frame `06010700533b45`) | 3 live |
| HR (history) | 89/85/83/74 → final sync 89/85/83/74/83/81 | 4 → 6 |
| SpO₂ (live) | **96 %** (payload `0x60`), intermediates 98/97/97/96; later run 89 % | — |
| SpO₂ (stored) | 98 / 96 / 89 (and 98/98 later) | 3–5 |
| Body temperature (live "BT") | **35.84–35.88 °C, mean 35.86 °C**; ambient "Env" 30.51–30.66 °C | **19 samples** |
| Temperature (stored) | **36.3 °C**; later 35.8 °C | — |
| HRV | **37 ms**; later 43 ms, 41 ms | — |
| BP (CANDIDATE, inferred) | 98/69 (pulse 74), 108/73 (pulse 100) | 2 |
| Raw PPG (G/R/IR ADC) | green/red/infrared ADC | 33+ samples |
| Battery | **100 %** | — |
| Body Sensor Location | Finger (`0x03`) | — |
| Steps channel | 0 | — |
| **ECG waveform** | **245 frames / 21,315 int16 samples / ~72 s / 44,100 bytes**; min −32768, max 32744, mean −177.89, std 15429.13, 7,488 distinct values; all CRC-valid | 245 |
| Stored history | HR 4, BP 2, combined 3 | — |

Supporting: `probe_deep_spo2.json` 210 frames; `probe_deep_bp.json` 157; `probe_deep_hrv.json`
141 (NO_DATA_ACK_ONLY); `all_signals_report.json` 65 frames logged / 26 received; standard
`0x2A37` decoy streamed `0400` for 120 s while worn.

### B.4 What FAILED / is unsupported — exact evidence `[REPO]`

- **Stress / fatigue ❌ GENUINELY ABSENT.** `05 33` (28 B: stress @8-9, fatigue @10-11)
  returns **`0xFC` = Unsupported Key**, confirmed on **fresh connections**.
  `out/probe_history_report.json`: key `05 33` verdict `REJECTED_0xFC`, payload `fc`. NUS debug
  console **never printed any stress/fatigue/pressure value in all 11 captured frame logs**.
  No `01 xx` stress monitor exists. "**Needs vendor firmware support; not inventing stress from
  HRV.**"
- **Sleep ⏳ needs overnight wear.** `05 04` answers but returns `0000` (empty); needs a night
  rollover. No instant "sleepiness" score exists.
- **Dedicated logs rejected `0xFC`:** `05 1a` (SpO₂ history), `05 1e` (temperature history),
  `05 2f` (comprehensive) — yet live SpO₂ works, so `0xFC` ≠ sensor absent.
- **HRV live/dedicated:** mode `0x0a` only enables `hr_auto_monitor 1,60`; `01 45` rejected
  `0xFC`; HRV appears only in `05 09` (@11).
- `02 27` GetEcgMode → `fc`; `03 14` ECG/PPG status → `fc`.
- **ECG wire format** was unpublished (only in vendor binary `libEcgAnaly.so`); recovered from
  disassembled SDK bytecode.

### B.5 The `0xFE` root cause and fix `[REPO]`

`0xFE` = "Data error" (official), **not** "unsupported". Our `02 xx` info queries were missing
the vendor's required 2-byte tags. With tags:
```
02 00 (4743) → 24-byte device info "93000d0100640001000000000800010082020100103f0020" (battery @5 = 0x64)
02 01 (4746) → 60-byte capability bitmap (39 set bits)
02 03 (4750) → "R30PRO" (52333050524f00)
02 28 (4746) → "0000"
02 1b → "00"    ; 03 0a {01} → "fa00" (250 Hz)
02 27 → "fc"    ; 03 14 → "fc"   (these two genuinely unsupported)
```
`sync_history.py` encodes `GET_TAGS = {0x00:"4743", 0x01:"4746", 0x03:"4750", 0x28:"4746"}`.

### B.6 FIRST SUCCESSFUL LIVE HARDWARE INTEGRATION / HISTORY SYNC `[REPO]`

- **First genuine measurement — 2026-11-15T10:34:04 UTC:** `out/first_measurement.json` —
  `status: SUCCESS`, heart rate **83 bpm**, frame `06 01`, payload hex `53`, raw
  `06010700533b45`, `crc_validated: true`, **`clinically_validated: false`**.
  `out/ycbt_session.json`: frames_sent 7, frames_received 8, hr_frames 1.
- **End-to-end ingestion verified (throwaway DB):** `POST /api/ring/data {bpm:83, spo2:96.0,
  seq:1} → 200`; `RingSensorLog: bpm=83 spo2=96.0 stress=None hrv=None sleep=None`;
  `SensorReading: hr=83 rmssd=None sdnn=None temp=None`. **Only measured fields stored.**
- **Pilot seeding:** `seed_recorded.py` pushed 3 real HR samples (89/85/83) each with spo2 96 /
  hrv 37, plus temperature 35.86 via `/api/sensor-readings`;
  `out/seed_recorded_result.json` `/me/wellness` ring = bpm 83, spo2 96.0, hrv 37, temperature
  35.86, stress null, sleep null, device_id `viaking_r30pro_F085`.
- `STATUS.md`: "Ring → Sentinel pipeline ✅ real readings pushed via `/api/ring/data`, **13 rows
  in DB**".
- **FINAL LIVE SESSION (~13:54 UTC, `STATUS.md`):** `python sync_history.py --enable-writes` →
  connected to `' F085'` → decoded **6 HR records (89/85/83/74/81/…) + 5 combined records** →
  auto-paired device → **11 × `POST /api/ring/data`, ALL HTTP 200**.
  `out/sync_seq.json` seq 11 at 13:54:29.
- **Offline `--from-log` verification:** 4 unique HR (89/85/83/74), 2 unique combined (SpO₂
  98/96, HRV 37, temp 36.3).
- **History proof:** `05 06` returned 89/85/83/74 bpm matching live readings exactly.
- **Ring 4-byte timestamps are NOT valid epoch-2000** (decode to years 2040–2099) → treated as
  **opaque IDs for dedupe only**; records stamped with sync time. **No invented timestamps.**

### B.7 ECG capture (raw ADC, NOT clinical interpretation) `[REPO]`

Command order (start ECG before info queries because one `0xFC` aborts the session):
```
01 00 <epoch>  ·  03 09  ·  03 0b {01,01}  ·  03 02 {02}  ·  75 s listen
03 02 {00}  ·  03 0b {00,01}  ·  07 00 (read-only ECG file history)
```
**245 frames** of `0605`, each 180 B = `[06][05][len=180][174 B = 87 × int16 LE][crc16]`,
**all CRC valid**. **21,315 samples**, 7,488 distinct, 44,100 bytes, window
**2026-11-15T11:48:02 → 11:49:14 UTC** (~72 s). **Single-finger wear** — the founder corrected
that "it is meant to measure with single finger"; the vendor two-electrode note does not apply to
this unit. `[SESSION]`

**Outputs:** `hardware_lab/out/ecg_waveform.csv` (21,316 lines, columns
`ts_utc,sample_index,int16_value`), `out/ecg_waveform_summary.json`, source
`out/probe_ecg_frames.jsonl` (1,387 records / 496 KB). **⚠️ `probe_ecg_report.json` does NOT
exist** — the successful run was interrupted before the report was written; neither
`probe_ecg_final_report.json` nor `probe_ecg_final_frames.jsonl` exist. `[REPO][UNKNOWN]`

### B.8 Errors, stuck states, recovery `[REPO][SESSION]`

- **Ring stuck in ECG streaming mode:** an interrupted ECG run left no advertising; every
  subsequent scan saw 0 devices. Recovery (`WHAT_TO_DO.md`): charging case ~10 s → take out,
  re-wear on ONE finger → toggle laptop Bluetooth if needed → rerun `probe_ecg_final.py`
  (stops in `finally`). Advertising is intermittent (~4 s) and can stop entirely.
- **`0xFC` poisoning:** one rejected query aborts the rest of that session → fresh connection
  per query.
- **Too-short measurement window (18–20 s) misdiagnosis:** SpO₂ needs 26+ algorithm iterations
  / 30–60 s (`SpO2: 0` ×26 → 98→97→97→96 %); a 90 s window + 20 s cooldown produced a valid
  `0602`. "Timing, not firmware."
- **Render free-tier cold start:** `/health` timed out 45–60 s while frontend answered in 0.4 s;
  UptimeRobot backend DOWN; fixed with the durable IndexedDB queue, 502/503/504 retries,
  backoff (1.5/4/9/15 s), Render API restart (HTTP 200). Last good deploy `c0af377`.
- **Live bugs fixed:** `/me/wellness` & `ring-vitals-risk` used newest row only (partial rows
  lost bpm) → latest measured value PER signal across last 50 rows; fake seeded vitals leaked
  (`stress:40` / `sleep:8.6` from 10 old `ring_alaya` rows) → deleted, 14 real rows remain;
  `collector.py` subscribed only `be940001` but real `0601` HR arrives on **`be940003`** → both;
  `sync_history.py` device_id mismatch → aligned to `viaking_r30pro_F085`; auto-pair added.
- **`0x2A05` Service Changed** refused subscription on Windows ("Access Denied");
  one-shot `BleakScanner.discover()` returned 0 devices; streaming callback scanner works.

### B.9 ACTUAL vs SIMULATED/FABRICATED vs ASSUMPTIONS (critical separation) `[REPO][SESSION]`

- **ACTUAL (CRC-validated):** all signals in §B.3, ECG waveform, battery 100 %, Finger, history
  records. Labelled `viaking_r30pro_experimental` / unvalidated.
- **SIMULATED / FABRICATED — REMOVED:** deleted `SimulatedRing`; removed `mockHistory`; removed
  hardcoded defaults (`bpm=72, stress=35, spo2=98, hrv=50, temperature=36.5`); stopped deriving
  `sdnn = hrv*0.8`. Backend `SensorDataCreate` defaults and `ring.py` hardcoded `temperature=36.5`
  were flagged as a **blocking data-integrity issue** (a bpm-only push would silently store 4
  fabricated clinical values) → made nullable/None. Fake seeded demo vitals (10 rows) deleted;
  remaining **14 rows are real hardware with zero non-null stress/sleep**.
- **ASSUMPTIONS / INTERPRETATIONS:** BP byte layout is **INFERRED** (candidate only, never
  clinical); box chip/spec claims manufacturer-printed, not independently verified; vendor
  identity LIKELY not proven; `BL` likely ODM code; `0x7811` possibly placeholder; `0x64` in
  manufacturer payload meaning unknown; `0xFEA2` `013b9ce3` meaning unknown; ring timestamps
  opaque IDs; `BT` is body temp as printed by the ring's own algorithm, not clinically
  validated; **ECG is raw ADC, not a clinical ECG interpretation**; **no clinical conclusions
  drawn anywhere**.

### B.10 Forbidden operations `[REPO]`

- Nordic Secure DFU `0xFE59` / `8ec90003-…` buttonless control point (writing `0x01` reboots
  into bootloader) — **NEVER WRITE**.
- **Reset, DFU/firmware update, OTA, pairing changes.**
- **History deletes `05 40 … 05 4E`** (never sent). Nuance: early docs said the `05 80` ACK
  "erases the ring's log, deliberately excluded"; later `sync_history.py` sends **only the
  mandatory `05 80 {00}` ACK when a terminal was seen** — an acknowledged evolution.
- **No unknown/guessed proprietary writes**; only documented opcodes; standard GATT reads +
  CCCD subscriptions otherwise. No auth/bind opcode required (none exists).
- `bridge.py` is a gated dry-run; `local_secrets.json` (device token) gitignored.

### B.11 Experiment timestamps (2026-11-15 UTC) `[REPO]`

| UTC | Event |
|---|---|
| 09:41:48 | 12 s scan, 0 devices (`scan_latest.json`) |
| 09:46:58 | `0x2A37` `0400` decoy packets |
| 09:52:14 | empty-payload handshake, `0xFE` errors |
| 10:28:45 / 10:31:31 | `all_signals_frames.jsonl` / report |
| **10:34:02–04** | **FIRST GENUINE MEASUREMENT (83 bpm)** |
| 10:37:10 | `probe_modes_report.json` |
| 10:52:48 | `genuine_measurements.json` + `probe_deep_spo2.json` (SpO₂ 96 %) |
| 10:55:59 / 10:58:42 | `probe_deep_bp.json` / `probe_deep_hrv.json` |
| 11:02:24 | `probe_history_report.json` (`0xFC` evidence) |
| 11:13:01 / 11:16:30 / 11:23:15 | passive 180 s / monitors / 144-command capability sweep |
| 11:39:36 | `seed_recorded_result.json` |
| **11:47:48–11:49:14** | **ECG session** |
| 13:52:55 | `collector_status.json` (1 cycle, 0 measurements, 1 gap, stopped) |
| **~13:54 / 13:54:29** | **FINAL LIVE RING SYNC — 11 POSTs all 200** |

`FINDINGS.md` revision chronology: §1–§11 (initial) → §12 long-window probe → §13 vendor SDK
recovered → **§14 ECG confirmed + `0xFE` root cause (FINAL)**.

### B.12 Scripts and artifacts inventory `[REPO]`

**30 Python scripts:** `common.py`, `ycbt.py`, `scan.py`, `gatt.py`, `notify.py`, `measure.py`,
`bridge.py` (helpers/core); `probe_all.py`, `analyze_all.py`, `probe_modes.py`,
`probe_history.py`, `probe_deep.py`, `probe_passive.py`, `probe_monitors.py`,
`probe_discover.py`, `probe_ecg.py`, `probe_ecg_final.py`, `inspect_ecg_replies.py` (probes);
`decode_ecg.py`, `decode_combined_official.py`, `decode_device_info.py`, `decode_history.py`,
`decode_mode.py`, `decode_nus.py`, `decode_temp.py`, `check_stress_sleep.py` (decoders);
`collector.py`, `sync_history.py`, `seed_recorded.py` (integration/sync/seed).
`requirements.txt`: `bleak>=3.0,<4`, `requests>=2.31`.

**`out/` — 39 files (24 `.json`, 14 `.jsonl`, 1 `.csv`)** including `genuine_measurements.json`,
`ecg_waveform.csv` (959 KB), `ecg_waveform_summary.json`, `temperature_hrv.json`,
`combined_decoded.json`, `device_info_decoded.json`, `all_signals_report.json`,
`probe_history_report.json`, `probe_deep_spo2.json`, `first_measurement.json`,
`ycbt_session.json`, `sync_history_result.json`, `sync_seq.json`, `probe_ecg_frames.jsonl`
(1,387 records). **Referenced but ABSENT:** `gatt_map.json`, `gatt_report.txt`,
`notifications.jsonl`, `notify_summary.json`, `probe_ecg_report.json`, `probe_ecg_final_report.json`,
`probe_ecg_final_frames.jsonl`, `probe_deep_spo2_frames.jsonl`, `seq.json`,
`collector_seq.json`, `local_secrets.json`. `[UNKNOWN]`

**Discrepancy:** `device_info_decoded.json` reports `battery_percent: 0` while its own hex has
byte @5 = `0x64` and all docs state 100 % — appears to be a stale/early artifact. `[REPO]`

### B.13 Integration architecture (two paths) `[REPO][SESSION]`

1. **Native Windows path (verified):** ring ↔ bleak/WinRT ↔ `hardware_lab/*.py` ↔
   `POST /api/ring/pair` → `X-Device-Serial` + `X-Device-Token`, or patient JWT fallback ↔
   `POST /api/ring/data`. `collector.py` = continuous always-on bridge; `sync_history.py` =
   once-a-day history pull.
2. **Browser Web Bluetooth path (hosted):** `frontend/src/ring/*` — `requestDevice` (filters
   `R30 PRO`, `F085`, `heart_rate`), YCBT handshake, `05 06`/`05 09` history, terminal ACK,
   durable IndexedDB queue, `POST /api/ring/data` with patient JWT. Requires HTTPS + user
   gesture + Chrome/Edge; **no background BLE**. `[SESSION]`

### B.14 Future hardware plans `[REPO]`

`docs/ROADMAP_HARDWARE.md` M1–M3: Jport spec request sheet (8 questions on UUIDs, byte formats,
sampling, sleep periods, battery service, pairing PIN, cloud REST, aggregation), live WS vitals,
auto-discrepancy on journal save, biometric crisis triggers (**sustained stress > 80, HR > 130,
HRV < 20** with cooldown), 30-ring Sept 2026 pilot, pair-onboarding (code/QR), device registry,
dedup/gap/backfill, Docker Compose `ring-bridge` service, token rotation tooling.
Paper §9: companion mobile app for journal + wearable sync. `[REPO][UNVERIFIED — planning]`

---

## PART C — GAPS `[UNKNOWN]`

- No 3D model / STL / CAD mesh file for the ring casing was found; the 3D-casing work survives
  only as prose in `boost/research_paper.md`. `[UNKNOWN]`
- The Jan 2026 KiCad 7.0 PCB source (the failed board) was not found on disk; only the logbook,
  paper and the May 2026 `Sentinel__/` stubs survive. `[UNKNOWN]`
- No recorded successful live BLE handshake from a **hosted browser** (Web Bluetooth path is
  built and bundle-verified but hardware-unverified). `[SESSION][UNKNOWN]`
- Whether Jport delivered a spec sheet / SDK, and M1–M3 outcomes, are not in the accessible
  corpus. `[UNKNOWN]`
