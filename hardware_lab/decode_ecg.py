"""Decode the captured 0605 ECG waveform frames into int16 samples.

Frame: [06][05][len:u16 LE=180][payload:174 B = 87 x int16 LE][crc16:2 LE]
Vendor constant: Real_UploadECG = 0x0605.
"""
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "probe_ecg_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
frames = [r for r in lines if r.get("opcode") == "0605" and r.get("crc_ok") and r.get("payload_hex")]

samples = []
for r in frames:
    p = bytes.fromhex(r["payload_hex"])
    for i in range(0, len(p) - 1, 2):
        v = int.from_bytes(p[i : i + 2], "little", signed=True)
        samples.append((r["ts_utc"], v))

vals = [v for _, v in samples]
n = len(vals)
mean = sum(vals) / n if n else 0
std = math.sqrt(sum((v - mean) ** 2 for v in vals) / n) if n else 0

ts = [t for t, _ in samples if t]
first, last = (min(ts), max(ts)) if ts else ("", "")
print("=== ECG WAVEFORM DECODE ===")
print(f"  frames            : {len(frames)}")
print(f"  samples (int16 LE): {n}")
print(f"  min / max         : {min(vals) if vals else 0} / {max(vals) if vals else 0}")
print(f"  mean / std        : {mean:.1f} / {std:.1f}")
print(f"  window            : {first} -> {last}")
print(f"  bytes captured    : {len(frames) * 180}")
print(f"  distinct values   : {len(set(vals))}  (a flat/zero stream would be 1)")

# Save raw samples as CSV for plotting / later analysis.
csv = OUT / "ecg_waveform.csv"
with csv.open("w", encoding="utf-8") as f:
    f.write("ts_utc,sample_index,int16_value\n")
    for i, (t, v) in enumerate(samples):
        f.write(f"{t},{i},{v}\n")

summary = {
    "signal": "ECG waveform (Real_UploadECG 0x0605)",
    "frames": len(frames),
    "samples": n,
    "sample_min": min(vals) if vals else None,
    "sample_max": max(vals) if vals else None,
    "sample_mean": round(mean, 2),
    "sample_std": round(std, 2),
    "window_start_utc": first,
    "window_end_utc": last,
    "bytes_raw": len(frames) * 180,
    "crc_all_valid": True,
    "source": "hardware_lab/out/probe_ecg_frames.jsonl",
    "validation": "Raw ADC waveform - NOT a clinical ECG interpretation",
}
(OUT / "ecg_waveform_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("\nsaved -> out/ecg_waveform.csv")
print("saved -> out/ecg_waveform_summary.json")
