"""Shared helpers for the Sentinel R30 PRO BLE lab.

EXPERIMENTAL / NON-PRODUCTION. This folder is deliberately outside ``backend/``
so it does not enter Sentinel's CI, deploy, or clinical processing pipeline.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "out"

# Human-readable names for Bluetooth SIG adopted UUIDs + descriptors.
UUID_NAMES: dict[str, str] = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access (0x1800)",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute (0x1801)",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information (0x180A)",
    "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate Service (0x180D)",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service (0x180F)",
    "00002a00-0000-1000-8000-00805f9b34fb": "Device Name (0x2A00)",
    "00002a01-0000-1000-8000-00805f9b34fb": "Appearance (0x2A01)",
    "00002a04-0000-1000-8000-00805f9b34fb": "Peripheral Preferred Connection Parameters (0x2A04)",
    "00002a05-0000-1000-8000-00805f9b34fb": "Service Changed (0x2A05)",
    "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level (0x2A19)",
    "00002a24-0000-1000-8000-00805f9b34fb": "Model Number (0x2A24)",
    "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number (0x2A25)",
    "00002a26-0000-1000-8000-00805f9b34fb": "Hardware Revision (0x2A26)",
    "00002a27-0000-1000-8000-00805f9b34fb": "Firmware Revision (0x2A27)",
    "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision (0x2A28)",
    "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name (0x2A29)",
    "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement (0x2A37)",
    "00002a38-0000-1000-8000-00805f9b34fb": "Body Sensor Location (0x2A38) [value 0x03 = Finger]",
    "00002a39-0000-1000-8000-00805f9b34fb": "Heart Rate Control Point (0x2A39)",
    "00002aa6-0000-1000-8000-00805f9b34fb": "Central Address Resolution (0x2AA6)",
    "00002900-0000-1000-8000-00805f9b34fb": "Characteristic Extended Properties (0x2900)",
    "00002901-0000-1000-8000-00805f9b34fb": "Characteristic User Description (0x2901)",
    "00002902-0000-1000-8000-00805f9b34fb": "Client Characteristic Configuration (0x2902)",
    "00002904-0000-1000-8000-00805f9b34fb": "Characteristic Presentation Format (0x2904)",
    # Tencent / WeChat "BLE Lite" pedometer protocol (0xFEE7 is SIG-assigned to Tencent)
    "0000fee7-0000-1000-8000-00805f9b34fb": "WeChat BLE Lite / WeRun service (0xFEE7)",
    "0000fec9-0000-1000-8000-00805f9b34fb": "WeChat: 6-byte MAC address (0xFEC9)",
    "0000fea1-0000-1000-8000-00805f9b34fb": "WeChat: current pedometer measurement (0xFEA1)",
    "0000fea2-0000-1000-8000-00805f9b34fb": "WeChat: step target (0xFEA2)",
    # Nordic Secure DFU / buttonless DFU - DO NOT WRITE (reboots into bootloader)
    "0000fe59-0000-1000-8000-00805f9b34fb": "Nordic Secure DFU service (0xFE59) - DO NOT WRITE",
    "8ec90003-f315-4f60-9fb8-838830daea50": "Nordic buttonless DFU control point - DO NOT WRITE",
    # Yucheng YCBT health protocol - the actual measurement path
    "be940000-7333-be46-b7ae-689e71722bd5": "Yucheng YCBT health service",
    "be940001-7333-be46-b7ae-689e71722bd5": "YCBT command channel (write + indicate)",
    "be940002-7333-be46-b7ae-689e71722bd5": "YCBT write channel",
    "be940003-7333-be46-b7ae-689e71722bd5": "YCBT data / response stream (indicate)",
    # Nordic UART Service
    "6e400001-b5a3-f393-e0a9-e50e24dcca9e": "Nordic UART Service (NUS)",
    "6e400002-b5a3-f393-e0a9-e50e24dcca9e": "Nordic UART RX (write)",
    "6e400003-b5a3-f393-e0a9-e50e24dcca9e": "Nordic UART TX (notify)",
}

HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

DEFAULT_TARGET_NAME_HINTS = ("R30 PRO", "R30PRO", "VIAKING", "HEALTHWEAR")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_out() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR


def write_json(name: str, payload: Any) -> Path:
    path = ensure_out() / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_jsonl(name: str, record: dict[str, Any]) -> None:
    path = ensure_out() / name
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def uuid_label(uuid: str) -> str:
    return UUID_NAMES.get(uuid.lower(), "")


def is_vendor_uuid(uuid: str) -> bool:
    """True for 128-bit UUIDs that are not Bluetooth SIG adopted ones."""
    u = uuid.lower()
    return not u.endswith("-0000-1000-8000-00805f9b34fb")


def norm_addr(addr: str) -> str:
    return addr.upper().replace(":", "").replace("-", "")


def looks_like_target(name: str | None, address: str, service_uuids: list[str]) -> bool:
    n = (name or "").upper()
    if any(h in n for h in DEFAULT_TARGET_NAME_HINTS):
        return True
    # 0x180D + 0xFEE7 is the observed advertisement signature.
    lowered = {u.lower() for u in service_uuids}
    return (
        "0000180d-0000-1000-8000-00805f9b34fb" in lowered
        and "0000fee7-0000-1000-8000-00805f9b34fb" in lowered
    )


def parse_hr_measurement(data: bytes) -> dict[str, Any]:
    """Decode a standard 0x2A37 Heart Rate Measurement packet.

    Flags (Bluetooth SIG): bit0 = uint16 bpm, bit2 = contact feature supported,
    bit1 = contact detected (only meaningful when bit2 set), bit3 = energy
    expended present, bit4 = RR intervals present.
    """
    if not data:
        return {"error": "empty packet"}
    flags = data[0]
    wide = bool(flags & 0x01)
    contact_supported = bool(flags & 0x04)
    contact_detected = bool(flags & 0x02) if contact_supported else None
    bpm: int | None = None
    offset = 1
    if wide and len(data) >= 3:
        bpm = int.from_bytes(data[1:3], "little")
        offset = 3
    elif not wide and len(data) >= 2:
        bpm = data[1]
        offset = 2
    energy = None
    if flags & 0x08 and len(data) >= offset + 2:
        energy = int.from_bytes(data[offset : offset + 2], "little")
        offset += 2
    rr: list[float] = []
    if flags & 0x10:
        while len(data) >= offset + 2:
            rr.append(round(int.from_bytes(data[offset : offset + 2], "little") / 1024 * 1000, 1))
            offset += 2
    return {
        "flags": f"0x{flags:02x}",
        "bpm": bpm,
        "bpm_format": "uint16" if wide else "uint8",
        "sensor_contact_supported": contact_supported,
        "sensor_contact_detected": contact_detected,
        "energy_expended": energy,
        "rr_intervals_ms": rr,
        "clinically_usable": bool(bpm and 30 <= bpm <= 250 and contact_detected is not False),
    }


def parse_battery_level(data: bytes) -> dict[str, Any]:
    return {"battery_percent": data[0] if data else None}


async def stream_scan(
    seconds: float,
    address: str | None = None,
    on_device=None,
) -> dict[str, dict[str, Any]]:
    """Active streaming scan. Empirical note: on this Windows/bleak 3.1 setup the
    one-shot ``BleakScanner.discover()`` returned 0 devices while the callback
    scanner found the ring reliably. Always use explicit start/stop.
    """
    from bleak import BleakScanner

    seen: dict[str, dict[str, Any]] = {}

    def cb(device, adv):
        rec = {
            "address": device.address,
            "name": device.name or adv.local_name or "",
            "rssi": adv.rssi,
            "service_uuids": [str(u) for u in adv.service_uuids],
            "manufacturer_data": {str(k): v.hex() for k, v in adv.manufacturer_data.items()},
            "service_data": {str(k): v.hex() for k, v in adv.service_data.items()},
            "tx_power": adv.tx_power,
            "first_seen_utc": now_iso(),
            "target_match": looks_like_target(device.name or adv.local_name, device.address, list(adv.service_uuids)),
        }
        key = norm_addr(device.address)
        prev = seen.get(key)
        if prev is None or rec["rssi"] > (prev.get("rssi") or -999):
            seen[key] = rec
        if on_device:
            on_device(device, adv)

    scanner = BleakScanner(detection_callback=cb, scanning_mode="active")
    await scanner.start()
    try:
        if address:
            wanted = norm_addr(address)
            for _ in range(int(seconds * 2)):
                if wanted in seen:
                    break
                await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(seconds)
    finally:
        await scanner.stop()
    return seen


def cached_address() -> str | None:
    """Address remembered by a previous successful scan (ads are intermittent)."""
    p = OUT_DIR / "device.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("address")
        except (OSError, ValueError):
            return None
    return None


def device_meta(dev: Any) -> tuple[str, str]:
    """(name, address) for either a BLEDevice or a plain address string."""
    if isinstance(dev, str):
        return ("R30 PRO (direct connect)", dev)
    return (dev.name or "R30 PRO", dev.address)


async def find_device(seconds: float = 10.0, address: str | None = None, retries: int = 3):
    """Re-scan and return a live BLEDevice (avoids WinRT address quirks).

    The ring advertises roughly every 4s with quiet gaps, so a single short scan
    can miss it. Retry, then fall back to connecting by a known address directly
    (WinRT can resolve a cached address without a fresh advertisement).
    """
    wanted = address or cached_address()
    for _ in range(retries):
        found: dict[str, Any] = {}

        def on_device(device, adv):
            if wanted and norm_addr(device.address) != norm_addr(wanted):
                return
            if wanted or looks_like_target(device.name or adv.local_name, device.address, list(adv.service_uuids)):
                if "dev" not in found:
                    found["dev"] = device

        await stream_scan(seconds, address=wanted, on_device=on_device)
        if "dev" in found:
            dev = found["dev"]
            write_json(
                "device.json",
                {
                    "address": dev.address,
                    "name": dev.name,
                    "last_seen_utc": now_iso(),
                    "note": "cached by hardware_lab; ads are intermittent",
                },
            )
            return dev
    return wanted  # str: BleakClient can connect by address on Windows


def iter_services(client):
    """Yield GATT services across bleak versions (3.x exposes a dict)."""
    coll = client.services
    raw = getattr(coll, "services", None)
    if isinstance(raw, dict):
        return list(raw.values())
    return list(coll)


def char_dict(char) -> dict[str, Any]:
    return {
        "uuid": str(char.uuid),
        "name": uuid_label(str(char.uuid)),
        "handle": char.handle,
        "properties": list(char.properties),
        "vendor_specific": is_vendor_uuid(str(char.uuid)),
        "descriptors": [
            {
                "uuid": str(d.uuid),
                "name": uuid_label(str(d.uuid)),
                "handle": d.handle,
            }
            for d in char.descriptors
        ],
    }
