import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
lines = [json.loads(x) for x in (OUT / "probe_ecg_frames.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

print("=== replies to ECG-related commands ===")
want = {"0200", "0201", "0203", "0228", "021b", "0227", "030a", "0314", "0309", "030b", "0302", "032f", "0700", "040b"}
for r in lines:
    if r.get("direction") == "send":
        print(f"  SEND {r.get('label')}: {r.get('raw_hex')}")
    elif r.get("opcode") in want and r.get("crc_ok"):
        print(f"    REPLY {r.get('opcode')} payload={r.get('payload_hex')} raw={r.get('raw_hex')}")

print("\n=== 0700 / 040b / 06f0 / 06f1 seen? ===")
for op in ("0700", "040b", "06f0", "06f1", "0603"):
    hits = [r for r in lines if r.get("opcode") == op]
    print(f"  {op}: {len(hits)}")

rep = OUT / "probe_ecg_report.json"
print("\nreport exists:", rep.exists())
if rep.exists():
    j = json.loads(rep.read_text(encoding="utf-8"))
    print("verdict:", j.get("verdict"), "| waveform frames:", j.get("ecg_waveform_frames"))
    print("nus lines:", j.get("nus_console_lines"))
    for s in j.get("nus_lines", [])[:15]:
        print("   ", s)
