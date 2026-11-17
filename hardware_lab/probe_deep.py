"""Different approach: single measurement, long window, ALL channels listed.

Hypothesis: batched sessions get ACKed but produce no data because the ring
allows one spot measurement per connection and needs a cooldown + skin contact.
This probe does: cooldown -> ONE clean connect -> minimal handshake -> ONE
start command -> long listen on EVERY notify/indicate characteristic.

Also experiments with the alternate write channel be940002 (same documented
opcode, different GATT characteristic) to see if replies change.

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
ALT_WRITE_CHAR = "be940002-7333-be46-b7ae-689e71722bd5"
STREAM_CHAR = "be940003-7333-be46-b7ae-689e71722bd5"

# Never write to these (DFU would reboot into bootloader).
FORBIDDEN = {
    "0000fe59-0000-1000-8000-00805f9b34fb",
    "8ec90003-f315-4f60-9fb8-838830daea50",
}

MODES = {"hr": 0x00, "bp": 0x01, "spo2": 0x02, "hrv": 0x0A}

LIVE = {"0600", "0601", "0602", "0603", "0615", "040e"}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="spo2", choices=list(MODES))
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--cooldown", type=float, default=20.0)
    ap.add_argument("--address", default=None)
    ap.add_argument("--alt-channel", action="store_true", help="also send start via be940002")
    args = ap.parse_args()

    mode = MODES[args.mode]
    print(f"cooldown {args.cooldown}s (no BLE traffic) - KEEP THE RING WORN", flush=True)
    await asyncio.sleep(args.cooldown)

    dev = await find_device(12.0, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr}) | mode={args.mode} (0x{mode:02x})", flush=True)

    frames: list[dict] = []
    phase = {"n": "init"}
    log_name = f"probe_deep_{args.mode}_frames.jsonl"

    def make_cb(channel: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "phase": phase["n"], "channel": channel, **parse_frame(raw)}
            frames.append(rec)
            append_jsonl(log_name, rec)
            op = rec.get("opcode")
            flag = "  <<< LIVE/COMPLETION" if op in LIVE else ""
            print(
                f"  <- [{channel}] {raw.hex():<44} {op} payload={rec.get('payload_hex')}{flag}",
                flush=True,
            )

        return cb

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}

        # Subscribe to EVERY notify/indicate char except the DFU control point.
        subs = []
        for svc in iter_services(client):
            for ch in svc.characteristics:
                u = str(ch.uuid).lower()
                if u in FORBIDDEN:
                    continue
                if any(p in ch.properties for p in ("notify", "indicate")):
                    try:
                        await client.start_notify(ch, make_cb(u[:8]))
                        subs.append(u)
                        print(f"  subscribed {u}", flush=True)
                    except Exception as exc:  # noqa: BLE001
                        print(f"  subscribe refused {u}: {exc}", flush=True)

        phase["n"] = "handshake"
        print("\n--- minimal handshake ---", flush=True)
        for label, raw in [
            ("get_device_name", frame(0x02, 0x03)),
            ("set_time", frame(0x01, 0x00, epoch_2000_local())),
            ("get_support_function", frame(0x02, 0x01)),
            ("get_measurement_function", frame(0x02, 0x28)),
            ("broadcast_enable", frame(0x03, 0x09)),
        ]:
            print(f"  -> {label:<28} {raw.hex()}", flush=True)
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.8)

        phase["n"] = f"measure_{args.mode}"
        start = frame(0x03, 0x2F, bytes([0x01, mode]))
        print(f"\n--- start {args.mode} (single measurement, {args.seconds}s window) ---", flush=True)
        print(f"  -> start {start.hex()}", flush=True)
        before = len(frames)
        await client.write_gatt_char(chars[CMD_CHAR], start, response=False)

        # Optional alternate-channel experiment halfway through (same opcode).
        if args.alt_channel and ALT_WRITE_CHAR in chars:
            await asyncio.sleep(args.seconds / 2)
            print(f"  -> start via ALT channel be940002 {start.hex()}", flush=True)
            await client.write_gatt_char(chars[ALT_WRITE_CHAR], start, response=False)
            remaining = args.seconds / 2
        else:
            remaining = args.seconds
        await asyncio.sleep(remaining)

        stop = frame(0x03, 0x2F, bytes([0x00, mode]))
        await client.write_gatt_char(chars[CMD_CHAR], stop, response=False)
        await asyncio.sleep(0.5)
        for u in subs:
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    during = frames[before:]
    live = [f for f in during if f.get("opcode") in LIVE and f.get("crc_ok")]
    by_op = {}
    for f in during:
        by_op[f.get("opcode")] = by_op.get(f.get("opcode"), 0) + 1

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "mode": args.mode,
        "mode_byte": f"0x{mode:02x}",
        "window_seconds": args.seconds,
        "cooldown_seconds": args.cooldown,
        "channels_subscribed": subs,
        "alt_channel_tried": args.alt_channel,
        "frames_during_measurement": len(during),
        "by_opcode": by_op,
        "live_or_completion_frames": [f["raw_hex"] for f in live],
        "verdict": "DATA" if live else "NO_DATA_ACK_ONLY",
        "safety": "documented opcodes only; no DFU/delete/reset/OTA; no guessed commands",
    }
    p = write_json(f"probe_deep_{args.mode}.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
