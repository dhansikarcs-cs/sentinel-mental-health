from pydantic import BaseModel, Field


class SensorDataCreate(BaseModel):
    """Wearable ingestion payload.

    Every physiological field is OPTIONAL. A device must only send what it
    actually measured; Sentinel never fills unmeasured fields with defaults,
    derived values, or invented numbers.
    """

    device_id: str = ""
    bpm: int | None = Field(default=None, ge=30, le=250)
    stress: int | None = Field(default=None, ge=0, le=100)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    spo2: float | None = Field(default=None, ge=50, le=100)
    hrv: int | None = Field(default=None, ge=0, le=300)
    seq: int | None = Field(default=None, ge=0, le=2_147_483_647)
    timestamp: str | None = None


class SensorDataResponse(BaseModel):
    id: int
    device_id: str
    patient_username: str
    bpm: int | None
    stress: int | None
    sleep_hours: float | None
    spo2: float | None
    hrv: int | None
    seq: int | None = None
    logged_at: str

    class Config:
        from_attributes = True


class RingDeviceCreate(BaseModel):
    serial: str = Field(min_length=1, max_length=128)
    vendor: str = ""


class RingDeviceResponse(BaseModel):
    serial: str
    patient_username: str
    vendor: str
    status: str
    last_seen_at: str
    created_at: str
    token: str = ""

    class Config:
        from_attributes = True
