"""Phase A - BLE advertising discovery for the Viaking R30 PRO.

Usage:
    python scan.py                     # single 12s scan
    python scan.py --seconds 20
    python scan.py --repeat 3 --seconds 15 --interval 5

Writes out/scan_<utc>.json and refreshes out/scan_latest.json.
Passive observation only: no connections, no writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from common import now_iso, stream_scan, write_json


async def one_scan(seconds: float) -> dict:
    seen = await stream_scan(seconds)
    devices = sorted(seen.values(), key=lambda d: -(d.get("rssi") or -999))
    targets = [d for d in devices if d["target_match"]]
    payload = {
        "captured_utc": now_iso(),
        "scan_seconds": seconds,
        "device_count": len(devices),
        "target_count": len(targets),
        "targets": targets,
        "all_devices": devices,
        "notes": [
            "Active streaming scan via BleakScanner(detection_callback=...).",
            "One-shot BleakScanner.discover() missed this device on Windows; streaming is reliable.",
            "R30 PRO advertises as 'R30 PRO <last4-of-MAC>', not plain 'R30 PRO'.",
            "Observed advertisement signature: 0x180D (Heart Rate) + 0xFEE7 (vendor).",
            "Manufacturer data company id 0x7811 ends with the device MAC.",
        ],
    }
    return payload


def print_summary(payload: dict) -> None:
    print(f"\n[{payload['captured_utc']}] devices={payload['device_count']} targets={payload['target_count']}")
    for d in payload["all_devices"][:30]:
        mark = "  <== R30 PRO CANDIDATE" if d["target_match"] else ""
        print(f"  {d['address']}  rssi={d['rssi']:>4}  {d['name']!r:<28} uuids={','.join(d['service_uuids'])}{mark}")
    for t in payload["targets"]:
        print(f"  TARGET mfg={t['manufacturer_data']} svc_data={t['service_data']}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--repeat", type=int, default=1, help="number of scans (to observe advertising changes)")
    ap.add_argument("--interval", type=float, default=5.0, help="pause between scans, seconds")
    args = ap.parse_args()

    for i in range(args.repeat):
        payload = await one_scan(args.seconds)
        print_summary(payload)
        stamp = payload["captured_utc"].replace(":", "-").replace("+", "Z")
        p = write_json(f"scan_{stamp}.json", payload)
        write_json("scan_latest.json", payload)
        print(f"  saved -> {p}")
        if i + 1 < args.repeat:
            await asyncio.sleep(args.interval)
    print("\nNext: python gatt.py --address <address-from-scan>")


if __name__ == "__main__":
    asyncio.run(main())
