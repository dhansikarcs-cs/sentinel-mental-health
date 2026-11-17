"""Extract real temperature + HRV from the debug console and combined records."""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "probe_discover_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

texts = []
for r in lines:
    if r.get("channel", "").startswith("6e4000"):
        try:
            texts.append(bytes.fromhex(r["raw_hex"]).decode("ascii").rstrip())
        except UnicodeDecodeError:
            pass

# Vendor debug format: "Env: 30.66, Skin: 30.66, BT: 35.88"  (BT = body temp)
pat = re.compile(r"Env:\s*([\d.]+),\s*Skin:\s*([\d.]+),\s*BT:\s*([\d.]+)")
rows = [pat.search(t) for t in texts]
rows = [m.groups() for m in rows if m]

print(f"=== TEMPERATURE DEBUG FRAMES: {len(rows)} ===")
for env, skin, bt in rows[:5]:
    print(f"  Env={env} C  Skin={skin} C  BT(body)={bt} C")
print("  ...")
bts = [float(bt) for _, _, bt in rows]
envs = [float(e) for e, _, _ in rows]
print(f"\nBody temp (BT): min={min(bts):.2f} max={max(bts):.2f} mean={sum(bts)/len(bts):.2f} C")
print(f"Ambient (Env): min={min(envs):.2f} max={max(envs):.2f} C")

other = [t for t in texts if not t.startswith(("G:", "No:", "Env:"))]
print(f"\n=== OTHER CONSOLE MESSAGES ({len(other)}) ===")
for t in other[:20]:
    print("  ", t)

combined = json.loads((OUT / "combined_decoded.json").read_text(encoding="utf-8"))
print("\n=== HRV / TEMP FROM COMBINED RECORDS ===")
for r in combined["records"]:
    print(f"  spo2={r['spo2']} hrv_ms={r['hrv_ms']} temp_c={r['temperature_c']} bp={r['systolic']}/{r['diastolic']}")

result = {
    "temperature_live": {
        "body_temp_c": {"min": min(bts), "max": max(bts), "mean": round(sum(bts) / len(bts), 2)},
        "ambient_c": {"min": min(envs), "max": max(envs)},
        "sample_count": len(rows),
        "source": "Nordic UART ASCII debug, after enabling 01 20 temperature monitor",
    },
    "temperature_stored_c": 36.3,
    "hrv_ms_from_combined_record": 37,
    "spo2_from_combined_records": [98, 96, 89],
    "note": "BT = body temperature as printed by the ring's own algorithm; not clinically validated",
}
(OUT / "temperature_hrv.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("\nsaved -> out/temperature_hrv.json")
