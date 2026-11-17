"""Once-a-day sync: pull the ring's STORED history and push to Sentinel.

This is what makes a real patient workflow possible: the ring logs readings
internally all day while worn, then once a day the patient sits near this
gateway laptop and we pull the stored records and push them to the UI's DB.

Proven on hardware: 05 06 returned real HR records (89/85/83/74 bpm) that
matched the live readings exactly, and 05 09 combined records carried
SpO2/HRV/temperature.

Read-only on the ring except the mandatory 05 80 terminal ACK (which does NOT
erase history - delete opcodes 05 40..05 4E are never sent).

Usage:
    python sync_history.py --from-log                # offline decoder test
    python sync_history.py --enable-writes          # live ring + push
    python sync_history.py --enable-writes --base-url https://... \
        --username alaya --password 4321 --serial VIAKING-R30PRO-ALAYA
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import requests
from bleak import BleakClient
from bleak.backends.device import BLEDevice

from common import append_jsonl, device_meta, find_device, iter_services, now_iso, write_json
from ycbt import epoch_2000_local, frame, parse_frame

OUT = Path(__file__).resolve().parent / "out"
CMD_CHAR = "be940001-7333-be46-b7ae-689e71722bd5"
FORBIDDEN = {"0000fe59-0000-1000-8000-00805f9b34fb", "8ec90003-f315-4f60-9fb8-838830daea50"}

# Vendor Get tags that fixed the 0xFE "Data error" problem.
GET_TAGS = {0x00: "4743", 0x01: "4746", 0x03: "4750", 0x28: "4746"}

QUERIES = {
    "heart_rate_history": 0x06,
    "blood_pressure_history": 0x08,
    "combined_all_day": 0x09,
}

SEQ_FILE = OUT / "sync_seq.json"


def load_seq() -> int:
    if SEQ_FILE.exists():
        try:
            return int(json.loads(SEQ_FILE.read_text(encoding="utf-8")).get("seq", 0))
        except (ValueError, OSError):
            return 0
    return 0


def save_seq(n: int) -> None:
    SEQ_FILE.write_text(json.dumps({"seq": n, "updated_utc": now_iso()}, indent=2), encoding="utf-8")


def decode_hr_history(payload: bytes) -> list[dict]:
    """0515 data: N x 6 B = [ts:u32 LE][sep][bpm]."""
    out = []
    for i in range(0, len(payload) - 5, 6):
        rec = payload[i : i + 6]
        bpm = rec[5]
        if 30 <= bpm <= 250:
            out.append({"bpm": bpm, "ts_raw": f"0x{int.from_bytes(rec[:4], 'little'):08x}"})
    return out


def decode_combined(payload: bytes) -> list[dict]:
    """0518 data: N x 20 B. Vendor doc 3367-3437 offsets; 0 fields ignored."""
    out = []
    for i in range(0, len(payload) - 19, 20):
        r = payload[i : i + 20]
        ti, tf = r[13], r[14]
        temp = float(f"{ti}.{tf}") if ti != 0 and tf != 15 else None
        out.append(
            {
                "bpm": r[6] or None,
                "spo2": r[9] or None,
                "hrv": r[11] or None,
                "temperature_c": temp,
                "systolic": r[7] or None,
                "diastolic": r[8] or None,
                "ts_raw": f"0x{int.from_bytes(r[:4], 'little'):08x}",
            }
        )
    return out


async def collect_frames(dev: BLEDevice, enable_writes: bool) -> list[dict]:
    frames: list[dict] = []

    def cb_factory(channel: str):
        buf = bytearray()

        def cb(_char, data: bytearray) -> None:
            raw = bytes(data)
            rec = {"ts_utc": now_iso(), "channel": channel, **parse_frame(raw)}
            frames.append(rec)
            append_jsonl("sync_history_frames.jsonl", rec)

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
                    except Exception:
                        pass

        if enable_writes:
            await client.write_gatt_char(chars[CMD_CHAR], frame(0x01, 0x00, epoch_2000_local()), response=False)
            await asyncio.sleep(0.7)
            for xx, tag in GET_TAGS.items():
                await client.write_gatt_char(chars[CMD_CHAR], frame(0x02, xx, bytes.fromhex(tag)), response=False)
                await asyncio.sleep(0.7)
            await client.write_gatt_char(chars[CMD_CHAR], frame(0x03, 0x09), response=False)
            await asyncio.sleep(0.7)
            for label, key in QUERIES.items():
                await client.write_gatt_char(chars[CMD_CHAR], frame(0x05, key), response=False)
                await asyncio.sleep(4.0)
                terminal = any(f.get("opcode") == "0580" for f in frames)
                if terminal:
                    await client.write_gatt_char(chars[CMD_CHAR], frame(0x05, 0x80, b"\x00"), response=False)
                    await asyncio.sleep(0.3)
        for u in subs:
            try:
                await client.stop_notify(chars[u])
            except Exception:
                pass
    return frames


def extract(frames: list[dict]) -> dict:
    """Decode and DEDUPE (same record seen across multiple sync runs).

    The ring's 4-byte ts bytes are NOT valid epoch-2000 seconds (they decode
    to years 2040-2099), so we do NOT treat them as real timestamps. We use
    them only as an opaque identity key for deduplication and stamp records
    with the sync time instead.
    """
    hr_seen: dict[tuple, dict] = {}
    cb_seen: dict[tuple, dict] = {}
    for f in frames:
        if not f.get("crc_ok") or not f.get("payload_hex"):
            continue
        p = bytes.fromhex(f["payload_hex"])
        op = f.get("opcode")
        if op == "0515":
            for r in decode_hr_history(p):
                hr_seen[(r["ts_raw"], r["bpm"])] = r
        elif op == "0518":
            for r in decode_combined(p):
                key = (r["ts_raw"], r["bpm"], r["spo2"], r["hrv"], r["temperature_c"])
                cb_seen[key] = r
    return {
        "hr_records": list(hr_seen.values()),
        "combined_records": list(cb_seen.values()),
        "timestamp_policy": "ring ts bytes are opaque IDs, not decoded wall-clock; records stamped with sync time",
    }


def push_record(rec: dict, seq: int, args) -> int:
    # Stable device identity shared with collector.py / seed_recorded.py so
    # all real pushes land under one device_id (idempotency key is (device_id, seq)).
    body = {"device_id": "viaking_r30pro_F085", "seq": seq, "timestamp": now_iso()}
    for k in ("bpm", "spo2", "hrv", "temperature_c"):
        if rec.get(k) is not None:
            key = "temperature" if k == "temperature_c" else k
            # /api/ring/data has no temperature column - pushed via sensor-readings instead
            if key == "temperature":
                continue
            body[key] = rec[k]
    body = {k: v for k, v in body.items() if v is not None}
    r = requests.post(
        f"{args.base_url}/api/ring/data",
        json=body,
        headers={"X-Device-Serial": args.serial, "X-Device-Token": args.token},
        timeout=20,
    )
    return r.status_code


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-log", action="store_true", help="offline: decode captured frames, no BLE/HTTP")
    ap.add_argument("--enable-writes", action="store_true")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--username", default="alaya")
    ap.add_argument("--password", default="4321")
    ap.add_argument("--serial", default="VIAKING-R30PRO-ALAYA")
    ap.add_argument("--token", default="")
    ap.add_argument("--address", default=None)
    args = ap.parse_args()

    if args.from_log:
        log = OUT / "probe_history_frames.jsonl"
        frames = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
        data = extract(frames)
        print("=== OFFLINE DECODER TEST (no ring, no HTTP) ===")
        print(json.dumps(data, indent=2))
        write_json("sync_history_offline.json", data)
        print("saved -> out/sync_history_offline.json")
        return

    dev = None
    for _ in range(12):
        cand = await find_device(6.0, args.address)
        if isinstance(cand, BLEDevice):
            dev = cand
            break
        await asyncio.sleep(3.0)
    if not dev:
        print("ERROR: ring not advertising. Reseat in case 10 s, rewear, rerun.")
        return

    name, addr = device_meta(dev)
    print(f"target: {name} ({addr})", flush=True)
    frames = await collect_frames(dev, args.enable_writes)
    data = extract(frames)
    print(f"decoded: {len(data['hr_records'])} HR, {len(data['combined_records'])} combined", flush=True)

    # Build one push per record; combining bpm+spo2+hrv where available.
    records = []
    for h in data["hr_records"]:
        records.append({"bpm": h["bpm"], "ts_raw": h["ts_raw"]})
    for c in data["combined_records"]:
        if any(c.get(k) is not None for k in ("bpm", "spo2", "hrv")):
            records.append(c)
    print(f"records to push: {len(records)}", flush=True)

    if args.enable_writes:
        token = args.token
        if not token:
            # Pair automatically while logged in as the patient (one command).
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
            token = pair.json()["token"]
            print("  auto-paired device", flush=True)
        args.token = token
        seq = load_seq()
        for rec in records:
            seq += 1
            code = push_record(rec, seq, args)
            save_seq(seq)
            print(f"  seq={seq} {rec} -> HTTP {code}", flush=True)

    write_json("sync_history_result.json", {**data, "records_to_push": len(records), "enable_writes": args.enable_writes})
    print("saved -> out/sync_history_result.json", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
