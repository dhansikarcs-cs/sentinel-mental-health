"""Final different approach for ECG/temperature/HRV/stress.

No measurement-start commands. Instead:
  1. Read EVERY characteristic (even write-only ones - some reply anyway).
  2. Subscribe to all notify/indicate channels.
  3. Minimal handshake (set clock) to trigger the ring's own auto-monitor.
  4. LONG passive listen - the ring itself emitted `hr_auto_monitor 1,60`,
     implying it pushes measurements every 60 s without being asked.
  5. Decode the Nordic UART ASCII console for temperature/ECG/HRV keywords.
  6. Re-query the combined all-day record (0509), the ONE history log that works.

Safety: no DFU, no deletes, no reset, no OTA. The only writes are the same
documented handshake frames already proven safe. No guessed commands.
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
FORBIDDEN = {"0000fe59-0000-1000-8000-00805f9b34fb", "8ec90003-f315-4f60-9fb8-838830daea50"}

KEYWORDS = re.compile(r"(temp|ecg|hrv|stress|spo2|bp|systol|diastol|rr|resp|glucose|sugar|body|wear|finger|algo|monitor)", re.I)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    dev = await find_device(12.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr}) - passive auto-monitor, {args.seconds}s", flush=True)

    frames: list[dict] = []
    nus_text: list[str] = []

    def cb_factory(channel: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "channel": channel, **parse_frame(raw)}
            frames.append(rec)
            append_jsonl("probe_passive_frames.jsonl", rec)
            if channel.startswith("6e4000"):
                try:
                    s = raw.decode("ascii").rstrip("\n")
                    nus_text.append(s)
                    if KEYWORDS.search(s) or not s.startswith(("G:", "No:")):
                        print(f"  NUS> {s}", flush=True)
                except UnicodeDecodeError:
                    pass
            else:
                op = rec.get("opcode")
                if op and op not in {"0700", "0400"}:
                    print(f"  <- [{channel[:8]}] {raw.hex():<44} {op} payload={rec.get('payload_hex')}", flush=True)

        return cb

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}

        # 1. Read every characteristic - even write-only ones may answer.
        print("\n=== READ ALL CHARACTERISTICS ===", flush=True)
        reads = {}
        for u, ch in chars.items():
            if u in FORBIDDEN:
                continue
            try:
                raw = bytes(await client.read_gatt_char(ch))
                reads[u] = raw.hex()
                try:
                    ascii_val = raw.decode("ascii")
                except UnicodeDecodeError:
                    ascii_val = ""
                print(f"  {u:<44} {raw.hex():<40} {ascii_val!r}", flush=True)
            except Exception as exc:  # noqa: BLE001
                reads[u] = f"ERR {exc}"

        # 2. Subscribe all channels.
        print("\n=== SUBSCRIBE ALL ===", flush=True)
        for svc in iter_services(client):
            for ch in svc.characteristics:
                u = str(ch.uuid).lower()
                if u in FORBIDDEN:
                    continue
                if any(p in ch.properties for p in ("notify", "indicate")):
                    try:
                        await client.start_notify(ch, cb_factory(u[:8]))
                        print(f"  subscribed {u}", flush=True)
                    except Exception as exc:  # noqa: BLE001
                        print(f"  refused {u}: {exc}", flush=True)

        # 3. Minimal handshake only (clock sync triggers auto-monitor).
        print("\n=== MINIMAL HANDSHAKE (no measurement start) ===", flush=True)
        for label, raw in [
            ("get_device_name", frame(0x02, 0x03)),
            ("set_time", frame(0x01, 0x00, epoch_2000_local())),
            ("broadcast_enable", frame(0x03, 0x09)),
        ]:
            print(f"  -> {label:<24} {raw.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.8)

        # 4. Long passive listen.
        print(f"\n=== PASSIVE LISTEN {args.seconds}s (ring worn, no commands) ===", flush=True)
        await asyncio.sleep(args.seconds)

        # 5. Re-query the combined all-day record (the one that works).
        print("\n=== RE-QUERY COMBINED ALL-DAY (0509) ===", flush=True)
        q = frame(0x05, 0x09)
        before = len(frames)
        await client.write_gatt_char(chars[CMD_CHAR], q, response=False)
        await asyncio.sleep(6)
        combined = [f for f in frames[before:] if f.get("crc_ok") and f.get("raw_hex", "").startswith(("0509", "0518", "0580"))]
        for f in combined:
            print(f"  {f['raw_hex']:<50} payload={f.get('payload_hex')}", flush=True)

        for svc in iter_services(client):
            for ch in svc.characteristics:
                u = str(ch.uuid).lower()
                if u not in FORBIDDEN and any(p in ch.properties for p in ("notify", "indicate")):
                    try:
                        await client.stop_notify(ch)
                    except Exception:
                        pass

    # 6. Analyse ASCII console for signals of interest.
    interesting = [s for s in nus_text if KEYWORDS.search(s)]
    ycbt_data = [f for f in frames if f.get("crc_ok") and f.get("opcode", "").startswith("06")]

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "method": "passive auto-monitor; no measurement-start commands",
        "listen_seconds": args.seconds,
        "all_characteristic_reads": reads,
        "nus_console_lines": len(nus_text),
        "nus_lines_matching_signal_keywords": interesting[:40],
        "ycbt_live_data_frames": [f["raw_hex"] for f in ycbt_data],
        "combined_all_day_frames": [f["raw_hex"] for f in combined],
        "verdict": "DATA" if (ycbt_data or interesting or any("0518" in f["raw_hex"] for f in combined)) else "NO_NEW_SIGNALS",
        "safety": "documented handshake only; no DFU/delete/reset/OTA/measurement-start; no guessed commands",
    }
    p = write_json("probe_passive_report.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
