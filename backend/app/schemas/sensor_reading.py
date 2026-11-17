from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    """Only measured fields should be sent. Unmeasured fields stay NULL."""

    heart_rate: int | None = Field(default=None, ge=30, le=250)
    rmssd: float | None = Field(default=None, ge=0, le=500)
    sdnn: float | None = Field(default=None, ge=0, le=500)
    temperature: float | None = Field(default=None, ge=34, le=42)
    device_id: str = ""


class SensorReadingResponse(BaseModel):
    id: int
    patient_username: str
    heart_rate: int | None
    rmssd: float | None
    sdnn: float | None
    temperature: float | None
    device_id: str
    logged_at: str

    class Config:
        from_attributes = True
