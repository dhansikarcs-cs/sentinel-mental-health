"""Decode the REAL 02 00 device-info and 02 01 capability-bitmap replies
that came back once we sent the vendor's 2-byte Get tags (not empty payload).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

# From probe_ecg_frames.jsonl replies (CRC-valid).
import json as _json

lines = [
    _json.loads(x)
    for x in (OUT / "probe_ecg_frames.jsonl").read_text(encoding="utf-8").splitlines()
    if x.strip()
]


def reply_payload(opcode: str) -> bytes:
    hits = [r for r in lines if r.get("opcode") == opcode and r.get("crc_ok") and r.get("payload_hex")]
    return bytes.fromhex(hits[-1]["payload_hex"]) if hits else b""


INFO = reply_payload("0200")
CAP = reply_payload("0201")
NAME = reply_payload("0203")

print("=== 02 00 device info ===")
print("  raw:", INFO.hex(), "len:", len(INFO))
print("  bytes:", list(INFO))
print("  battery byte @5 =", INFO[5], "%")  # 0x64 = 100, matches 0x2A19
print("  firmware-ish bytes @0-3:", INFO[:4].hex())

print("\n=== 02 03 device name ===")
print("  ", NAME.decode("ascii", errors="replace").rstrip("\x00"))

print("\n=== 02 01 capability bitmap ===")
print("  raw len:", len(CAP))
print("  first 32 bytes:", list(CAP[:32]))
print("  non-zero offsets:", [(i, b) for i, b in enumerate(CAP) if b])
bits = set()
for i, b in enumerate(CAP):
    for bit in range(8):
        if b & (1 << bit):
            bits.add(i * 8 + bit)
print("  set bits (first 60):", sorted(bits)[:60])

# Vendor-documented capability bit names (PulseLoop / Tk5SupportFunction).
BIT_NAMES = {
    0: "ISHASBLOOD", 1: "ISHASHRV", 2: "ISHASBLOODOXYGEN",
    64: "ISHASSTEP", 120: "ISHASTEMP", 128: "ISHASFINDDEVICE",
}
print("\n  named bits present:", {n: (b in bits) for n, b in BIT_NAMES.items()})

result = {
    "device_name": NAME.decode("ascii", errors="replace").rstrip("\x00"),
    "battery_percent": INFO[5],
    "device_info_hex": INFO.hex(),
    "capability_bitmap_hex": CAP.hex(),
    "capability_bitmap_len": len(CAP),
    "set_bit_count": len(bits),
    "note": "Obtained only after sending vendor Get tags; empty-payload Gets returned 0xFE Data error",
}
(OUT / "device_info_decoded.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("\nsaved -> out/device_info_decoded.json")
