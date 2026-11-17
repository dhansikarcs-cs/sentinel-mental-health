"""Decode Nordic UART ASCII + list real YCBT data frames for a probe_deep mode."""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
mode = sys.argv[1] if len(sys.argv) > 1 else "spo2"
p = OUT / f"probe_deep_{mode}_frames.jsonl"
lines = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

print(f"=== {mode}: {len(lines)} frames ===\n")
print("--- YCBT frames with real opcodes (non-ASCII) ---")
for r in lines:
    if r.get("channel", "").startswith("be94") and r.get("crc_ok"):
        print(f"  {r['channel'][:8]} {r['raw_hex']:<44} op={r.get('opcode')} payload={r.get('payload_hex')}")

print("\n--- Nordic UART ASCII debug (decoded) ---")
for r in lines:
    if r.get("channel", "").startswith("6e4000"):
        raw = bytes.fromhex(r["raw_hex"])
        try:
            print("  ", raw.decode("ascii").rstrip("\n"))
        except UnicodeDecodeError:
            print("  ", repr(raw))
