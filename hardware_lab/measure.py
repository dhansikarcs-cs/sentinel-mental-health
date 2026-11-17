"""FIRST SUCCESS CRITERION: Windows laptop -> R30 PRO -> one genuine measurement.

Usage:
    python measure.py                       # waits up to 90s for a real HR
    python measure.py --timeout 180
    python measure.py --address C1:75:21:86:F0:85

What it does:
  1. discovers the ring,
  2. connects,
  3. reads battery level (a genuine measurement, always available),
  4. subscribes to the standard 0x2A37 Heart Rate Measurement,
  5. waits for a packet with sensor contact DETECTED and a plausible bpm,
  6. saves raw packet + decoded value + metadata to out/first_measurement.json.

IMPORTANT: the ring reports `04 00` (flags 0x04 = "sensor contact NOT detected",
bpm 0) when it is not being worn. That is a CORRECT status, not a broken reading.
Put the ring on a finger (optical sensors flat against skin, snug but not tight)
and keep it still for this run. No vendor commands are sent.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from bleak import BleakClient

from common import (
    BATTERY_LEVEL_UUID,
    HR_MEASUREMENT_UUID,
    append_jsonl,
    device_meta,
    find_device,
    iter_services,
    now_iso,
    parse_battery_level,
    parse_hr_measurement,
    write_json,
)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--timeout", type=float, default=90.0, help="seconds to wait for a valid HR")
    ap.add_argument("--scan-seconds", type=float, default=10.0)
    args = ap.parse_args()

    dev = await find_device(args.scan_seconds, args.address)
    if not dev:
        print("ERROR: ring not found. Take it out of the case / charge it / keep it near the laptop.")
        return
    name, addr = device_meta(dev)
    print(f"connected target: {name} ({addr})", flush=True)

    battery = None
    hr_packets: list[dict] = []
    best = None
    got_valid = asyncio.Event()

    def on_hr(_char, data: bytearray) -> None:
        nonlocal best
        raw = bytes(data)
        decoded = parse_hr_measurement(raw)
        rec = {"ts_utc": now_iso(), "uuid": HR_MEASUREMENT_UUID, "hex": raw.hex(), "decoded": decoded}
        hr_packets.append(rec)
        append_jsonl("measure_hr_packets.jsonl", rec)
        print(f"  HR {raw.hex()} -> bpm={decoded.get('bpm')} contact={decoded.get('sensor_contact_detected')}", flush=True)
        if decoded.get("clinically_usable") and not got_valid.is_set():
            best = rec
            got_valid.set()

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        if BATTERY_LEVEL_UUID in chars:
            try:
                raw = bytes(await client.read_gatt_char(chars[BATTERY_LEVEL_UUID]))
                battery = {"raw_hex": raw.hex(), **parse_battery_level(raw), "ts_utc": now_iso()}
                print(f"  BATTERY {raw.hex()} -> {battery['battery_percent']}%", flush=True)
            except Exception as exc:  # noqa: BLE001
                print("  battery read failed:", exc, flush=True)
        if HR_MEASUREMENT_UUID not in chars:
            print("ERROR: standard HR Measurement characteristic not present")
            return
        await client.start_notify(chars[HR_MEASUREMENT_UUID], on_hr)
        print("\nWaiting for a genuine HR reading. Wear the ring now (sensors against skin).", flush=True)
        print("Streaming `04 00` means 'sensor contact NOT detected' - keep it on and still.\n", flush=True)
        try:
            await asyncio.wait_for(got_valid.wait(), timeout=args.timeout)
        except asyncio.TimeoutError:
            print("\nNo clinically usable HR packet arrived in time.", flush=True)
        await client.stop_notify(chars[HR_MEASUREMENT_UUID])

    payload = {
        "captured_utc": now_iso(),
        "experiment": "first_measurement",
        "status": "SUCCESS" if best else "NO_VALID_HR_YET",
        "device": {
            "name": name,
            "address": addr,
            "vendor": "Viaking / R30 PRO (box claim; not independently verified)",
            "source_label": "viaking_r30pro_experimental",
        },
        "genuine_measurements": {
            "battery_level": battery,
            "heart_rate": best["decoded"] if best else None,
            "heart_rate_raw_hex": best["hex"] if best else None,
            "heart_rate_captured_utc": best["ts_utc"] if best else None,
        },
        "hr_packets_observed": len(hr_packets),
        "last_hr_packets": hr_packets[-5:],
        "validation": {
            "clinically_validated": False,
            "note": "Experimental wearable measurement. NOT for clinical conclusions until validated.",
            "sensor_contact_requirement": "optical sensor must detect skin contact",
        },
        "safety": "read + notify only; no vendor commands, no writes, no cloud, no subscription",
    }
    p = write_json("first_measurement.json", payload)
    print("\nRESULT:", payload["status"])
    print(json.dumps(payload["genuine_measurements"], indent=2))
    print("saved ->", p)
    if best:
        print("\nFirst hardware-to-software path ESTABLISHED. Next: review FINDINGS.md Phase F.")
    else:
        print("\nNext: put the ring on, rerun `python measure.py --timeout 180`.")


if __name__ == "__main__":
    asyncio.run(main())
