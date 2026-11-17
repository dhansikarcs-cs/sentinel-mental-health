"""Phase B - GATT discovery (connect + enumerate, read-only).

Usage:
    python gatt.py                                  # auto-discover the R30 PRO
    python gatt.py --address C1:75:21:86:F0:85

Exports out/gatt_map.json and out/gatt_report.txt.

SAFETY: connects, enumerates, and reads characteristics marked 'read' only.
No writes, no CCCD manipulation, no auth/handshake, no DFU, no vendor commands.
"""

from __future__ import annotations

import argparse
import asyncio

from bleak import BleakClient

from common import (
    BATTERY_LEVEL_UUID,
    HR_MEASUREMENT_UUID,
    OUT_DIR,
    char_dict,
    device_meta,
    find_device,
    is_vendor_uuid,
    iter_services,
    now_iso,
    uuid_label,
    write_json,
)

SAFE_READ_UUIDS = {
    "00002a00-0000-1000-8000-00805f9b34fb",  # Device Name
    "00002a01-0000-1000-8000-00805f9b34fb",  # Appearance
    "00002a04-0000-1000-8000-00805f9b34fb",  # Peripheral Preferred Connection Parameters
    "00002a19-0000-1000-8000-00805f9b34fb",  # Battery Level
    "00002a24-0000-1000-8000-00805f9b34fb",  # Model Number
    "00002a25-0000-1000-8000-00805f9b34fb",  # Serial Number
    "00002a26-0000-1000-8000-00805f9b34fb",  # Hardware Revision
    "00002a27-0000-1000-8000-00805f9b34fb",  # Firmware Revision
    "00002a28-0000-1000-8000-00805f9b34fb",  # Software Revision
    "00002a29-0000-1000-8000-00805f9b34fb",  # Manufacturer Name
    "00002a38-0000-1000-8000-00805f9b34fb",  # HR Control Point (read-only here)
    "00002aa6-0000-1000-8000-00805f9b34fb",  # Central Address Resolution
    "0000fec9-0000-1000-8000-00805f9b34fb",  # vendor: MAC
    "0000fea1-0000-1000-8000-00805f9b34fb",  # vendor: status block
    "0000fea2-0000-1000-8000-00805f9b34fb",  # vendor: unknown 4-byte value
}


def report_text(payload: dict) -> str:
    lines = [
        "Sentinel R30 PRO - GATT DISCOVERY REPORT (read-only)",
        f"captured_utc : {payload['captured_utc']}",
        f"device       : {payload['device']['name']}  {payload['device']['address']}",
        f"services     : {len(payload['services'])}",
        "",
        "STANDARD PROFILE CHECKS",
        f"  Heart Rate Service 0x180D : {payload['standard_profiles']['heart_rate_service']}",
        f"  HR Measurement 0x2A37     : {payload['standard_profiles']['hr_measurement']}",
        f"  Battery Service 0x180F    : {payload['standard_profiles']['battery_service']}",
        f"  Battery Level 0x2A19      : {payload['standard_profiles']['battery_level']}",
        f"  Device Information 0x180A : {payload['standard_profiles']['device_information']}",
        "",
    ]
    for svc in payload["services"]:
        lines.append(f"SERVICE {svc['uuid']} (handle {svc['handle']}) {svc['name']}")
        for ch in svc["characteristics"]:
            tag = " [VENDOR]" if ch["vendor_specific"] else ""
            lines.append(f"  CHAR {ch['uuid']} h={ch['handle']} props={','.join(ch['properties'])} {ch['name']}{tag}")
            if ch.get("read_hex") is not None:
                lines.append(f"       READ len={ch['read_len']} hex={ch['read_hex']} ascii={ch.get('read_ascii')!r}")
            if ch.get("read_error"):
                lines.append(f"       READ FAILED: {ch['read_error']}")
            for d in ch["descriptors"]:
                lines.append(f"       DESC {d['uuid']} h={d['handle']} {d['name']}")
        lines.append("")
    lines += [
        "INTERPRETATION NOTES",
        "  * These are BLE-visible interfaces, NOT proof that a sensor's raw data is exposed.",
        "  * Vendor 128-bit characteristics are unmapped; their packet format is unknown.",
        "  * See FINDINGS.md for the data accessibility matrix and unresolved questions.",
    ]
    return "\n".join(lines) + "\n"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    dev = await find_device(args.seconds, args.address)
    if not dev:
        print("ERROR: R30 PRO not found. Is it out of the case, charged, and near the laptop?")
        return
    name, addr = device_meta(dev)
    print(f"connecting to {name} ({addr}) ...", flush=True)

    services_out = []
    async with BleakClient(dev, timeout=args.timeout) as client:
        print("connected:", client.is_connected)
        for svc in iter_services(client):
            s = {
                "uuid": str(svc.uuid),
                "name": uuid_label(str(svc.uuid)),
                "handle": svc.handle,
                "vendor_specific": is_vendor_uuid(str(svc.uuid)),
                "characteristics": [],
            }
            for ch in svc.characteristics:
                c = char_dict(ch)
                if "read" in ch.properties and str(ch.uuid).lower() in SAFE_READ_UUIDS:
                    try:
                        val = bytes(await client.read_gatt_char(ch))
                        c["read_hex"] = val.hex()
                        c["read_len"] = len(val)
                        try:
                            c["read_ascii"] = val.decode("utf-8").strip("\x00")
                        except UnicodeDecodeError:
                            c["read_ascii"] = None
                    except Exception as exc:  # noqa: BLE001 - log every failure, keep going
                        c["read_error"] = str(exc)
                s["characteristics"].append(c)
            services_out.append(s)

    all_chars = [c for s in services_out for c in s["characteristics"]]
    by_uuid = {c["uuid"].lower(): c for c in all_chars}
    payload = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "services": services_out,
        "standard_profiles": {
            "heart_rate_service": any(s["uuid"].lower().startswith("0000180d") for s in services_out),
            "hr_measurement": HR_MEASUREMENT_UUID in by_uuid,
            "battery_service": any(s["uuid"].lower().startswith("0000180f") for s in services_out),
            "battery_level": BATTERY_LEVEL_UUID in by_uuid,
            "device_information": any(s["uuid"].lower().startswith("0000180a") for s in services_out),
        },
        "vendor_characteristic_count": sum(1 for c in all_chars if c["vendor_specific"]),
        "safety": "read-only; no CCCD writes, no vendor commands, no DFU",
    }

    p = write_json("gatt_map.json", payload)
    rp = OUT_DIR / "gatt_report.txt"
    rp.write_text(report_text(payload), encoding="utf-8")
    print(f"\n{len(services_out)} services, {len(all_chars)} characteristics")
    print("saved ->", p)
    print("saved ->", rp)
    print("\nNext: python notify.py (passive packet capture), then python measure.py")


if __name__ == "__main__":
    asyncio.run(main())
