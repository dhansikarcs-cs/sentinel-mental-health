"""Sensor reading container and RingSource base contract."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass
class SensorData:
    """A reading from a physical ring.

    Every physiological field is optional: NULL means the device did not
    measure it. No defaults, derived values, or invented numbers.
    """

    device_id: str = ""
    bpm: int | None = None
    stress: int | None = None
    sleep_hours: float | None = None
    spo2: float | None = None
    hrv: int | None = None
    mood: str = ""
    timestamp: str = ""

    @classmethod
    def from_dict(cls, data: dict, device_id: str = "") -> "SensorData":
        def opt_int(v):
            return int(v) if v is not None else None

        def opt_float(v):
            return float(v) if v is not None else None

        return cls(
            device_id=data.get("device_id") or device_id,
            bpm=opt_int(data.get("bpm")),
            stress=opt_int(data.get("stress")),
            sleep_hours=opt_float(data.get("sleep_hours") or data.get("sleep")),
            spo2=opt_float(data.get("spo2")),
            hrv=opt_int(data.get("hrv")),
            mood=str(data.get("mood") or ""),
            timestamp=str(data.get("timestamp") or datetime.now(UTC).isoformat()),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class RingSource(ABC):
    """Base contract for any ring data provider."""

    name: str = "base"

    def connect(self) -> bool:
        return True

    @abstractmethod
    def read_sensors(self) -> SensorData:
        """Return the latest sensor reading."""
        raise NotImplementedError

    def disconnect(self) -> None:
        return None
