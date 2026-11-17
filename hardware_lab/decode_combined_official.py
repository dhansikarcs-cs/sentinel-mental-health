"""Decode combined all-day records using the CONFIRMED vendor layout.

Layout (Yucheng SDK doc lines 3367-3437 + PulseLoop §4.4), 20-byte stride:
  @0  ts:u32 LE (seconds since 2000-01-01, local wall clock)
  @4  steps:u16 LE
  @6  heartRate        @11 hrv            @17 bloodSugar
  @7  systolic         @12 cvrr           @18-19 reserved
  @8  diastolic        @13 tempInt
  @9  spo2             @14 tempFrac
  @10 respiratoryRate  @15 bodyFatInt
                       @16 bodyFatFrac

"Fields that return 0 should be ignored" (vendor doc).
Temperature = float(f"{tempInt}.{tempFrac}"); FILLER when tempInt==0 or tempFrac==15.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

# Combined records captured across the three probe runs (deduped by timestamp).
BLOBS = [
    "50410ebc000000000062002500240300004e1f54be744382000000000060000000000f000000f51c",
    "50410ebc000000000062002500240300004e1f54be744382000000000060000000000f000000f51c296ebe4c000000000059000000000f000000ca20",
]

EPOCH = datetime(2000, 1, 1)


def decode(rec: bytes) -> dict:
    ts = int.from_bytes(rec[0:4], "little")
    try:
        when = (EPOCH + timedelta(seconds=ts)).isoformat()
    except (OverflowError, ValueError):
        when = f"raw=0x{ts:08x}"

    temp_int, temp_frac = rec[13], rec[14]
    temp = None
    if temp_int != 0 and temp_frac != 15:
        temp = float(f"{temp_int}.{temp_frac}")

    def v(i):
        return rec[i] if rec[i] != 0 else None

    return {
        "ts_raw": f"0x{ts:08x}",
        "ts_decoded_local": when,
        "steps": int.from_bytes(rec[4:6], "little") or None,
        "heart_rate": v(6),
        "systolic": v(7),
        "diastolic": v(8),
        "spo2": v(9),
        "respiratory_rate": v(10),
        "hrv_ms": v(11),
        "temperature_c": temp,
        "temperature_raw": f"{temp_int}.{temp_frac}" if temp else None,
        "blood_sugar_raw": v(17),
    }


seen = {}
for blob in BLOBS:
    d = bytes.fromhex(blob)
    for i in range(0, len(d), 20):
        rec = d[i : i + 20]
        if len(rec) < 20:
            continue
        r = decode(rec)
        seen[r["ts_raw"]] = r

print("=== COMBINED ALL-DAY RECORDS (official vendor layout) ===\n")
for r in sorted(seen.values(), key=lambda x: x["ts_raw"]):
    print(json.dumps(r, indent=2))

print("\n=== NON-ZERO SIGNALS FOUND ===")
for key in ("heart_rate", "systolic", "diastolic", "spo2", "respiratory_rate", "hrv_ms", "temperature_c", "steps"):
    vals = [r[key] for r in seen.values() if r[key] is not None]
    print(f"  {key:<18}: {vals}")

Path(OUT / "combined_decoded.json").write_text(
    json.dumps({"layout": "Yucheng SDK doc 3367-3437 + PulseLoop 4.4", "records": list(seen.values())}, indent=2),
    encoding="utf-8",
)
print("\nsaved -> out/combined_decoded.json")
