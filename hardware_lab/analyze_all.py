"""Recompute an HONEST per-phase report from the verbatim frame log."""
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "all_signals_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

DATA = {"0600", "0601", "0602", "0603", "0615"}
REJECT = "fc"
EMPTY = "0000"

by_phase = defaultdict(lambda: {"recv": [], "sent": 0})
for r in lines:
    p = r.get("phase", "?")
    if r.get("direction") == "recv":
        by_phase[p]["recv"].append(r)
    elif r.get("direction") == "send":
        by_phase[p]["sent"] += 1

print("=== PER-PHASE TRUTH (recv frames that arrived DURING that phase) ===\n")
for phase, d in by_phase.items():
    recvs = d["recv"]
    opcodes = [r.get("opcode_name") or r.get("opcode") for r in recvs]
    data_frames = [r for r in recvs if r.get("opcode") in DATA]
    print(f"{phase}: sent={d['sent']} recv={len(recvs)}")
    print(f"   opcodes: {sorted(set(o for o in opcodes if o))}")
    if data_frames:
        print(f"   >>> LIVE DATA FRAMES: {[r['raw_hex'] for r in data_frames]}")
    for r in recvs:
        pl = r.get("payload_hex", "")
        tag = ""
        if pl == REJECT:
            tag = "  <-- REJECTED / NOT SUPPORTED (0xFC)"
        elif pl == EMPTY:
            tag = "  <-- NO RECORDS (empty)"
        elif pl.startswith("02") and r.get("opcode") == "0506":
            tag = "  <-- HISTORY HEADER (records present)"
        elif r.get("opcode") == "0515":
            tag = "  <-- HISTORY DATA RECORD"
        elif r.get("opcode") == "0580":
            tag = "  <-- TRANSFER TERMINAL"
        print(f"      {r['opcode']} payload={pl}{tag}")
    print()

print("=== SUMMARY ===")
all_recv = [r for r in lines if r.get("direction") == "recv"]
live = [r for r in all_recv if r.get("opcode") in DATA]
rejects = [r for r in all_recv if r.get("payload_hex") == REJECT]
empty = [r for r in all_recv if r.get("payload_hex") == EMPTY]
history = [r for r in all_recv if r.get("opcode") in {"0506", "0515", "0580"}]
print("total recv frames:", len(all_recv))
print("live measurement frames (06 xx):", len(live))
print("history frames with real records:", len(history), [r["raw_hex"] for r in history])
print("queries REJECTED with 0xFC:", len(rejects))
print("queries answered EMPTY 0000:", len(empty))
print("CRC-invalid frames:", sum(1 for r in all_recv if not r.get("crc_ok")))
