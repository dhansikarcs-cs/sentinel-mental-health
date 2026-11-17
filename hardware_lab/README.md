# Sentinel — Viaking R30 PRO direct BLE lab

> **EXPERIMENTAL / NON-PRODUCTION.** This folder is intentionally outside
> `backend/` so it never enters Sentinel's CI (`ruff check backend/`), the Render
> deploy, or the clinical processing pipeline. Nothing here generates clinical
> conclusions. Do not commit `out/` or `local_secrets.json`.

## Goal

Prove a direct path: **Windows laptop → R30 PRO → genuine measurement → Sentinel**,
with no phone, no HealthWear Premium, no vendor cloud, no subscription.

Execution order (per the brief): discover → connect → map GATT → one genuine
measurement → *only then* design ingestion.

## Environment (verified on this Victus laptop)

| Item | Status |
| --- | --- |
| OS | Windows (native Python, **not WSL2**) |
| Python | 3.11.9 (`C:\Users\dhans\AppData\Local\Programs\Python\Python311\python.exe`) |
| BLE library | `bleak 3.1.0` + WinRT backends (installed) |
| Bluetooth adapter | Realtek Wireless Bluetooth Adapter — OK |
| Bluetooth radio | `Radio.state = 1` (On) |
| BLE enumerator | Microsoft Bluetooth LE Enumerator — OK |

Install once: `pip install -r requirements.txt`

## Quick start

```powershell
cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
python scan.py                      # Phase A: find the ring
python gatt.py                      # Phase B: full GATT map
python notify.py --seconds 60       # Phase D: passive raw packet capture
python measure.py --timeout 180     # FIRST SUCCESS CRITERION: wear the ring!
python bridge.py                    # Phase F: dry-run payload, sends nothing
```

Outputs land in `out/` (gitignored). Run scripts from this folder so `common.py`
resolves.

## Safety rules (enforced by the scripts)

- **No writes** to unknown/vendor characteristics.
- No reset, no DFU/firmware update, no guessed proprietary command sequences.
- No pairing changes; only standard GATT reads and CCCD subscriptions.
- Raw packets preserved verbatim in hex before any interpretation.
- All captured data labelled `viaking_r30pro_experimental` / unvalidated.

## Files

| File | Deliverable |
| --- | --- |
| `common.py` | Shared helpers, UUID name table, HR/battery parsers, streaming scan |
| `scan.py` | #2 BLE scanner (Phase A) |
| `gatt.py` | #3 GATT discovery (Phase B) |
| `notify.py` | #5 notification monitor (Phase D) |
| `measure.py` | First success criterion — captures one genuine measurement |
| `bridge.py` | #9 Sentinel integration design stub (gated, dry-run) |
| `FINDINGS.md` | #1, #7, #8, #10 — reports, matrix, feasibility, open questions |
| `out/` | #4 GATT JSON, #6 raw packet logs, captured artefacts |

## Current status (2026-11-15, REVISED)

- ✅ Laptop discovers and connects to the ring directly (no phone/app/cloud).
- ✅ Full GATT map captured (9 services); protocol identified as **Yucheng YCBT**.
- ✅ **Heart rate**: 89 / 85 / 83 bpm live + 4 stored history records.
- ✅ **SpO₂: 96 %** (needs a ~60 s measurement window - see `probe_deep.py`).
- ✅ **Blood pressure (candidate)** and **raw PPG (G/R/IR ADC)** retrieved.
- ✅ Battery 100 %, identity, WeChat step channel.
- ✅ Real readings pushed through Sentinel's `/api/ring/data` and stored with
  **only measured fields** (no fabricated values).
- ❌ ECG, temperature, HRV, sleep, stress — not obtained (see FINDINGS.md §12).
- ⚠️ Standard `0x2A37` HR service is a **decoy** (always `0400`); use `0601`.
- ⛔ Everything here is local to this repo, not the live Render deployment.

**Key lesson:** the earlier "not working" verdict was a too-short measurement
window (18-20 s), not a firmware limit. See `FINDINGS.md §12`.

## Hardware behaviour notes (observed, not inferred)

- **The ring's LEDs light up during a measurement.** The Nordic UART debug
  console emits `app_led_set 2,0,4` at measurement start. Green/red/IR LEDs
  are the PPG light source - illuminated LEDs mean the sensor is sampling,
  NOT a fault. They turn off when `03 2f {00, mode}` stops the measurement.
- **Battery is 100 %** (`0x2A19` returns `0x64`), consistent across every
  session from 09:36 to 11:13 UTC. That is a genuine reading, not a default.
- **Standard `0x2A37` always returns `0400`** ("sensor contact not detected,
  bpm 0") even while worn - it is a compatibility decoy. Real HR is `0601`.
- **Passive auto-monitor** (`hr_auto_monitor 1,60`) pushes a keepalive every
  ~60 s but no measurement frames. A measurement must be explicitly started.
- **Advertising is intermittent (~4 s bursts) and sometimes stops entirely**
  after an aborted/interrupted BLE session. A scan can return 0 devices even
  with the ring worn. Fix: reseat the ring in its charging case for a few
  seconds, then put it back on — this restarts advertising. A retry loop that
  waits for a genuine `BLEDevice` (not a cached address) is required; scripts
  should never treat the cached-address fallback as a found device.
- `0xFC` = "this history command does not exist in this firmware" and it
  aborts the rest of that session's queries - use one connection per query.
- `0xFE` = stub/short reply for capability queries on this stripped-down
  firmware; control commands still succeed.
