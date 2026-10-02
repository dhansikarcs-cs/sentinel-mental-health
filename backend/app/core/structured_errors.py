"""Structured errors: one envelope for every failure.

Every error response in the API looks like:
    {"code": "BOOKING_SLOT_CONFLICT", "message": "...", "trace_id": "...", "details": {...}}

`ErrorCode` is the central registry — module-prefixed so clients can switch
on exact causes. Raise `ApiError` for a specific code; plain HTTPException
still gets a sensible mapped code from the global handler, so nothing is
ever unlabelled.
"""

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str
    trace_id: str | None = None
    details: dict[str, Any] | None = None


class ErrorCode:
    # ── Generic ──────────────────────────────────────────────────
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    CONFLICT = "CONFLICT"
    # ── Auth / account ───────────────────────────────────────────
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    LOGIN_RATE_LIMITED = "LOGIN_RATE_LIMITED"
    PASSWORD_TOO_WEAK = "PASSWORD_TOO_WEAK"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    # ── Ownership / access ───────────────────────────────────────
    IDOR_BLOCKED = "IDOR_BLOCKED"
    NOT_ASSIGNED = "NOT_ASSIGNED"  # client not assigned to this clinician
    OWNER_ONLY = "OWNER_ONLY"  # resource belongs to another user
    # ── Bookings ─────────────────────────────────────────────────
    BOOKING_SLOT_CONFLICT = "BOOKING_SLOT_CONFLICT"
    BOOKING_OUTSIDE_AVAILABILITY = "BOOKING_OUTSIDE_AVAILABILITY"
    BOOKING_INVALID_TRANSITION = "BOOKING_INVALID_TRANSITION"
    BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
    AVAILABILITY_NOT_FOUND = "AVAILABILITY_NOT_FOUND"
    # ── Clinical records ─────────────────────────────────────────
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    REPORT_FORBIDDEN = "REPORT_FORBIDDEN"
    NOTE_NOT_FOUND = "NOTE_NOT_FOUND"
    NOTE_EMPTY = "NOTE_EMPTY"
    FOLLOWUP_NOT_FOUND = "FOLLOWUP_NOT_FOUND"
    JOURNAL_NOT_FOUND = "JOURNAL_NOT_FOUND"
    PATIENT_NOT_FOUND = "PATIENT_NOT_FOUND"
    # ── Crisis ───────────────────────────────────────────────────
    CRISIS_ACTIVE = "CRISIS_ACTIVE"
    CRISIS_NOT_FOUND = "CRISIS_NOT_FOUND"
    CRISIS_ALREADY_RESOLVED = "CRISIS_ALREADY_RESOLVED"
    # ── Files / uploads ──────────────────────────────────────────
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    ATTACHMENT_NOT_FOUND = "ATTACHMENT_NOT_FOUND"
    # ── Records (typed routers) ──────────────────────────────────
    AI_ANALYSIS_NOT_FOUND = "AI_ANALYSIS_NOT_FOUND"
    EMOTION_RESULT_NOT_FOUND = "EMOTION_RESULT_NOT_FOUND"
    RISK_ASSESSMENT_NOT_FOUND = "RISK_ASSESSMENT_NOT_FOUND"
    TRIAGE_NOT_FOUND = "TRIAGE_NOT_FOUND"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    # ── Devices ──────────────────────────────────────────────────
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_ALREADY_PAIRED = "DEVICE_ALREADY_PAIRED"
    # ── Account ──────────────────────────────────────────────────
    ACCOUNT_UNLOCK_FAILED = "ACCOUNT_UNLOCK_FAILED"
    # ── AI ───────────────────────────────────────────────────────
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    # ── Requests ─────────────────────────────────────────────────
    REQUEST_ENTITY_TOO_LARGE = "REQUEST_ENTITY_TOO_LARGE"


class ApiError(HTTPException):
    """HTTPException that carries an explicit machine-readable code."""

    def __init__(
        self, status_code: int, code: str, message: str, details: dict | None = None, headers: dict | None = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.error_code = code
        self.details = details or {}


def make_error(code: str, message: str, trace_id: str = "", details: dict = None) -> dict:
    return APIError(
        code=code,
        message=message,
        trace_id=trace_id or None,
        details=details,
    ).model_dump(exclude_none=True)


def err(status_code: int, code: str, message: str, details: dict | None = None) -> ApiError:
    """Shorthand: `raise err(409, ErrorCode.BOOKING_SLOT_CONFLICT, "That slot was just taken")`."""
    return ApiError(status_code=status_code, code=code, message=message, details=details)
