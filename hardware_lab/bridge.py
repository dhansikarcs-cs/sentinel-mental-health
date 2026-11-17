"""Phase F - Sentinel ingestion bridge (DESIGN STUB, deliberately gated).

Usage:
    python bridge.py                                  # dry-run: print exact payload, send nothing
    python bridge.py --measurement out/first_measurement.json
    python bridge.py --pair --base-url http://localhost:8000 --jwt <patient-jwt>
    python bridge.py --send --i-have-a-validated-measurement \
        --i-accept-backend-defaults --base-url http://localhost:8000

Sentinel already exposes the ingestion contract:
    POST /api/ring/pair   {serial, vendor}  -> token   (patient JWT required)
    POST /api/ring/data   X-Device-Serial + X-Device-Token, body {device_id, bpm,
                          stress, sleep_hours, spo2, hrv, seq, timestamp}
                          idempotent on (device_id, seq)

BLOCKING DESIGN ISSUE (see FINDINGS.md): SensorDataCreate gives `stress=35`,
`sleep_hours=7.0`, `spo2=98.0`, `hrv=50` as DEFAULTS. A partial push containing
only `bpm` would silently store four fabricated clinical values. Do not send to
the live system until the backend accepts nullable/partial wearable payloads.

This file DOES NOT run automatically and DOES NOT touch the live deployment by
default. It is here to make the integration contract concrete.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import LAB_DIR, OUT_DIR, now_iso, write_json

SECRETS = LAB_DIR / "local_secrets.json"  # gitignored
SEQ_FILE = OUT_DIR / "seq.json"


def load_measurement(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = LAB_DIR / p
    if not p.exists():
        raise SystemExit(f"measurement file not found: {p} (run measure.py first)")
    return json.loads(p.read_text(encoding="utf-8"))


def next_seq() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cur = 0
    if SEQ_FILE.exists():
        cur = int(json.loads(SEQ_FILE.read_text(encoding="utf-8")).get("seq", 0))
    nxt = cur + 1
    SEQ_FILE.write_text(json.dumps({"seq": nxt, "updated_utc": now_iso()}, indent=2), encoding="utf-8")
    return nxt


def build_payload(measurement: dict, device_id: str) -> dict:
    hr = measurement.get("genuine_measurements", {}).get("heart_rate") or {}
    bpm = hr.get("bpm")
    if not bpm or not (30 <= bpm <= 250):
        raise SystemExit("no plausible heart_rate in measurement - refusing to fabricate a value")
    return {
        "device_id": device_id,
        "bpm": int(bpm),
        "seq": next_seq(),
        "timestamp": measurement.get("genuine_measurements", {}).get("heart_rate_captured_utc") or now_iso(),
        "_experimental": {
            "source_label": "viaking_r30pro_experimental",
            "raw_hex": measurement.get("genuine_measurements", {}).get("heart_rate_raw_hex"),
            "note": "unvalidated wearable measurement - label, never treat as clinical truth",
        },
    }


def save_secrets(serial: str, token: str) -> None:
    SECRETS.write_text(
        json.dumps({"serial": serial, "device_token": token, "saved_utc": now_iso()}, indent=2),
        encoding="utf-8",
    )
    print("device token saved to local_secrets.json (gitignored)")


def pair(base_url: str, jwt: str, serial: str) -> None:
    import requests

    r = requests.post(
        f"{base_url}/api/ring/pair",
        json={"serial": serial, "vendor": "viaking_r30pro_experimental"},
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=30,
    )
    print("pair HTTP", r.status_code)
    if r.status_code != 200:
        raise SystemExit(r.text[:500])
    save_secrets(serial, r.json()["token"])


def send(base_url: str, body: dict) -> None:
    import requests

    if not SECRETS.exists():
        raise SystemExit("no device token - run --pair first")
    s = json.loads(SECRETS.read_text(encoding="utf-8"))
    # Strip the private _experimental envelope before hitting the real API.
    public = {k: v for k, v in body.items() if not k.startswith("_")}
    r = requests.post(
        f"{base_url}/api/ring/data",
        json=public,
        headers={"X-Device-Serial": s["serial"], "X-Device-Token": s["device_token"]},
        timeout=30,
    )
    print("push HTTP", r.status_code, r.text[:500])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--measurement", default="out/first_measurement.json")
    ap.add_argument("--device-id", default="viaking_r30pro_C1752186F085")
    ap.add_argument("--pair", action="store_true")
    ap.add_argument("--jwt", default=os.environ.get("SENTINEL_PATIENT_JWT", ""))
    ap.add_argument("--serial", default="VIAKING-R30PRO-F085")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--i-have-a-validated-measurement", action="store_true")
    ap.add_argument("--i-accept-backend-defaults", action="store_true")
    args = ap.parse_args()

    if args.pair:
        if not args.jwt:
            raise SystemExit("--pair needs --jwt (or SENTINEL_PATIENT_JWT env)")
        pair(args.base_url, args.jwt, args.serial)
        return

    m = load_measurement(args.measurement)
    body = build_payload(m, args.device_id)
    print("\n--- DRY RUN: exact payload that WOULD be sent ---")
    print(json.dumps(body, indent=2))
    print("\nHeaders: X-Device-Serial, X-Device-Token  (from POST /api/ring/pair)")
    print("Endpoint:", f"{args.base_url}/api/ring/data")
    print("\nWARNING: backend SensorDataCreate defaults will inject stress=35,")
    print("sleep_hours=7.0, spo2=98.0, hrv=50 unless the API is changed to accept")
    print("nullable partial wearable payloads. See FINDINGS.md Phase F.")

    if args.send:
        if not args.i_have_a_validated_measurement:
            raise SystemExit("refusing: pass --i-have-a-validated-measurement")
        if not args.i_accept_backend_defaults:
            raise SystemExit("refusing: pass --i-accept-backend-defaults")
        if "sentinelpsytech.com" in args.base_url:
            print("\n!!! TARGET IS THE LIVE DEPLOYMENT - experimental data will enter the demo DB !!!")
        send(args.base_url, body)
    else:
        print("\nDry run only - nothing sent. Integration is intentionally NOT built yet.")


if __name__ == "__main__":
    main()
