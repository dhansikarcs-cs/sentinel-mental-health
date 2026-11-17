# What to do — exact instructions

## 1. ECG ✅ WORKING — you already did it

Single finger, normal wear, keep still. That was correct (the "second
electrode" note in the vendor docs does **not** apply to this ring).

Captured: 245 ECG waveform frames, 21,315 samples, ~72 s, all CRC-valid.
Files: `out/ecg_waveform.csv`, `out/ecg_waveform_summary.json`.

To capture again:

```powershell
cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
python probe_ecg_final.py --seconds 45
```

What you do: put the ring on ONE finger, keep that hand still for ~45 s.
Use `probe_ecg_final.py` (NOT the older `probe_ecg.py`): it sends the paired
stop commands in a `finally` block, so the ring is always released.

**IMPORTANT - why the ring stopped advertising.** The earlier successful ECG
run was interrupted before it could send the STOP commands. That left the ring
stuck in ECG streaming mode, and every scan afterwards saw 0 devices. Fix:

1. Put the ring in its charging case for ~10 s.
2. Take it out and put it back on ONE finger.
3. If a scan still finds 0 devices, toggle the laptop Bluetooth off/on.
4. Rerun `probe_ecg_final.py`.

To decode the waveform afterwards: `python decode_ecg.py`.

## 2. Stress / fatigue ❌ NOT AVAILABLE — nothing you can do

- `05 33` (body-data record, which per the vendor doc holds stress @8-9 and
  fatigue @10-11) returns `0xFC` = **Unsupported Key**. Confirmed on fresh
  connections, so it is genuinely absent from this firmware, not a session
  artefact.
- The Nordic UART debug console never printed any stress/fatigue/pressure
  value in any of the 11 captured logs.
- There is no `01 xx` stress monitor command in the vendor constants.

This needs firmware support from the vendor. No amount of wearing or
command variation will produce it. It is not exposed over BLE.

## 3. Sleep / sleepiness ⏳ NEEDS OVERNIGHT WEAR

`05 04` (sleep-stage history) IS implemented — it answers, but returns
`0000` (empty). Sleep staging is computed from a full night of wear and a
night rollover, so it cannot be produced in a short live session.

What you do:
1. Wear the ring to bed tonight (single finger, normal).
2. Tomorrow morning, with the ring still on and awake:

```powershell
cd C:\Users\dhans\Desktop\sentinel3\hardware_lab
python probe_history.py --seconds 8
```

3. Look at the `sleep_stages` section in `out/probe_history_report.json`.
   If it shows records instead of `0000`, sleep data is there.

No "sleepiness" instant score exists on this device — only staged sleep
history from overnight data.

## 4. Everything else that works, recapped

| Signal | Value | How |
| --- | --- | --- |
| Heart rate | 89 / 85 / 83 bpm | `ycbt.py --enable-writes --seconds 45` |
| SpO₂ | 96 % | `probe_deep.py --mode spo2 --seconds 90 --cooldown 20` (needs 30–60 s) |
| Temperature | 35.84–35.88 °C | `probe_discover.py --sweep --listen 120` (enables `01 20`) |
| HRV | 37 ms | combined record `05 09` `@11`, decoded by `decode_combined_official.py` |
| Battery | 100 % | `0x2A19`, or `02 00` tagged info byte @5 |
| Raw PPG | G/R/IR ADC | Nordic UART debug console |

## 5. UI (hardware-less pilot)

Already running and showing real recorded data:

- API: http://127.0.0.1:8000
- UI: http://127.0.0.1:5173 → login **alaya / 4321** → Dashboard →
  💍 Wearable Vitals (HR 83, SpO₂ 96, HRV 37, Temp 35.86, dashes for
  stress/sleep)
- To reseed after a DB reset: `python seed_recorded.py`
- Full runbook: `PILOT.md`

## Safety

All probes use documented vendor opcodes only. No DFU, no deletes, no resets,
no OTA, no guessed commands. Every start has a paired stop.
