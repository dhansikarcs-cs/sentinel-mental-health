"""Offline: did the ring EVER emit stress / fatigue / sleepiness / sleep data?

Scans every captured frame log. Does not touch BLE.
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
KEY = re.compile(r"(stress|fatigue|press|sleep|drows|tired|nap|body|relax| parasym|sympath)", re.I)

logs = sorted(OUT.glob("*frames.jsonl")) + sorted(OUT.glob("notifications.jsonl"))
print("frame logs:", [p.name for p in logs], "\n")

nus_hits = []
opcodes = {}
for p in logs:
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        op = r.get("opcode")
        if op:
            opcodes[op] = opcodes.get(op, 0) + 1
        ch = r.get("channel", "")
        if ch.startswith("6e4000") or ch.startswith("6e40"):
            try:
                s = bytes.fromhex(r["raw_hex"]).decode("ascii", errors="replace").rstrip()
                if KEY.search(s):
                    nus_hits.append((p.name, s))
            except (ValueError, KeyError):
                pass

print("=== debug-console lines mentioning stress/fatigue/sleep ===")
if nus_hits:
    for f, s in nus_hits[:40]:
        print(f"  [{f}] {s}")
else:
    print("  NONE - the ring never printed any stress / fatigue / sleep value")

print("\n=== relevant YCBT history opcodes seen across all logs ===")
targets = {"0504", "0505", "0533", "0534", "0513", "0514", "0509", "0518", "0605", "06f0", "06f1"}
for op in sorted(targets):
    print(f"  {op}: {opcodes.get(op, 0)} frames")

print("\n=== stress/fatigue/sleep status (vendor doc) ===")
print("  stress/fatigue  -> 05 33 / 05 34 body-data record (28 B): @8-9 stress, @10-11 fatigue")
print("  sleep stages    -> 05 04 history (needs overnight wear + night rollover)")
print("  combined 05 09  -> does NOT contain stress (vendor doc 3367-3437)")
