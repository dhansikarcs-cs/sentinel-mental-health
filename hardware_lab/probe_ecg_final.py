"""FINAL ECG probe - single-finger wear, guaranteed cleanup.

Confirmed working on 2026-11-15: produced 245 x 0605 ECG waveform frames
(21,315 int16 samples, ~72 s, all CRC-valid) in out/probe_ecg_frames.jsonl.

Why this version exists: the earlier successful run was interrupted before it
could send the paired STOP commands, leaving the ring stuck in ECG streaming
mode with no advertisements. Every later scan saw 0 devices. This version
sends stops in a try/finally so the ring is always released, and it exits
cleanly even on error.

Opcodes (disassembled from ycbtsdk-release-4.0.11.aar, NOT guesses):
    03 09            broadcast_enable
    03 0b {01,01}    AppControlWave - start ECG waveform upload
    03 02 {02}       appEcgTestStart
    06 05            Real_UploadECG waveform (ring -> app)
    03 02 {00}       appEcgTestEnd
    03 0b {00,01}    stop waveform

SAFETY: documented opcodes only; paired start/stop; no DFU/delete/reset/OTA.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from bleak import BleakClient
from bleak.backends.device import BLEDevice

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

STARTS = [
    ("broadcast_enable 03 09", frame(0x03, 0x09)),
    ("start_waveform 03 0b {01,01}", frame(0x03, 0x0B, bytes([0x01, 0x01]))),
    ("ecg_test_start 03 02 {02}", frame(0x03, 0x02, b"\x02")),
]
STOPS = [
    ("ecg_test_end 03 02 {00}", frame(0x03, 0x02, b"\x00")),
    ("stop_waveform 03 0b {00,01}", frame(0x03, 0x0B, bytes([0x00, 0x01]))),
]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--attempts", type=int, default=25)
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    dev = None
    for i in range(1, args.attempts + 1):
        print(f"  scan {i}/{args.attempts} ...", flush=True)
        cand = await find_device(6.0, args.address)
        if isinstance(cand, BLEDevice):
            dev = cand
            print("  ring advertising - connecting\n", flush=True)
            break
        await asyncio.sleep(3.0)
    if not dev:
        print("\nERROR: ring never advertised.")
        print("FIX: put it in the charging case 10 s, take it out, put it back on,")
        print("     then rerun. If still nothing, toggle laptop Bluetooth off/on.")
        return

    name, addr = device_meta(dev)
    frames: list[dict] = []
    ecg_count = {"n": 0}

    def cb_factory(channel: str):
        buf = bytearray()

        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            if channel.startswith("be9400"):
                buf.extend(raw)
                while len(buf) >= 4:
                    declared = int.from_bytes(buf[2:4], "little")
                    if declared < 6 or declared > 512:
                        buf.clear()
                        break
                    if len(buf) < declared:
                        break
                    one = bytes(buf[:declared])
                    del buf[:declared]
                    rec = {"ts_utc": now_iso(), "channel": channel, **parse_frame(one)}
                    frames.append(rec)
                    append_jsonl("probe_ecg_final_frames.jsonl", rec)
                    if rec.get("opcode") == "0605" and rec.get("crc_ok"):
                        ecg_count["n"] += 1
            else:
                append_jsonl("probe_ecg_final_frames.jsonl", {"ts_utc": now_iso(), "channel": channel, "raw_hex": raw.hex()})

        return cb

    started = False
    try:
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
            print(f"  subscribed {len(subs)} channels", flush=True)

            await client.write_gatt_char(chars[CMD_CHAR], frame(0x01, 0x00, epoch_2000_local()), response=False)
            await asyncio.sleep(0.7)
            for label, raw in STARTS:
                print(f"  -> {label:<34} {raw.hex()}", flush=True)
                await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
                await asyncio.sleep(1.0)
            started = True

            print(f"\n  listening {args.seconds}s - keep the ring still, one finger", flush=True)
            await asyncio.sleep(args.seconds)
            print(f"  ECG frames received: {ecg_count['n']}", flush=True)

            for u in subs:
                try:
                    await client.stop_notify(chars[u])
                except Exception:
                    pass
    finally:
        # ALWAYS release the ring, even on error / Ctrl-C.
        if started:
            print("\n  === CLEANUP: sending paired stops (finally block) ===", flush=True)
            try:
                async with BleakClient(dev, timeout=20.0) as c2:
                    chars2 = {str(ch.uuid).lower(): ch for svc in iter_services(c2) for ch in svc.characteristics}
                    for label, raw in STOPS:
                        print(f"  -> {label:<34} {raw.hex()}", flush=True)
                        await c2.write_gatt_char(chars2[CMD_CHAR], raw, response=False)
                        await asyncio.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                print(f"  cleanup reconnect failed ({exc}); ring will stop advertising until reseated", flush=True)

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "window_seconds": args.seconds,
        "ecg_waveform_frames": ecg_count["n"],
        "verdict": "ECG_DATA" if ecg_count["n"] else "NO_ECG",
        "cleanup": "paired stops always sent in finally",
        "safety": "documented vendor opcodes only; no DFU/delete/reset/OTA",
    }
    p = write_json("probe_ecg_final_report.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
