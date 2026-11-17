"""Exhaustive YCBT probe - try EVERY documented measurement and history log.

Runs one BLE session:
  1. full handshake + capability bitmap
  2. all standard GATT reads (identity, battery, WeChat steps)
  3. spot measurement for HR / BP / SpO2 / HRV (03 2f {01, mode})
  4. every documented history query (05 <key>) with terminal ACK
  5. verbatim frame log + honest report of what actually returned data

Only DOCUMENTED opcodes are used (PulseLoop YCBT driver, verified on this unit
by CRC). NEVER touches Nordic DFU (0xFE59), NEVER sends history-delete opcodes
(05 40..05 4E), no reset, no OTA. Terminal ACK (05 80 {00}) is sent only when
the ring declares a completed transfer - it does not erase the log.

Usage: python probe_all.py [--enable-writes] [--seconds 18]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter

from bleak import BleakClient

from common import (
    append_jsonl,
    device_meta,
    find_device,
    iter_services,
    now_iso,
    parse_battery_level,
    write_json,
)
from ycbt import crc16_ccitt_false, frame, parse_frame

SERVICE = "be940000-7333-be46-b7ae-689e71722bd5"
CMD_CHAR = "be940001-7333-be46-b7ae-689e71722bd5"  # write + indicate (replies)
STREAM_CHAR = "be940003-7333-be46-b7ae-689e71722bd5"  # indicate (data)

STD_READS = {
    "00002a00-0000-1000-8000-00805f9b34fb": "device_name",
    "00002a19-0000-1000-8000-00805f9b34fb": "battery",
    "00002a29-0000-1000-8000-00805f9b34fb": "manufacturer",
    "00002a38-0000-1000-8000-00805f9b34fb": "body_sensor_location",
    "0000fec9-0000-1000-8000-00805f9b34fb": "wechat_mac",
    "0000fea1-0000-1000-8000-00805f9b34fb": "wechat_steps",
    "0000fea2-0000-1000-8000-00805f9b34fb": "wechat_target",
    "00002a04-0000-1000-8000-00805f9b34fb": "connection_params",
}

# 03 2f {01, mode} starts a spot measurement; {00, mode} stops it.
SPOT_MODES = {
    0x00: "heart_rate",
    0x01: "blood_pressure",
    0x02: "spo2",
    0x0A: "hrv",
}

# 05 <key> history queries (documented). NO delete keys (05 40..05 4E).
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

# Known live/data frame opcodes (type << 8 | cmd)
DATA_OPCODES = {
    0x0200: "device_info_reply",
    0x0201: "support_function_bitmap",
    0x0203: "device_name_reply",
    0x0228: "measurement_function",
    0x0226: "keep_alive",
    0x0309: "broadcast_enable_ack",
    0x032F: "measurement_control_ack",
    0x040E: "measurement_complete",
    0x0580: "history_terminal",
    0x0600: "activity_live",
    0x0601: "heart_rate_live",
    0x0602: "spo2_live",
    0x0603: "blood_pressure_live",
    0x0615: "battery_push",
    0xFFFF: "keepalive_frame",
}


def build(cmd_type: int, cmd: int, payload: bytes = b"") -> bytes:
    return frame(cmd_type, cmd, payload)


async def run(args) -> None:
    dev = await find_device(args.scan_seconds, args.address)
    if not dev:
        print("ERROR: ring not found - take it out of the case / charge it")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr})\n", flush=True)

    frames: list[dict] = []
    phase = {"name": "init"}

    def make_cb(channel: str):
        buf = bytearray()

        def cb(_char, data: bytearray) -> None:
            nonlocal buf
            buf.extend(bytes(data))
            # Reassemble using declared total length (frames split at MTU-3).
            while len(buf) >= 4:
                declared = int.from_bytes(buf[2:4], "little")
                if declared < 6 or declared > 512:
                    buf.clear()
                    break
                if len(buf) < declared:
                    break
                raw = bytes(buf[:declared])
                del buf[:declared]
                rec = {
                    "ts_utc": now_iso(),
                    "phase": phase["name"],
                    "channel": channel,
                    "direction": "recv",
                    **parse_frame(raw),
                }
                op = (raw[0] << 8) | raw[1]
                rec["opcode_name"] = DATA_OPCODES.get(op, "")
                frames.append(rec)
                append_jsonl("all_signals_frames.jsonl", rec)
                print(
                    f"  <- {rec['raw_hex']:<40} {rec.get('opcode_name') or rec.get('opcode',''):<28} "
                    f"payload={rec.get('payload_hex','')} crc={rec.get('crc_ok')}",
                    flush=True,
                )

        return cb

    async def send(label: str, raw: bytes, wait: float = 1.2) -> None:
        phase_rec = {
            "ts_utc": now_iso(),
            "phase": phase["name"],
            "channel": "cmd",
            "direction": "send",
            "label": label,
            **parse_frame(raw),
        }
        frames.append(phase_rec)
        append_jsonl("all_signals_frames.jsonl", phase_rec)
        print(f"  -> {label:<32} {raw.hex()}", flush=True)
        if args.enable_writes:
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(wait)
        else:
            print("     [DRY RUN - not sent]", flush=True)

    async def listen(label: str, secs: float) -> None:
        before = len(frames)
        print(f"  ... listening {secs}s for {label}", flush=True)
        await asyncio.sleep(secs)
        got = [f for f in frames[before:] if f["direction"] == "recv"]
        print(f"  ... got {len(got)} frames for {label}", flush=True)

    async with BleakClient(dev, timeout=30.0) as client:
        chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
        await client.start_notify(chars[CMD_CHAR], make_cb("cmd"))
        await client.start_notify(chars[STREAM_CHAR], make_cb("stream"))
        print("subscribed to be940001 + be940003\n", flush=True)

        # ── 0. Standard GATT reads ─────────────────────────────────────────
        phase["name"] = "standard_gatt_reads"
        std_results = {}
        for uuid, label in STD_READS.items():
            if uuid not in chars:
                std_results[label] = None
                continue
            try:
                raw = bytes(await client.read_gatt_char(chars[uuid]))
                rec = {
                    "ts_utc": now_iso(),
                    "phase": phase["name"],
                    "direction": "read",
                    "label": label,
                    "uuid": uuid,
                    "hex": raw.hex(),
                    "decoded_battery": parse_battery_level(raw) if label == "battery" else None,
                }
                frames.append(rec)
                append_jsonl("all_signals_frames.jsonl", rec)
                std_results[label] = raw.hex()
                try:
                    ascii_val = raw.decode("utf-8").strip("\x00")
                except UnicodeDecodeError:
                    ascii_val = None
                print(f"  READ {label:<26} {raw.hex():<32} ascii={ascii_val}", flush=True)
            except Exception as exc:  # noqa: BLE001
                std_results[label] = f"ERROR: {exc}"
                print(f"  READ {label:<26} FAILED {exc}", flush=True)

        # ── 1. Handshake ───────────────────────────────────────────────────
        phase["name"] = "handshake"
        print("\n=== HANDSHAKE ===", flush=True)
        handshake = [
            ("get_device_name", build(0x02, 0x03)),
            ("set_time", build(0x01, 0x00, int(time.time() - 946684800).to_bytes(4, "little"))),
            ("get_support_function", build(0x02, 0x01)),
            ("get_measurement_function", build(0x02, 0x28)),
            ("get_device_info", build(0x02, 0x00)),
            ("broadcast_enable", build(0x03, 0x09)),
        ]
        for label, raw in handshake:
            await send(label, raw, wait=1.5)
        await listen("handshake replies", 4.0)

        # ── 2. Spot measurements ───────────────────────────────────────────
        spot_results = {}
        for mode, label in SPOT_MODES.items():
            phase["name"] = f"spot_{label}"
            print(f"\n=== SPOT MEASUREMENT: {label} (mode 0x{mode:02x}) ===", flush=True)
            before = len([f for f in frames if f["direction"] == "recv"])
            await send(f"start_{label}", build(0x03, 0x2F, bytes([0x01, mode])), wait=1.0)
            await listen(label, args.seconds)
            await send(f"stop_{label}", build(0x03, 0x2F, bytes([0x00, mode])), wait=0.8)
            new = [
                f
                for f in frames[before:]
                if f["direction"] == "recv" and f.get("crc_ok") and f.get("payload_hex")
            ]
            spot_results[label] = {
                "frames_with_payload": len(new),
                "payloads": [f["payload_hex"] for f in new[:12]],
                "opcodes": sorted({f.get("opcode_name") or f.get("opcode") for f in new}),
            }

        # ── 3. History queries ─────────────────────────────────────────────
        hist_results = {}
        for key, label in HISTORY_KEYS.items():
            phase["name"] = f"history_{label}"
            print(f"\n=== HISTORY: {label} (05 {key:02x}) ===", flush=True)
            before = len([f for f in frames if f["direction"] == "recv"])
            await send(f"query_{label}", build(0x05, key), wait=1.0)
            await listen(label, args.history_seconds)
            got = [f for f in frames[before:] if f["direction"] == "recv"]
            terminal = any(f.get("opcode") == "0580" for f in got)
            if terminal and args.enable_writes:
                await send("terminal_ack (no delete)", build(0x05, 0x80, b"\x00"), wait=0.8)
            hist_results[label] = {
                "frames": len(got),
                "terminal_seen": terminal,
                "opcodes": sorted({f.get("opcode_name") or f.get("opcode") for f in got}),
                "payloads": [f["payload_hex"] for f in got if f.get("payload_hex")][:8],
            }

        # ── 4. WeChat steps + keep-alive ───────────────────────────────────
        phase["name"] = "final"
        print("\n=== FINAL: keep-alive + WeChat steps ===", flush=True)
        await send("keep_alive", build(0x02, 0x26), wait=1.0)
        await listen("final", 3.0)
        if "0000fea1-0000-1000-8000-00805f9b34fb" in chars:
            try:
                raw = bytes(await client.read_gatt_char(chars["0000fea1-0000-1000-8000-00805f9b34fb"]))
                print(f"  READ wechat_steps (final) {raw.hex()}", flush=True)
                std_results["wechat_steps_final"] = raw.hex()
            except Exception as exc:  # noqa: BLE001
                print("  wechat steps read failed:", exc, flush=True)

        for u in (CMD_CHAR, STREAM_CHAR):
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    recv = [f for f in frames if f["direction"] == "recv"]
    by_opcode = dict(Counter(f.get("opcode_name") or f.get("opcode") or "?" for f in recv))

    # Only count frames that carried actual measurement payload as "data".
    data_frames = [f for f in recv if f.get("crc_ok") and f.get("payload_hex")]
    collected = sorted({f.get("opcode_name") or f.get("opcode") for f in data_frames})

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "protocol": "Yucheng YCBT (be940000); CRC16/CCITT-FALSE verified on this unit",
        "writes_enabled": args.enable_writes,
        "total_frames_logged": len(frames),
        "frames_received": len(recv),
        "by_opcode": by_opcode,
        "frames_carrying_payload": len(data_frames),
        "opcodes_that_returned_data": collected,
        "standard_gatt_reads": std_results,
        "spot_measurements": spot_results,
        "history_queries": hist_results,
        "safety": "documented opcodes only; no DFU, no delete, no reset, no OTA, no guessed commands",
        "note": "payloads preserved verbatim in out/all_signals_frames.jsonl; scales not validated",
    }
    p = write_json("all_signals_report.json", report)
    print("\n" + "=" * 70)
    print("REPORT")
    print("=" * 70)
    print(json.dumps(report, indent=2))
    print("\nsaved ->", p)
    print("raw frames -> out/all_signals_frames.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=None)
    ap.add_argument("--scan-seconds", type=float, default=10.0)
    ap.add_argument("--seconds", type=float, default=18.0, help="listen per spot measurement")
    ap.add_argument("--history-seconds", type=float, default=6.0, help="listen per history query")
    ap.add_argument("--enable-writes", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
