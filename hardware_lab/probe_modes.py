"""Try EVERY documented spot measurement, one clean connection per mode.

Why: the exhaustive single-session probe polluted the ring's YCBT state
machine (extra 0200 command, terminal ACKs sent without a terminal frame),
so no live 06 xx stream appeared. A fresh connect + minimal known-good
handshake per mode is the reliable way to give each signal its best shot.

Only documented opcodes. No DFU, no deletes, no reset, no guessed commands.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from bleak import BleakClient

from common import (
    append_jsonl,
    device_meta,
    find_device,
    iter_services,
    now_iso,
    write_json,
)
from ycbt import epoch_2000_local, frame, parse_frame

CMD_CHAR = "be940001-7333-be46-b7ae-689e71722bd5"
STREAM_CHAR = "be940003-7333-be46-b7ae-689e71722bd5"

SPOT_MODES = {
    0x00: "heart_rate",
    0x01: "blood_pressure",
    0x02: "spo2",
    0x0A: "hrv",
}

LIVE_OPCODES = {
    "0600": "activity_live",
    "0601": "heart_rate_live",
    "0602": "spo2_live",
    "0603": "blood_pressure_live",
    "0615": "battery_live",
}


def handshake():
    return [
        ("get_device_name", frame(0x02, 0x03)),
        ("set_time", frame(0x01, 0x00, epoch_2000_local())),
        ("get_support_function", frame(0x02, 0x01)),
        ("get_measurement_function", frame(0x02, 0x28)),
        ("broadcast_enable", frame(0x03, 0x09)),
    ]


async def one_mode(dev, mode: int, label: str, seconds: float) -> dict:
    frames: list[dict] = []

    def cb(_char, data: bytearray) -> None:
        raw = bytes(data)
        rec = {"ts_utc": now_iso(), "mode": label, **parse_frame(raw)}
        frames.append(rec)
        append_jsonl("probe_modes_frames.jsonl", rec)
        op = rec.get("opcode")
        extra = LIVE_OPCODES.get(op, "")
        print(f"    <- {raw.hex():<40} {op} {extra} payload={rec.get('payload_hex')}", flush=True)

    print(f"\n=== {label} (mode 0x{mode:02x}) - fresh connection ===", flush=True)
    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        await client.start_notify(chars[CMD_CHAR], cb)
        await client.start_notify(chars[STREAM_CHAR], cb)
        for _label, raw in handshake():
            print(f"    -> {_label:<28} {raw.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.6)

        start = frame(0x03, 0x2F, bytes([0x01, mode]))
        print(f"    -> start_{label:<23} {start.hex()}", flush=True)
        before = len(frames)
        await client.write_gatt_char(chars[CMD_CHAR], start, response=False)
        await asyncio.sleep(seconds)
        stop = frame(0x03, 0x2F, bytes([0x00, mode]))
        await client.write_gatt_char(chars[CMD_CHAR], stop, response=False)
        await asyncio.sleep(0.5)
        for u in (CMD_CHAR, STREAM_CHAR):
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    during = frames[before:]
    live = [f for f in during if f.get("opcode") in LIVE_OPCODES and f.get("crc_ok")]
    return {
        "mode": f"0x{mode:02x}",
        "label": label,
        "frames_during_measurement": len(during),
        "live_data_frames": len(live),
        "live_payloads": [f["payload_hex"] for f in live],
        "live_opcodes": sorted({f["opcode"] for f in live}),
        "all_opcodes": sorted({f.get("opcode") for f in during if f.get("opcode")}),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--seconds", type=float, default=20.0)
    args = ap.parse_args()

    dev = await find_device(10.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr}) - KEEP THE RING WORN", flush=True)

    results = []
    for mode, label in SPOT_MODES.items():
        # Re-scan once at the start; reuse the cached address for later connects.
        results.append(await one_mode(dev, mode, label, args.seconds))

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "protocol": "Yucheng YCBT; fresh connection + minimal handshake per mode",
        "results": results,
        "safety": "documented opcodes only; no DFU/delete/reset/OTA; no guessed commands",
    }
    p = write_json("probe_modes_report.json", report)
    print("\n=== FINAL ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
