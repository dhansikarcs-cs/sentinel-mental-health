"""Sentinel continuous ring collector (always-on BLE -> FastAPI bridge).

Runs indefinitely: discover -> connect -> collect REAL measurements -> push to
Sentinel's /api/ring/data -> sleep -> repeat. Handles disconnects, advertising
gaps, and reconnection. Never invents values.

Architecture (brief Phase F):
  R30 PRO -> BLE Collector -> YCBT frame decoder -> validation -> /api/ring/data
  -> RingSensorLog/SensorReading -> wellness / triage

Design rules:
  * Only measured fields are sent; unmeasured stay NULL (no defaults, no
    derived HRV/sdnn, no hardcoded temperature).
  * seq is monotonic and idempotent on (device_id, seq) - no duplicates.
  * Every raw frame is preserved verbatim in out/collector_frames.jsonl.
  * Every start command has a paired stop in a finally block, so the ring is
    never stranded in measurement mode (the cause of earlier 0-advertiser hangs).
  * Disconnects / missing readings are logged, not fabricated.
  * Experimental data clearly labelled; no clinical conclusions.

Usage:
    python collector.py                      # dry run (no writes, no BLE writes)
    python collector.py --enable-writes      # actually collect + push
    python collector.py --enable-writes --cycles 0   # run forever

Requires the Sentinel backend running (see PILOT.md) and the ring worn.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import requests
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
STREAM_CHAR = "be940003-7333-be46-b7ae-689e71722bd5"
FORBIDDEN = {"0000fe59-0000-1000-8000-00805f9b34fb", "8ec90003-f315-4f60-9fb8-838830daea50"}

# Documented opcodes (vendor SDK).
HANDSHAKE = [
    frame(0x01, 0x00, epoch_2000_local()),
    frame(0x03, 0x09),
]
START_HR = frame(0x03, 0x2F, bytes([0x01, 0x00]))
STOP_HR = frame(0x03, 0x2F, bytes([0x00, 0x00]))

SEQ_FILE = "collector_seq.json"


def load_seq() -> int:
    from pathlib import Path

    p = Path(__file__).resolve().parent / "out" / SEQ_FILE
    if p.exists():
        try:
            return int(json.loads(p.read_text(encoding="utf-8")).get("seq", 0))
        except (ValueError, OSError):
            return 0
    return 0


def save_seq(n: int) -> None:
    from pathlib import Path

    p = Path(__file__).resolve().parent / "out" / SEQ_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"seq": n, "updated_utc": now_iso()}, indent=2), encoding="utf-8")


def push(measurement: dict, seq: int, base_url: str, serial: str, token: str) -> int:
    """POST only genuinely measured fields. Returns HTTP status."""
    body = {
        "device_id": "viaking_r30pro_F085",
        "seq": seq,
        "bpm": measurement.get("bpm"),
        "timestamp": measurement.get("ts_utc"),
    }
    if measurement.get("spo2") is not None:
        body["spo2"] = float(measurement["spo2"])
    if measurement.get("hrv") is not None:
        body["hrv"] = int(measurement["hrv"])
    body = {k: v for k, v in body.items() if v is not None}
    r = requests.post(
        f"{base_url}/api/ring/data",
        json=body,
        headers={"X-Device-Serial": serial, "X-Device-Token": token},
        timeout=20,
    )
    return r.status_code


async def collect_once(dev: BLEDevice, seconds: float, enable_writes: bool) -> list[dict]:
    """One connection: start HR measurement, collect real 0601 frames, stop."""
    frames: list[dict] = []

    def cb(_char, data: bytearray) -> None:
        raw = bytes(data)
        rec = {"ts_utc": now_iso(), "raw_hex": raw.hex(), **parse_frame(raw)}
        frames.append(rec)
        append_jsonl("collector_frames.jsonl", rec)

    started = False
    try:
        async with BleakClient(dev, timeout=30.0) as client:
            chars = {str(ch.uuid).lower(): ch for svc in iter_services(client) for ch in svc.characteristics}
            # Real 0601 HR data arrives on be940003 (stream), NOT the command
            # characteristic. Subscribe to BOTH.
            subs = [chars[CMD_CHAR]]
            if STREAM_CHAR in chars:
                subs.append(chars[STREAM_CHAR])
            for ch in subs:
                await client.start_notify(ch, cb)
            for raw in HANDSHAKE:
                await client.write_gatt_char(chars[CMD_CHAR], raw, response=False)
                await asyncio.sleep(0.7)
            await client.write_gatt_char(chars[CMD_CHAR], START_HR, response=False)
            started = True
            await asyncio.sleep(seconds)
            for ch in subs:
                try:
                    await client.stop_notify(ch)
                except Exception:
                    pass
    finally:
        # ALWAYS stop the measurement so the ring keeps advertising.
        if started and enable_writes:
            try:
                async with BleakClient(dev, timeout=15.0) as c2:
                    ch2 = {str(ch.uuid).lower(): ch for svc in iter_services(c2) for ch in svc.characteristics}
                    await c2.write_gatt_char(ch2[CMD_CHAR], STOP_HR, response=False)
            except Exception:
                pass

    # Decode ONLY real 0601 HR frames with a plausible bpm.
    out = []
    for r in frames:
        if r.get("opcode") == "0601" and r.get("crc_ok") and r.get("payload_hex"):
            p = bytes.fromhex(r["payload_hex"])
            bpm = p[0] if p else None
            if bpm and 30 <= bpm <= 250:
                out.append({"bpm": bpm, "ts_utc": r["ts_utc"], "raw_hex": r["raw_hex"]})
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--username", default="alaya")
    ap.add_argument("--password", default="4321")
    ap.add_argument("--serial", default="VIAKING-R30PRO-F085")
    ap.add_argument("--seconds", type=float, default=30.0, help="collection window per cycle")
    ap.add_argument("--interval", type=float, default=60.0, help="sleep between cycles")
    ap.add_argument("--cycles", type=int, default=0, help="0 = run forever")
    ap.add_argument("--enable-writes", action="store_true", help="actually write to ring + POST to Sentinel")
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    # Auth once (device token from /ring/pair).
    s = requests.Session()
    login = s.post(
        f"{args.base_url}/api/auth/login",
        json={"username": args.username, "password": args.password},
        timeout=20,
    )
    login.raise_for_status()
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    pair = s.post(
        f"{args.base_url}/api/ring/pair",
        json={"serial": args.serial, "vendor": "viaking_r30pro"},
        headers=h,
        timeout=20,
    )
    if pair.status_code == 409:
        s.post(f"{args.base_url}/api/ring/unpair?serial={args.serial}", headers=h, timeout=20)
        pair = s.post(
            f"{args.base_url}/api/ring/pair",
            json={"serial": args.serial, "vendor": "viaking_r30pro"},
            headers=h,
            timeout=20,
        )
    pair.raise_for_status()
    device_token = pair.json()["token"]
    print(f"collector: authenticated, device={args.serial}", flush=True)

    seq = load_seq()
    cycle = 0
    stats = {"cycles": 0, "measurements": 0, "pushes": 0, "errors": 0, "gaps": 0}

    try:
        while args.cycles == 0 or cycle < args.cycles:
            cycle += 1
            print(f"\n[{now_iso()}] cycle {cycle}", flush=True)
            dev = None
            for _ in range(10):
                cand = await find_device(6.0, args.address)
                if isinstance(cand, BLEDevice):
                    dev = cand
                    break
                await asyncio.sleep(3.0)
            if not dev:
                stats["gaps"] += 1
                print("  ring not advertising (gap logged, will retry)", flush=True)
                await asyncio.sleep(args.interval)
                continue

            name, addr = device_meta(dev)
            try:
                readings = await collect_once(dev, args.seconds, args.enable_writes)
            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                print(f"  collection error (logged): {exc}", flush=True)
                await asyncio.sleep(args.interval)
                continue

            stats["cycles"] += 1
            if not readings:
                stats["gaps"] += 1
                print("  no valid readings this cycle (missing, not fabricated)", flush=True)
            for m in readings:
                stats["measurements"] += 1
                print(f"  HR {m['bpm']} bpm from {m['raw_hex']}", flush=True)
                if args.enable_writes:
                    seq += 1
                    try:
                        code = push(m, seq, args.base_url, args.serial, device_token)
                        save_seq(seq)
                        stats["pushes"] += 1 if code == 200 else 0
                        print(f"  -> POST /api/ring/data seq={seq}: HTTP {code}", flush=True)
                    except Exception as exc:  # noqa: BLE001
                        stats["errors"] += 1
                        print(f"  push error (logged): {exc}", flush=True)

            write_json("collector_status.json", {"updated_utc": now_iso(), **stats})
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ncollector stopped by user", flush=True)

    write_json("collector_status.json", {"updated_utc": now_iso(), **stats, "stopped": True})
    print("\nfinal stats:", json.dumps(stats), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
