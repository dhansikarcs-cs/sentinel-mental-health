"""Decode the LATEST real YCBT history records (after live measurements)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "probe_history_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

# Group by query, keep frames from the LAST occurrence of each query phase.
buckets = {}
for r in lines:
    if r.get("crc_ok"):
        buckets.setdefault(r.get("query", "?"), []).append(r)


def frames_for(q, prefix):
    fs = [bytes.fromhex(r["raw_hex"]) for r in buckets.get(q, []) if r["raw_hex"].startswith(prefix)]
    return fs[-1] if fs else b""


print("=== HR HISTORY (05 06 / 0515) - latest ===")
h = frames_for("heart_rate_history", "050610")
d = frames_for("heart_rate_history", "05151e") or frames_for("heart_rate_history", "051518")
hdr, data = h[4:-2], d[4:-2]
print("header:", hdr.hex(), "records =", int.from_bytes(hdr[:2], "little"), "bytes =", int.from_bytes(hdr[6:10], "little"))
print("data:", data.hex(), "len =", len(data))
for i in range(0, len(data), 6):
    r = data[i : i + 6]
    print(f"   rec{i//6}: ts=0x{int.from_bytes(r[:4],'little'):08x} HR={r[5]} bpm")

print("\n=== BP HISTORY (05 08 / 0517) - latest ===")
h = frames_for("blood_pressure_history", "050810")
d = frames_for("blood_pressure_history", "051716")
hdr, data = h[4:-2], d[4:-2]
print("header:", hdr.hex(), "records =", int.from_bytes(hdr[:2], "little"), "bytes =", int.from_bytes(hdr[6:10], "little"))
print("data:", data.hex(), "len =", len(data))
for i in range(0, len(data), 8):
    r = data[i : i + 8]
    print(f"   rec{i//8}: {r.hex()}  bytes={list(r)}  (candidate sys/dia: {r[5]}/{r[6]})")

print("\n=== COMBINED ALL-DAY (05 09 / 0518) - latest ===")
h = frames_for("combined_all_day_record", "050910")
d = frames_for("combined_all_day_record", "05182e")
hdr, data = h[4:-2], d[4:-2]
print("header:", hdr.hex(), "records =", int.from_bytes(hdr[:2], "little"), "bytes =", int.from_bytes(hdr[6:10], "little"))
print("data:", data.hex(), "len =", len(data))
for i in range(0, len(data), 20):
    r = data[i : i + 20]
    print(f"   rec{i//20}: {r.hex()}")
    print(f"      byte[9]={r[9]}  byte[11]={r[11]}  byte[13]={r[13]}  (SpO2 candidate at byte 9)")
