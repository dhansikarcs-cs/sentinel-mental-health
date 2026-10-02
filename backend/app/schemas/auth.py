import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.dates import is_valid_dob
from app.core.location import is_valid_tz


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    role: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    clinic_code: str = Field(default="", max_length=50)
    role: Literal["patient", "psychologist"] = "patient"
    dob: str = Field(min_length=10, max_length=10)
    occupation: str = Field(min_length=1, max_length=100)
    professional_code: str = Field(default="", max_length=50)
    assigned_psych: str = Field(default="", max_length=50)
    country: str = Field(default="", max_length=100)
    timezone: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=200)
    invite_code: str = Field(default="", max_length=50)
    license_number: str = Field(default="", max_length=60)

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v and ("@" not in v or "." not in v.split("@")[-1]):
            raise ValueError("email must be a valid email address")
        return v

    @field_validator("license_number")
    @classmethod
    def license_stripped(cls, v: str) -> str:
        return v.strip()

    @field_validator("invite_code")
    @classmethod
    def invite_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, v: str) -> str:
        v = v.strip()
        if v and not is_valid_tz(v):
            raise ValueError("timezone must be a valid IANA timezone")
        return v

    @field_validator("name")
    @classmethod
    def name_must_be_real(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("name must contain at least one letter")
        return v

    @field_validator("dob")
    @classmethod
    def dob_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_dob(v):
            raise ValueError("dob must be a valid past date (YYYY-MM-DD)")
        return v

    @field_validator("occupation")
    @classmethod
    def occupation_stripped(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("occupation/specialisation is required")
        return v.strip()


class UnlockRequest(BaseModel):
    passphrase: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ResendVerificationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class InviteCreateRequest(BaseModel):
    clinic_code: str = Field(min_length=1, max_length=50)
    max_uses: int = Field(default=1, ge=1, le=500)
    expires_in_days: int = Field(default=14, ge=1, le=365)


class DoctorCreateClientRequest(BaseModel):
    """Doctor provisioning a client account in-clinic (no self-signup)."""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=4, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    dob: str = Field(min_length=10, max_length=10)
    occupation: str = Field(default="", max_length=100)
    contact_info: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=100)
    timezone: str = Field(default="", max_length=100)

    @field_validator("name")
    @classmethod
    def name_must_be_real(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("name must contain at least one letter")
        return v

    @field_validator("dob")
    @classmethod
    def dob_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_dob(v):
            raise ValueError("dob must be a valid past date (YYYY-MM-DD)")
        return v

    @field_validator("contact_info")
    @classmethod
    def contact_valid(cls, v: str) -> str:
        v = v.strip()
        if v and ("@" not in v or "." not in v.split("@")[-1]):
            raise ValueError("contact_info must be a valid email")
        return v

    @field_validator("occupation")
    @classmethod
    def occupation_stripped(cls, v: str) -> str:
        return v.strip()


class PreferencesUpdate(BaseModel):
    country: str = Field(max_length=100)
    timezone: str = Field(max_length=100)

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_tz(v):
            raise ValueError("timezone must be a valid IANA timezone")
        return v

    @field_validator("country")
    @classmethod
    def country_stripped(cls, v: str) -> str:
        return v.strip()
