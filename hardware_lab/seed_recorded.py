"""Seed the hardware-less pilot with REAL recorded ring data.

Reads out/genuine_measurements.json (values actually captured from the
physical Viaking R30 PRO) and pushes them through Sentinel's own API so the
UI shows real data without needing the ring connected.

Only measured fields are sent. Nothing is invented: stress/sleep stay null
because the ring never produced them. Temperature goes in via the
sensor-readings endpoint because RingSensorLog has no temperature column.

Usage: python seed_recorded.py [--base-url http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--username", default="alaya")
    ap.add_argument("--password", default="4321")
    args = ap.parse_args()

    src = json.loads((OUT / "genuine_measurements.json").read_text(encoding="utf-8"))
    temp = json.loads((OUT / "temperature_hrv.json").read_text(encoding="utf-8"))

    s = requests.Session()
    login = s.post(
        f"{args.base_url}/api/auth/login",
        json={"username": args.username, "password": args.password},
        timeout=30,
    )
    print("login:", login.status_code)
    login.raise_for_status()
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    pair = s.post(
        f"{args.base_url}/api/ring/pair",
        json={"serial": "VIAKING-R30PRO-F085", "vendor": "viaking_r30pro"},
        headers=h,
        timeout=30,
    )
    print("pair:", pair.status_code)
    if pair.status_code == 409:  # already paired - re-pair by unpairing first
        s.post(
            f"{args.base_url}/api/ring/unpair?serial=VIAKING-R30PRO-F085",
            headers=h,
            timeout=30,
        )
        pair = s.post(
            f"{args.base_url}/api/ring/pair",
            json={"serial": "VIAKING-R30PRO-F085", "vendor": "viaking_r30pro"},
            headers=h,
            timeout=30,
        )
        print("re-pair:", pair.status_code)
    pair.raise_for_status()
    dh = {"X-Device-Serial": pair.json()["serial"], "X-Device-Token": pair.json()["token"]}

    hr = src["genuine_signals"]["heart_rate_bpm"]["live_readings"]  # [89, 85, 83]
    spo2 = src["genuine_signals"]["spo2_percent"]["live_result"]  # 96
    hrv = temp["hrv_ms_from_combined_record"]  # 37
    body_temp = temp["temperature_live"]["body_temp_c"]["mean"]  # 35.86

    # Three real HR samples, each with the real SpO2 and real HRV values.
    for i, bpm in enumerate(hr, start=1):
        payload = {
            "device_id": "viaking_r30pro_F085",
            "seq": i,
            "bpm": bpm,
            "spo2": float(spo2),
            "hrv": int(hrv),
            "timestamp": f"2026-11-15T10:5{i}:00Z",
        }
        r = s.post(f"{args.base_url}/api/ring/data", json=payload, headers=dh, timeout=30)
        print(f"  push bpm={bpm} spo2={spo2} hrv={hrv}: HTTP {r.status_code}")

    # Body temperature (real recorded mean) into the sensor-readings table.
    r = s.post(
        f"{args.base_url}/api/sensor-readings",
        json={"device_id": "viaking_r30pro_F085", "heart_rate": hr[-1], "temperature": body_temp},
        headers=h,
        timeout=30,
    )
    print(f"  push temperature={body_temp} C: HTTP {r.status_code}")

    wellness = s.get(f"{args.base_url}/api/patients/me/wellness", headers=h, timeout=30)
    print("\n=== GET /api/patients/me/wellness ===")
    print(wellness.status_code, json.dumps(wellness.json(), indent=2))

    (OUT / "seed_recorded_result.json").write_text(
        json.dumps(
            {"wellness": wellness.json(), "sourced_from": "out/genuine_measurements.json"},
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
