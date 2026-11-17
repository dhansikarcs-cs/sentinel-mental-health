"""Verify the ring SDK layer (app.services.ring) works without a server.

Run: python scripts/test_ring_api.py

Sentinel stores ONLY genuinely measured wearable signals. There is no
SimulatedRing and no fabricated defaults: an unmeasured field stays None.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.ring import (
    BLEGATTRingSource,
    SensorData,
    VendorAPIRingSource,
    parse_hrm,
    uint8,
    uint16_le,
)


def test_sensor_data_no_fabrication():
    sd = SensorData.from_dict({"bpm": 85, "stress": 40, "mood": "anxious"})
    assert sd.bpm == 85, f"Expected bpm=85 got {sd.bpm}"
    assert sd.stress == 40, f"Expected stress=40 got {sd.stress}"
    assert sd.mood == "anxious", f"Expected mood=anxious got {sd.mood}"
    # Nothing invented: unmeasured signals stay NULL, never defaulted.
    assert sd.hrv is None, "hrv must stay None when not measured"
    assert sd.spo2 is None, "spo2 must stay None when not measured"
    assert sd.sleep_hours is None, "sleep_hours must stay None when not measured"
    print("OK - SensorData.from_dict (no fabricated defaults)")


def test_vendor_api_source_with_fetch_fn():
    def fake_fetch():
        return {"bpm": 91, "stress": 55, "spo2": 96.0, "hrv": 40}

    src = VendorAPIRingSource("ring-oura-1", fetch_fn=fake_fetch)
    src.connect()
    sd = src.read_sensors()
    assert sd.bpm == 91, f"Expected bpm=91 got {sd.bpm}"
    assert sd.hrv == 40, f"Expected hrv=40 got {sd.hrv}"
    print("OK - VendorAPIRingSource fetch_fn")


def test_vendor_api_requires_credentials():
    src = VendorAPIRingSource("ring-oura-2")
    try:
        src.connect()
        raise AssertionError("Expected RuntimeError for missing credentials")
    except RuntimeError:
        print("OK - VendorAPIRingSource rejects missing credentials")


def test_ble_hrm_parser():
    # Standard HRM: flags=0x00 -> 8-bit bpm in byte 1
    assert parse_hrm(bytes([0x00, 96])) == {"bpm": 96}
    # flags=0x01 -> 16-bit bpm (little-endian) in bytes 1-2
    assert parse_hrm(bytes([0x01, 0x64, 0x00])) == {"bpm": 100}
    # No data / sensor contact NOT detected -> no invented reading
    assert parse_hrm(b"") == {}
    assert parse_hrm(bytes([0x04, 0x00])) == {}
    print("OK - BLEGATT parse_hrm (8-bit, 16-bit, empty, no contact)")


def test_ble_uuid_parsers():
    assert uint8(bytes([42])) == 42
    assert uint16_le(bytes([0x34, 0x12])) == 0x1234
    print("OK - BLEGATT uint8 / uint16_le")


def test_ble_source_requires_address():
    try:
        BLEGATTRingSource()
        raise AssertionError("Expected ValueError without address/device_id")
    except ValueError:
        print("OK - BLEGATTRingSource requires a BLE address or device_id")


if __name__ == "__main__":
    test_sensor_data_no_fabrication()
    test_vendor_api_source_with_fetch_fn()
    test_vendor_api_requires_credentials()
    test_ble_hrm_parser()
    test_ble_uuid_parsers()
    test_ble_source_requires_address()
    print("\nAll ring SDK tests passed!")
