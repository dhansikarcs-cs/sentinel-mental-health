"""ECG probe - CONFIRMED vendor SDK opcodes, SINGLE-FINGER wear.

This ring measures ECG with the ring worn normally on one finger. No second
electrode contact is required (user correction; vendor doc's two-contact note
does not apply to this unit).

Opcodes from disassembled ycbtsdk-release-4.0.11.aar (not guesses):
  03 02 {02}     appEcgTestStart      | 03 02 {00} appEcgTestEnd
  03 0b {01,01}  AppControlWave ECG waveform upload (type 01 = ECG)
  06 05          Real_UploadECG waveform
  06 f0 / 06 f1  ECG HRV / ECG RR
  06 03          HR/BP/SpO2/temp during ECG
  04 0b          DeviceEndECG (ring -> app)
  03 14          AppECGPPGStatus (electrode/wear status)
  02 27          GetEcgMode (empty payload)
  07 00          ECG raw-file history query num

ORDER MATTERS: 0xFC = "unsupported Key" and aborts the rest of that session's
queries. So we start ECG FIRST with a minimal handshake, listen, then stop,
and only do optional info queries afterwards on a separate phase.

SAFETY: start/stop pairs only. No DFU, no deletes, no reset, no OTA, no
guessed command sequences. All frames use documented YCBT CRC framing.
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
from ycbt import crc16_ccitt_false, epoch_2000_local, frame, parse_frame

CMD_CHAR = "be940001-7333-be46-b7ae-689e71722bd5"
FORBIDDEN = {"0000fe59-0000-1000-8000-00805f9b34fb", "8ec90003-f315-4f60-9fb8-838830daea50"}

ECG_OPCODES = {"0605", "06f0", "06f1", "0603", "040b", "0314", "0227", "0700"}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=75.0)
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    # Validate CRC framing against the vendor's own example frame.
    crc = crc16_ccitt_false(bytes.fromhex("020008004743"))
    print(f"CRC self-check: 0x{crc:04x} vs vendor 6fec -> {'MATCH' if crc == 0xEC6F else 'MISMATCH'}\n", flush=True)

    # Advertising is intermittent (~4 s bursts). Retry until visible rather
    # than failing immediately - the user is wearing the ring for a short window.
    from bleak.backends.device import BLEDevice

    dev = None
    max_attempts = 40  # ~6 min: tolerates a case-reseat / advertising gap
    for attempt in range(1, max_attempts + 1):
        print(f"  scan attempt {attempt}/{max_attempts} ...", flush=True)
        candidate = await find_device(6.0, args.address)
        # find_device falls back to a cached ADDRESS STRING. Only accept a real,
        # currently-advertising BLEDevice - otherwise the connect will fail.
        if isinstance(candidate, BLEDevice):
            dev = candidate
            print("  ring is advertising - connecting now", flush=True)
            break
        print("  not visible yet (cached address only)", flush=True)
        await asyncio.sleep(3.0)
    if not dev:
        print("ERROR: ring never advertised. Wake it (tap / reseat on finger) and rerun.")
        return
    name, addr = device_meta(dev)
    print(f"target: {name} ({addr}) | single-finger wear | {args.seconds}s window\n", flush=True)

    frames: list[dict] = []
    nus: list[str] = []
    phase = {"n": "init"}

    def cb_factory(channel: str):
        buf = bytearray()

        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "phase": phase["n"], "channel": channel, "raw_hex": raw.hex(), "len": len(raw)}
            frames.append(rec)
            append_jsonl("probe_ecg_frames.jsonl", rec)

            if channel.startswith("6e4000"):
                try:
                    s = raw.decode("ascii").rstrip()
                    nus.append(s)
                    print(f"    NUS> {s}", flush=True)
                except UnicodeDecodeError:
                    pass
                return

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
                p = parse_frame(one)
                prec = {"ts_utc": now_iso(), "phase": phase["n"], "channel": channel, **p}
                frames.append(prec)
                append_jsonl("probe_ecg_frames.jsonl", prec)
                op = prec.get("opcode", "")
                flag = "  <<< ECG DATA" if op in ECG_OPCODES else ""
                print(
                    f"    <- {one.hex():<48} {op} payload={prec.get('payload_hex')} crc={prec.get('crc_ok')}{flag}",
                    flush=True,
                )

        return cb

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
                    except Exception as exc:  # noqa: BLE001
                        print(f"  subscribe refused {u[:8]}: {exc}", flush=True)
        print(f"  subscribed {len(subs)} channels\n", flush=True)

        async def send(label: str, raw: bytes, wait: float = 0.8):
            print(f"  -> {label:<34} {raw.hex()}", flush=True)
            append_jsonl(
                "probe_ecg_frames.jsonl",
                {"ts_utc": now_iso(), "phase": phase["n"], "direction": "send", "label": label, **parse_frame(raw)},
            )
            await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
            await asyncio.sleep(wait)

        # Minimal handshake - nothing that can return 0xFC before ECG starts.
        phase["n"] = "handshake"
        print("=== MINIMAL HANDSHAKE ===", flush=True)
        await send("set_time", frame(0x01, 0x00, epoch_2000_local()))
        await send("broadcast_enable", frame(0x03, 0x09))

        # ECG start FIRST.
        phase["n"] = "ecg_start"
        print("\n=== START ECG ===", flush=True)
        await send("start_waveform 03 0b {01,01}", frame(0x03, 0x0B, bytes([0x01, 0x01])), wait=1.2)
        await send("ecg_test_start 03 02 {02}", frame(0x03, 0x02, b"\x02"), wait=1.2)

        phase["n"] = "ecg_listen"
        print(f"\n=== LISTENING {args.seconds}s (keep ring still, one finger) ===", flush=True)
        before = len(frames)
        await asyncio.sleep(args.seconds)
        during = frames[before:]

        phase["n"] = "ecg_stop"
        print("\n=== STOP ECG (paired stops) ===", flush=True)
        await send("ecg_test_end 03 02 {00}", frame(0x03, 0x02, b"\x00"), wait=0.5)
        await send("stop_waveform 03 0b {00,01}", frame(0x03, 0x0B, bytes([0x00, 0x01])), wait=0.5)

        # Optional read-only info AFTER the measurement (0xFC here is harmless).
        phase["n"] = "info_queries"
        print("\n=== OPTIONAL INFO QUERIES (after measurement) ===", flush=True)
        await send("ecg_ppg_status 03 14", frame(0x03, 0x14), wait=1.0)
        await send("get_ecg_mode 02 27", frame(0x02, 0x27), wait=1.0)
        await send("ecg_file_query_num 07 00", frame(0x07, 0x00), wait=2.0)

        for u in subs:
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass

    waveforms = [
        f for f in frames if f.get("opcode") == "0605" or (f.get("raw_hex", "").startswith("0605") and "opcode" not in f)
    ]
    ecg_related = [f for f in frames if f.get("opcode") in ECG_OPCODES]

    report = {
        "captured_utc": now_iso(),
        "device": {"name": name, "address": addr},
        "method": "vendor SDK ECG opcodes; single-finger wear; ECG started before any query",
        "window_seconds": args.seconds,
        "crc_self_check": "MATCH" if crc == 0xEC6F else "MISMATCH",
        "total_frames": len(frames),
        "nus_console_lines": len(nus),
        "nus_lines": nus[:60],
        "ecg_waveform_frames": len(waveforms),
        "ecg_related_frames": [f.get("raw_hex") for f in ecg_related][:40],
        "verdict": "ECG_DATA" if waveforms else ("ECG_RELATED" if ecg_related else "NO_ECG"),
        "safety": "documented vendor opcodes only; start/stop pairs; no DFU/delete/reset/OTA",
    }
    p = write_json("probe_ecg_report.json", report)
    print("\n=== RESULT ===", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("saved ->", p, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
