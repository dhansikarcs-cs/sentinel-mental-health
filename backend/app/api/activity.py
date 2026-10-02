from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.booking import Booking
from app.models.crisis import CrisisLog
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
def get_activity_feed(
    user: User = Depends(require_role("psychologist", "admin")),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    events = []

    if user.role == "admin":
        patients = db.query(User).filter(User.role == "patient").all()
    else:
        patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()
    patient_usernames = [p.username for p in patients]

    for p in patient_usernames:
        for j in (
            db.query(JournalEntry).filter(JournalEntry.patient_username == p, JournalEntry.timestamp >= cutoff).all()
        ):
            events.append(
                {
                    "type": "journal",
                    "patient": p,
                    "timestamp": j.timestamp,
                    "summary": (j.summary or "New journal entry — AI summary pending")[:80],
                    "severity": "info",
                }
            )

        for m in db.query(MoodLog).filter(MoodLog.patient_username == p, MoodLog.timestamp >= cutoff).all():
            events.append(
                {
                    "type": "mood",
                    "patient": p,
                    "timestamp": m.timestamp,
                    "summary": f"Mood: {m.emoji} {m.label}",
                    "severity": "info",
                }
            )

        for c in db.query(CrisisLog).filter(CrisisLog.patient == p, CrisisLog.timestamp >= cutoff).all():
            severity = "high" if c.event in ("triggered",) else "medium"
            events.append(
                {
                    "type": "crisis",
                    "patient": p,
                    "timestamp": c.timestamp,
                    "summary": f"Crisis: {c.event}",
                    "severity": severity,
                }
            )

    booking_q = db.query(Booking).filter(Booking.created_at >= cutoff)
    if user.role != "admin":
        booking_q = booking_q.filter(Booking.psychologist_username == user.username)
    for b in booking_q.all():
        events.append(
            {
                "type": "booking",
                "patient": b.patient_username,
                "timestamp": b.created_at,
                "summary": f"Booking {b.status}: {b.date} @ {b.time}",
                "severity": "info",
            }
        )

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return {"events": events[:50]}
