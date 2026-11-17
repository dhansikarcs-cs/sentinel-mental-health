"""Phase E/F - Yucheng YCBT protocol client for the R30 PRO health channel.

The `be940000-...` GATT service is the Yucheng YCBT protocol (HealthWear /
SmartHealth app family), documented by the open-source PulseLoop project:
    https://saksham2001.github.io/PulseLoopiOS/hardware/tk5/#protocol

Frame: [type:1][cmd:1][len:2 LE][payload:N][crc16:2 LE]
       len = TOTAL frame length; CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF),
       little-endian, computed over everything before the CRC.

VERIFIED ON THIS UNIT: the ring's unsolicited indication ffff0600a6aa has
len=6 and CRC(ffff0600)=0xAAA6 -> bytes a6 aa. Exact match.

Usage:
    python ycbt.py                       # DRY RUN: print frames, write NOTHING
    python ycbt.py --enable-writes       # send documented handshake + start HR
    python ycbt.py --enable-writes --seconds 60

SAFETY (deliberately enforced):
  * Writes are OFF unless --enable-writes is passed.
  * NEVER touches the Nordic DFU service (0xFE59 / 8ec90003) - that reboots
    into the bootloader.
  * NEVER sends history-delete opcodes (05 40..05 4E) or the terminal ACK
    (05 80) - those ERASE the ring's log.
  * No reset, no OTA, no firmware update, no guessed commands.
  * Only the documented handshake + a reversible measurement start/stop.
  * Every frame (sent and received) is logged verbatim to out/ycbt_frames.jsonl.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
import time
from datetime import datetime

from bleak import BleakClient

from common import (
    OUT_DIR,
    append_jsonl,
    device_meta,
    find_device,
    iter_services,
    now_iso,
    write_json,
)

YCBT_SERVICE = "be940000-7333-be46-b7ae-689e71722bd5"
CMD_CHAR = "be940001-7333-be46-b7ae-689e71722bd5"  # write + indicate (replies)
STREAM_CHAR = "be940003-7333-be46-b7ae-689e71722bd5"  # indicate (live vitals)

# Documented opcode pairs (type, cmd). Source: PulseLoop YCBT driver.
OPCODES = {
    "get_device_name": (0x02, 0x03),
    "set_time": (0x01, 0x00),
    "get_support_function": (0x02, 0x01),
    "get_measurement_function": (0x02, 0x28),
    "keep_alive": (0x02, 0x26),
    "broadcast_enable": (0x03, 0x09),
    "measurement_control": (0x03, 0x2F),  # payload: {on/off, type}
}

# Live data frame types arriving on 06 xx
STREAM_TYPES = {
    0x0600: "activity / steps counter",
    0x0601: "heart rate measurement",
    0x0602: "SpO2 measurement",
    0x0603: "blood pressure measurement",
    0x0606: "completion / status",
    0x0615: "battery push",
}


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def frame(type_byte: int, cmd_byte: int, payload: bytes = b"") -> bytes:
    """Build a YCBT frame. len = total frame length (header + payload + CRC)."""
    total = 4 + len(payload) + 2
    head = bytes([type_byte, cmd_byte]) + struct.pack("<H", total)
    crc = crc16_ccitt_false(head + payload)
    return head + payload + struct.pack("<H", crc)


def parse_frame(raw: bytes) -> dict:
    out = {"raw_hex": raw.hex(), "length": len(raw)}
    if len(raw) < 6:
        out["error"] = "short frame"
        return out
    t, c = raw[0], raw[1]
    declared = struct.unpack("<H", raw[2:4])[0]
    payload = raw[4:-2]
    crc_got = struct.unpack("<H", raw[-2:])[0]
    crc_calc = crc16_ccitt_false(raw[:-2])
    out.update(
        {
            "type": f"0x{t:02x}",
            "cmd": f"0x{c:02x}",
            "opcode": f"{t:02x}{c:02x}",
            "declared_length": declared,
            "payload_hex": payload.hex(),
            "crc_ok": crc_got == crc_calc,
            "crc_received": f"0x{crc_got:04x}",
            "crc_computed": f"0x{crc_calc:04x}",
        }
    )
    key = (t << 8) | c
    if key in STREAM_TYPES:
        out["meaning"] = STREAM_TYPES[key]
    return out


def epoch_2000_local() -> bytes:
    """Seconds since 2000-01-01 in the ring's LOCAL wall-clock, 4-byte LE."""
    delta = datetime.now() - datetime(2000, 1, 1)
    return struct.pack("<I", int(delta.total_seconds()))


def handshake_frames() -> list[tuple[str, bytes]]:
    """The documented init sequence. No deletes, no DFU, no reset."""
    f = frame
    return [
        ("get_device_name", f(*OPCODES["get_device_name"])),
        ("set_time", f(*OPCODES["set_time"], epoch_2000_local())),
        ("get_support_function", f(*OPCODES["get_support_function"])),
        ("get_measurement_function", f(*OPCODES["get_measurement_function"])),
        ("broadcast_enable", f(*OPCODES["broadcast_enable"])),
    ]


def start_hr_frames() -> list[tuple[str, bytes]]:
    # 03 2F {01=on, 00=HR mode}; mode 02=SpO2, 01=BP.
    return [
        ("start_hr_measurement", frame(*OPCODES["measurement_control"], bytes([0x01, 0x00]))),
    ]


def stop_hr_frames() -> list[tuple[str, bytes]]:
    return [
        ("stop_hr_measurement", frame(*OPCODES["measurement_control"], bytes([0x00, 0x00]))),
    ]


async def run(args) -> None:
    dev = await find_device(args.scan_seconds, args.address)
    if not dev:
        print("ERROR: ring not found")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr})")

    frames_to_send = handshake_frames() + start_hr_frames()
    print("\n=== FRAMES THAT WOULD BE SENT (documented YCBT handshake) ===")
    for label, raw in frames_to_send:
        print(f"  {label:<28} {raw.hex()}  -> {json.dumps(parse_frame(raw))}")
    print("\n=== STOP FRAME (sent at end) ===")
    for label, raw in stop_hr_frames():
        print(f"  {label:<28} {raw.hex()}")

    if not args.enable_writes:
        print("\nDRY RUN - nothing written to the ring. Re-run with --enable-writes to perform the handshake.")
        return

    print("\n>>> WRITES ENABLED. Connecting, subscribing, sending handshake ...", flush=True)
    received: list[dict] = []
    hr_values: list[dict] = []

    def make_cb(channel: str):
        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "channel": channel, **parse_frame(raw)}
            received.append(rec)
            append_jsonl("ycbt_frames.jsonl", {**rec, "direction": "recv"})
            print(f"  <- {rec['raw_hex']}  {rec.get('meaning', rec.get('opcode', ''))}", flush=True)
            if rec.get("opcode") == "0601" and rec.get("crc_ok"):
                hr_values.append(rec)

        return cb

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        for u in (CMD_CHAR, STREAM_CHAR):
            if u not in chars:
                raise SystemExit(f"missing YCBT characteristic {u}")
            await client.start_notify(chars[u], make_cb("cmd" if u == CMD_CHAR else "stream"))
        print("subscribed to be940001 (cmd) + be940003 (stream)", flush=True)

        for label, raw in frames_to_send:
            print(f"  -> {label:<28} {raw.hex()}", flush=True)
            append_jsonl("ycbt_frames.jsonl", {"ts_utc": now_iso(), "direction": "send", "label": label, **parse_frame(raw)})
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(0.6)

        print(f"\nlistening {args.seconds}s for live HR (06 01) frames - ring must be WORN ...", flush=True)
        t0 = time.time()
        while time.time() - t0 < args.seconds:
            await asyncio.sleep(1)

        print("sending stop measurement ...", flush=True)
        for label, raw in stop_hr_frames():
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            append_jsonl("ycbt_frames.jsonl", {"ts_utc": now_iso(), "direction": "send", "label": label, **parse_frame(raw)})
        for u in (CMD_CHAR, STREAM_CHAR):
            await client.stop_notify(chars[u])

    # Decode the documented 06 01 payload: first byte = bpm.
    decoded_hr = []
    for r in hr_values:
        payload = bytes.fromhex(r["payload_hex"])
        bpm = payload[0] if payload else None
        decoded_hr.append(
            {
                "ts_utc": r["ts_utc"],
                "raw_hex": r["raw_hex"],
                "payload_hex": r["payload_hex"],
                "bpm": bpm,
                "plausible": bool(bpm and 30 <= bpm <= 250),
                "crc_ok": r.get("crc_ok"),
            }
        )

    summary = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "protocol": "Yucheng YCBT (be940000); CRC16/CCITT-FALSE verified on this unit",
        "frames_sent": [{"label": l, "hex": r.hex()} for l, r in frames_to_send + stop_hr_frames()],
        "frames_received": len(received),
        "hr_frames": len(hr_values),
        "decoded_hr": decoded_hr,
        "hr_payloads": [r["payload_hex"] for r in hr_values[:20]],
        "safety": "no DFU, no reset, no history delete, no terminal ACK, no OTA",
        "note": "06 01 payload byte 0 = bpm (documented); raw frames preserved verbatim",
    }
    p = write_json("ycbt_session.json", summary)
    print("\nSUMMARY", json.dumps(summary, indent=2))
    print("saved ->", p)
    print("raw frames -> out/ycbt_frames.jsonl")

    # FIRST SUCCESS CRITERION artefact, in the shape bridge.py consumes.
    valid = [d for d in decoded_hr if d["plausible"] and d["crc_ok"]]
    if valid:
        best = valid[0]
        measurement = {
            "captured_utc": now_iso(),
            "experiment": "first_measurement",
            "status": "SUCCESS",
            "device": {
                "name": name,
                "address": addr,
                "vendor": "Viaking / R30 PRO; Yucheng YCBT firmware",
                "source_label": "viaking_r30pro_experimental",
            },
            "genuine_measurements": {
                "heart_rate": {
                    "bpm": best["bpm"],
                    "unit": "bpm",
                    "source_frame": "06 01",
                    "payload_hex": best["payload_hex"],
                    "crc_validated": True,
                },
                "heart_rate_raw_hex": best["raw_hex"],
                "heart_rate_captured_utc": best["ts_utc"],
                "battery_level": None,
            },
            "validation": {
                "clinically_validated": False,
                "note": "Experimental wearable measurement - NOT for clinical conclusions.",
            },
            "safety": "documented YCBT handshake + measurement start/stop; no DFU, no delete, no reset",
        }
        mp = write_json("first_measurement.json", measurement)
        print(f"\n*** GENUINE MEASUREMENT: {best['bpm']} bpm ***")
        print("saved ->", mp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--scan-seconds", type=float, default=10.0)
    ap.add_argument("--seconds", type=float, default=45.0, help="listen duration after handshake")
    ap.add_argument("--enable-writes", action="store_true", help="actually send documented frames to the ring")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
