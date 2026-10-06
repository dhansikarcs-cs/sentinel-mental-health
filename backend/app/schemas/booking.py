from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _valid_booking_date(value: str) -> str:
    if not value or len(value) != 10:
        raise ValueError("date must be YYYY-MM-DD")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError("date must be a real calendar date (YYYY-MM-DD)") from None
    if parsed.year < 1970 or parsed.year > 2100:
        raise ValueError("date out of supported range")
    return value


def _valid_booking_time(value: str) -> str:
    if not value:
        raise ValueError("time is required")
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        raise ValueError("time must be HH:MM (24-hour)") from None
    return value


class BookingCreate(BaseModel):
    psychologist_username: str = Field(min_length=1, max_length=50)
    patient_username: str = Field(default="", max_length=50)
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=1, max_length=10)
    session_type: str = Field(default="", max_length=50)
    members: str = Field(default="", max_length=200)
    contact: str = Field(default="", max_length=200)
    explanation: str = Field(default="", max_length=2000)

    _date_valid = field_validator("date")(_valid_booking_date)
    _time_valid = field_validator("time")(_valid_booking_time)


class BookingResponse(BaseModel):
    id: int
    patient_username: str
    psychologist_username: str
    date: str
    time: str
    session_type: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class BookingUpdate(BaseModel):
    status: Literal["Pending", "Approved", "Rejected", "Cancelled", "Completed"]


class BookingReschedule(BaseModel):
    date: str
    time: str

    _date_valid = field_validator("date")(_valid_booking_date)
    _time_valid = field_validator("time")(_valid_booking_time)


class AvailabilityCreate(BaseModel):
    date: str
    start_time: str = "09:00"
    end_time: str = "17:00"
