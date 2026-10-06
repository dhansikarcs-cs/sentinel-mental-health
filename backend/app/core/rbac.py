"""Shared authorization helpers.

Ownership rule across the API: a caller may access a patient's data only when
they ARE that patient, an admin, or the psychologist the patient is assigned to.
Psychologists may NOT view patients assigned to a different clinician.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.models.user import User


def can_access_patient(username: str, user: User, db: Session) -> bool:
    """True when the caller may read/modify the given patient's data."""
    if user.role == "admin" or user.username == username:
        return True
    if user.role == "psychologist":
        if not username:
            return False
        patient = db.query(User).filter(User.username == username, User.deleted_at.is_(None)).first()
        return patient is not None and patient.assigned_psych == user.username
    return False


def owns_or_psych(username: str, user: User) -> bool:
    # Deprecated shim: kept for call sites outside the audit scope. Prefer
    # can_access_patient which enforces clinician assignment.
    return user.username == username or user.role == "psychologist"


def ensure_can_access_patient(username: str, user: User, db: Session) -> None:
    if not can_access_patient(username, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def ensure_owns_or_psych(username: str, user: User) -> None:
    if user.role in ("psychologist", "admin") or user.username == username:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def get_owner_or_psych(username: str, user: User = Depends(get_current_user)) -> User:
    ensure_owns_or_psych(username, user)
    return user
