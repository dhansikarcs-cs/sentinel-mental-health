"""Phase D - passive BLE notification / indication capture.

Usage:
    python notify.py --seconds 60

Subscribes to every characteristic that declares notify/indicate and records raw
packets as hex with UTC timestamps to out/notifications.jsonl.

SAFETY: subscriptions (CCCD) only. No writes to any characteristic, no vendor
commands, no pairing changes, no DFU. Some characteristics (e.g. 0x2A05 Service
Changed) legitimately refuse subscription on Windows - those are logged, not
retried.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter

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
    uuid_label,
    write_json,
)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--seconds", type=float, default=60.0, help="capture duration")
    ap.add_argument("--scan-seconds", type=float, default=10.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    dev = await find_device(args.scan_seconds, args.address)
    if not dev:
        print("ERROR: R30 PRO not found")
        return
    name, addr = device_meta(dev)
    print(f"connecting to {name} ({addr}) ...", flush=True)

    records: list[dict] = []
    subscribed: list[str] = []
    refused: list[dict] = []

    def make_cb(uuid: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {
                "ts_utc": now_iso(),
                "uuid": uuid,
                "name": uuid_label(uuid),
                "length": len(raw),
                "hex": raw.hex(),
            }
            if uuid.lower() == HR_MEASUREMENT_UUID:
                rec["decoded_hr"] = parse_hr_measurement(raw)
            elif uuid.lower() == BATTERY_LEVEL_UUID:
                rec["decoded_battery"] = parse_battery_level(raw)
            records.append(rec)
            append_jsonl("notifications.jsonl", rec)
            extra = rec.get("decoded_hr") or rec.get("decoded_battery") or ""
            print(f"  {rec['ts_utc']}  {uuid}  len={len(raw):>3}  {raw.hex()}  {extra}", flush=True)

        return cb

    async with BleakClient(dev, timeout=args.timeout) as client:
        targets = [
            ch
            for svc in iter_services(client)
            for ch in svc.characteristics
            if any(p in ch.properties for p in ("notify", "indicate"))
        ]
        print(f"notify/indicate characteristics: {len(targets)}", flush=True)
        for ch in targets:
            u = str(ch.uuid)
            try:
                await client.start_notify(ch, make_cb(u))
                subscribed.append(u)
                print(f"  subscribed {u} {uuid_label(u)}", flush=True)
            except Exception as exc:  # noqa: BLE001
                refused.append({"uuid": u, "error": str(exc)})
                print(f"  REFUSED   {u} -> {exc}", flush=True)

        if not subscribed:
            print("ERROR: no subscriptions established")
            return
        print(f"capturing for {args.seconds}s - passive, no writes ...", flush=True)
        await asyncio.sleep(args.seconds)
        for ch in targets:
            try:
                await client.stop_notify(ch)
            except Exception:
                pass

    by_uuid = Counter(r["uuid"] for r in records)
    summary = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "duration_seconds": args.seconds,
        "packet_count": len(records),
        "by_uuid": dict(by_uuid),
        "subscribed": subscribed,
        "refused": refused,
        "hr_packets": sum(1 for r in records if "decoded_hr" in r),
        "usable_hr_packets": sum(1 for r in records if r.get("decoded_hr", {}).get("clinically_usable")),
        "safety": "subscriptions only; original packets preserved verbatim in notifications.jsonl",
    }
    p = write_json("notify_summary.json", summary)
    print("\nSUMMARY", json.dumps(summary, indent=2))
    print("saved ->", p)
    print("raw packets -> out/notifications.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
