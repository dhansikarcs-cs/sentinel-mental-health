"""Last different route: enable documented YCBT background monitors.

PulseLoop YCBT spec documents five `01 xx {enable, interval}` monitor commands,
including:
  01 20 - skin temperature monitor
  01 1c - all-day blood pressure monitor
  01 45 - HRV monitor (payload {enable, interval, 0, 0, 0})

Hypothesis: spot measurements don't populate the combined all-day record with
temperature/HRV, but ENABLING the background monitors may. After enabling we
run one long SpO2 measurement (known to converge), then re-query all histories.

Every enable is paired with a disable at the end, so the ring is left as found.
Only documented opcodes. No DFU, no deletes, no reset, no OTA, no guessing.
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

MONITORS = {
    "temperature": (0x01, 0x20, bytes([0x01, 0x1E])),
    "all_day_bp": (0x01, 0x1C, bytes([0x01, 0x1E])),
    "hrv": (0x01, 0x45, bytes([0x01, 0x1E, 0x00, 0x00, 0x00])),
}

HISTORY = {
    "combined_all_day": 0x09,
    "heart_rate": 0x06,
    "blood_pressure": 0x08,
    "temperature": 0x1E,
    "spo2": 0x1A,
}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=75.0)
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    dev = await find_device(12.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr}) - KEEP RING WORN", flush=True)

    frames: list[dict] = []
    phase = {"n": "init"}

    def cb_factory(channel: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "phase": phase["n"], "channel": channel, **parse_frame(raw)}
            frames.append(rec)
            append_jsonl("probe_monitors_frames.jsonl", rec)
            if channel.startswith("be94") and rec.get("crc_ok"):
                op = rec.get("opcode")
                print(f"    <- {raw.hex():<48} {op} payload={rec.get('payload_hex')}", flush=True)
            elif channel.startswith("6e4000"):
                try:
                    s = raw.decode("ascii").rstrip()
                    if not s.startswith(("G:", "No:")):
                        print(f"    NUS> {s}", flush=True)
                except UnicodeDecodeError:
                    pass

        return cb

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        await client.start_notify(chars[CMD_CHAR], cb_factory("be940001"))
        await client.start_notify(chars[STREAM_CHAR], cb_factory("be940003"))

        phase["n"] = "handshake"
        print("\n=== HANDSHAKE ===", flush=True)
        for label, raw in [
            ("get_device_name", frame(0x02, 0x03)),
            ("set_time", frame(0x01, 0x00, epoch_2000_local())),
            ("get_support_function", frame(0x02, 0x01)),
            ("broadcast_enable", frame(0x03, 0x09)),
        ]:
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.8)

        phase["n"] = "enable_monitors"
        print("\n=== ENABLE DOCUMENTED BACKGROUND MONITORS ===", flush=True)
        sent = []
        for label, (t, c, payload) in MONITORS.items():
            on = frame(t, c, payload)
            off = frame(t, c, bytes([0x00]) + payload[1:])
            sent.append((label, on, off))
            print(f"  -> enable {label:<18} {on.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], on, response=False)
            await asyncio.sleep(1.0)

        phase["n"] = "spo2_measurement"
        print(f"\n=== FORCE ONE SpO2 MEASUREMENT ({args.seconds}s) ===", flush=True)
        await client.write_gatt_char(chars[CMD_CHAR], frame(0x03, 0x2F, bytes([0x01, 0x02])), response=False)
        await asyncio.sleep(args.seconds)
        await client.write_gatt_char(chars[CMD_CHAR], frame(0x03, 0x2F, bytes([0x00, 0x02])), response=False)
        await asyncio.sleep(0.5)

        phase["n"] = "history_requery"
        print("\n=== RE-QUERY HISTORIES ===", flush=True)
        for label, key in HISTORY.items():
            before = len(frames)
            q = frame(0x05, key)
            print(f"  -> query {label:<20} {q.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], q, response=False)
            await asyncio.sleep(5)
            got = [f for f in frames[before:] if f.get("crc_ok")]
            terminal = any(f.get("opcode") == "0580" for f in got)
            if terminal:
                await client.write_gatt_char(chars[CMD_CHAR], frame(0x05, 0x80, b"\x00"), response=False)
                await asyncio.sleep(0.3)

        phase["n"] = "disable_monitors"
        print("\n=== DISABLE MONITORS (leave ring as found) ===", flush=True)
        for label, _on, off in sent:
            print(f"  -> disable {label:<17} {off.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], off, response=False)
            await asyncio.sleep(0.8)

        for u in (CMD_CHAR, STREAM_CHAR):
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    data_frames = [f for f in frames if f.get("crc_ok") and f.get("opcode", "").startswith("06")]
    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "method": "documented 01 xx monitor enable + forced SpO2 + history re-query",
        "monitors_enabled": list(MONITORS),
        "live_06xx_frames": [f["raw_hex"] for f in data_frames],
        "total_frames": len(frames),
        "history_replies": [f["raw_hex"] for f in frames if f.get("phase") == "history_requery" and f.get("crc_ok")],
        "safety": "documented opcodes only; monitors disabled at end; no DFU/delete/reset/OTA",
    }
    p = write_json("probe_monitors_report.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
