"""Capability discovery: ask the firmware WHICH commands exist.

Different approach: instead of trusting a documented opcode list, sweep the
`01 xx` monitor family with ENABLE=0 (a no-op "disable") and the `02 xx` info
family with empty payload. Reply codes map the implemented command surface:

  00 = accepted / implemented
  fe = stub reply (implemented but no data)
  fc = not implemented in this firmware

SAFETY: every swept command is a no-op (enable=0) or a read-only info query.
No delete opcodes (05 40..05 4E), no terminal ACK, no DFU, no reset, no OTA,
no measurement-start. All frames use the documented YCBT CRC framing on the
known command channel be940001.

Phase 2 enables ONLY the monitors that Phase 1 proved are actually accepted,
with a short interval, then listens for temperature/HRV/stress keywords on the
Nordic UART debug console and any 06 xx live frames.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re

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
NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
FORBIDDEN = {"0000fe59-0000-1000-8000-00805f9b34fb", "8ec90003-f315-4f60-9fb8-838830daea50"}

KEYWORDS = re.compile(r"(temp|ecg|hrv|stress|press|spo2|glucose|sugar|resp|body|wear|finger|monitor)", re.I)

# Exclude ranges that are NOT harmless disables.
SKIP_01 = {0x00, 0x09}  # 0100 = SetTime (writes clock), 0309 is a different type


def handshake():
    return [
        frame(0x02, 0x03),
        frame(0x01, 0x00, epoch_2000_local()),
        frame(0x03, 0x09),
    ]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true", help="run the 01xx/02xx capability sweep")
    ap.add_argument("--listen", type=float, default=120.0, help="seconds for phase-2 monitor listen")
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    dev = await find_device(12.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr})", flush=True)

    frames: list[dict] = []
    nus: list[str] = []

    def cb_factory(channel: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "channel": channel, **parse_frame(raw)}
            frames.append(rec)
            append_jsonl("probe_discover_frames.jsonl", rec)
            if channel.startswith("6e4000"):
                try:
                    s = raw.decode("ascii").rstrip()
                    nus.append(s)
                    if KEYWORDS.search(s) or not s.startswith(("G:", "No:")):
                        print(f"    NUS> {s}", flush=True)
                except UnicodeDecodeError:
                    pass

        return cb

    results: dict[str, dict] = {}
    accepted_monitors: list[tuple[int, bytes]] = []

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        subs = []
        for svc in iter_services(client):
            for ch in svc.characteristics:
                u = str(ch.uuid).lower()
                if u in FORBIDDEN:
                    continue
                if any(p in ch.properties for p in ("notify", "indicate")):
                    try:
                        await client.start_notify(ch, cb_factory(u[:8]))
                        subs.append(u)
                    except Exception:
                        pass

        for raw in handshake():
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.7)

        if args.sweep:
            print("\n=== PHASE 1a: 01 xx monitor-disable sweep (no-op, harmless) ===", flush=True)
            for xx in range(0x00, 0x51):
                if xx in SKIP_01:
                    continue
                cmd = frame(0x01, xx, bytes([0x00, 0x1E]))  # enable=0 -> disable
                before = len(frames)
                await client.write_gatt_char(chars[CMD_CHAR], cmd, response=False)
                await asyncio.sleep(0.18)
                replies = [f for f in frames[before:] if f.get("channel", "").startswith("be94") and f.get("crc_ok")]
                status = replies[0].get("payload_hex") if replies else "no_reply"
                results[f"01 {xx:02x}"] = status
                print(f"  01 {xx:02x} -> {status}", flush=True)
                if status == "00":
                    accepted_monitors.append((xx, bytes([0x01, 0x01])))  # enable, 1-min interval

            print("\n=== PHASE 1b: 02 xx info query sweep (read-only) ===", flush=True)
            for xx in range(0x00, 0x41):
                cmd = frame(0x02, xx)
                before = len(frames)
                await client.write_gatt_char(chars[CMD_CHAR], cmd, response=False)
                await asyncio.sleep(0.18)
                replies = [f for f in frames[before:] if f.get("channel", "").startswith("be94") and f.get("crc_ok")]
                status = replies[0].get("payload_hex") if replies else "no_reply"
                results[f"02 {xx:02x}"] = status

        # Phase 2: enable ONLY accepted monitors, then long listen.
        print(f"\n=== PHASE 2: enabling {len(accepted_monitors)} accepted monitors, listening {args.listen}s ===", flush=True)
        enabled = []
        for xx, payload in accepted_monitors:
            on = frame(0x01, xx, payload)
            print(f"  -> enable 01 {xx:02x} {on.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], on, response=False)
            enabled.append((xx, payload))
            await asyncio.sleep(0.5)
        await asyncio.sleep(args.listen)
        for xx, payload in enabled:
            off = frame(0x01, xx, bytes([0x00]) + payload[1:])
            await client.write_gatt_char(chars[CMD_CHAR], off, response=False)
            await asyncio.sleep(0.3)

        for u in subs:
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    live = [f["raw_hex"] for f in frames if f.get("crc_ok") and f.get("opcode", "").startswith("06")]
    accepted = {k: v for k, v in results.items() if v not in ("fc", "no_reply")}
    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "method": "no-op capability sweep + enable only accepted monitors",
        "sweep_size": len(results),
        "accepted_or_stub_commands": accepted,
        "rejected_0xfc_count": sum(1 for v in results.values() if v == "fc"),
        "accepted_monitors_enabled": [f"01 {xx:02x}" for xx, _ in enabled],
        "nus_console_lines": len(nus),
        "nus_lines_with_signal_keywords": [s for s in nus if KEYWORDS.search(s)][:50],
        "live_06xx_frames": live,
        "safety": "no-op/enable-only commands; no delete/DFU/reset/OTA/measurement-start",
    }
    p = write_json("probe_discover_report.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
