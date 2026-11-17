"""Decode the ASCII debug stream from Nordic UART TX (6e400003).

This channel was silently carrying the ring's raw PPG values and its
SpO2/HR algorithm output. Frames are NOT YCBT - they are plain ASCII text,
so parse_frame() mislabels them; we decode them as text here.
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "probe_deep_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

nus = [r for r in lines if r.get("channel") == "6e4000" or r.get("channel", "").startswith("6e4000")]
print("NUS frames:", len(nus), "\n")

texts = []
for r in nus:
    raw = bytes.fromhex(r["raw_hex"])
    try:
        s = raw.decode("ascii").rstrip("\n")
    except UnicodeDecodeError:
        s = repr(raw)
    texts.append(s)

for s in texts:
    print("  ", s)

print("\n=== EXTRACTED VALUES ===")
ppg = [t for t in texts if t.startswith("G:")]
spo2 = re.findall(r"SpO2:\s*(\d+)%", " ".join(texts))
rv = re.findall(r"SpO2:\s*0\b", " ".join(texts))
print("raw PPG samples (G/R/IR ADC):", len(ppg))
print("SpO2 percentages seen:", spo2)
print("SpO2=0 (no valid reading) count:", len(rv))
print("lifestyle/debug messages:", [t for t in texts if not t.startswith(("G:", "No:")) and "SpO2" not in t][:12])
