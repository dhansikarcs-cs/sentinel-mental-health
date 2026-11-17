"""Every documented history log, fresh connection each, no cascading 0xFC.

PulseLoop docs: a ring that lacks a log may reply 0xFC, after which it stops
answering the rest of THAT session. So each query needs its own connection.

Terminal ACK (05 80 {00}) is sent ONLY when a real terminal frame was seen.
No delete opcodes (05 40..05 4E), no DFU, no reset, no guessed commands.
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

HISTORY_KEYS = {
    0x02: "activity_steps_distance_calories",
    0x04: "sleep_stages",
    0x06: "heart_rate_history",
    0x08: "blood_pressure_history",
    0x09: "combined_all_day_record",
    0x1A: "spo2_history",
    0x1E: "temperature_history",
    0x2F: "comprehensive_record",
    0x33: "body_data_stress_fatigue",
}


def handshake():
    return [
        frame(0x02, 0x03),
        frame(0x01, 0x00, epoch_2000_local()),
        frame(0x02, 0x01),
        frame(0x02, 0x28),
        frame(0x03, 0x09),
    ]


async def one_query(dev, key: int, label: str, seconds: float) -> dict:
    frames: list[dict] = []

    def cb(_char, data: bytearray) -> None:
        raw = bytes(data)
        rec = {"ts_utc": now_iso(), "query": label, **parse_frame(raw)}
        frames.append(rec)
        append_jsonl("probe_history_frames.jsonl", rec)
        print(f"    <- {raw.hex():<40} {rec.get('opcode')} payload={rec.get('payload_hex')}", flush=True)

    print(f"\n=== {label} (05 {key:02x}) - fresh connection ===", flush=True)
    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        await client.start_notify(chars[CMD_CHAR], cb)
        await client.start_notify(chars[STREAM_CHAR], cb)
        for raw in handshake():
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.6)

        q = frame(0x05, key)
        print(f"    -> query {q.hex()}", flush=True)
        before = len(frames)
        await client.write_gatt_char(chars[CMD_CHAR], q, response=False)
        await asyncio.sleep(seconds)
        during = frames[before:]
        terminal = any(f.get("opcode") == "0580" and f.get("crc_ok") for f in during)
        if terminal:
            ack = frame(0x05, 0x80, b"\x00")
            print(f"    -> terminal_ack (no delete) {ack.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], ack, response=False)
            await asyncio.sleep(0.4)
        for u in (CMD_CHAR, STREAM_CHAR):
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    payload_frames = [f for f in during if f.get("crc_ok") and f.get("payload_hex")]
    verdict = "empty_or_ack_only"
    if any(f.get("payload_hex") == "fc" for f in during):
        verdict = "REJECTED_0xFC"
    if any(f.get("opcode") in {"0506", "0515", "0512", "0513", "0514"} for f in during):
        verdict = "HAS_RECORDS"
    return {
        "key": f"05 {key:02x}",
        "label": label,
        "verdict": verdict,
        "frames": len(during),
        "terminal_seen": terminal,
        "opcodes": sorted({f.get("opcode") for f in during if f.get("opcode")}),
        "payloads": [f["payload_hex"] for f in payload_frames][:10],
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--seconds", type=float, default=6.0)
    args = ap.parse_args()

    dev = await find_device(10.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr})", flush=True)

    results = []
    for key, label in HISTORY_KEYS.items():
        results.append(await one_query(dev, key, label, args.seconds))
        await asyncio.sleep(2.0)  # cooldown between connections

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "protocol": "Yucheng YCBT; fresh connection per history query",
        "results": results,
        "safety": "documented opcodes only; no delete/DFU/reset/OTA; terminal ACK only when terminal seen",
    }
    p = write_json("probe_history_report.json", report)
    print("\n=== FINAL ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
