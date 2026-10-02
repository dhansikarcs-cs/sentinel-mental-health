import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.core.database import SessionLocal
from app.core.leader import leader
from app.models.booking import Booking
from app.models.journal import JournalEntry
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("sentinel")

_REMINDER_CHECK_SECONDS = 60 * 30  # sweep every 30 minutes
_REMINDER_LEADER_RETRY_SECONDS = 30
_REMINDER_ACTIVE_FROM_HOUR = 8  # only queue reminders between 08:00 and 21:00
_REMINDER_ACTIVE_UNTIL_HOUR = 21

REMINDER_TITLE = "📅 Daily journal reminder"
REMINDER_MESSAGE = "Take 2 minutes to jot down how you're feeling today. Your clinician sees the summary."

SESSION_REMINDER_TITLE = "⏰ Session tomorrow"


def _sweep_session_reminders() -> None:
    """Remind both parties the day before an Approved session.

    Idempotent: the notification title embeds the booking id, and the sweep
    skips anyone already notified for that specific booking.
    """
    db = SessionLocal()
    try:
        tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
        sessions = db.query(Booking).filter(Booking.status == "Approved", Booking.date == tomorrow).all()
        for b in sessions:
            marker = f"#{b.id}"
            for username, is_patient in ((b.patient_username, True), (b.psychologist_username, False)):
                if not username:
                    continue
                already = (
                    db.query(Notification)
                    .filter(
                        Notification.title == SESSION_REMINDER_TITLE,
                        Notification.message.like(f"%{marker}%"),
                        Notification.patient_username == (b.patient_username if is_patient else b.patient_username),
                        Notification.recipient_username == (None if is_patient else username),
                    )
                    .first()
                )
                if already:
                    continue
                db.add(
                    Notification(
                        patient_username=b.patient_username,
                        recipient_username=None if is_patient else username,
                        title=SESSION_REMINDER_TITLE,
                        message=f"Session {marker} tomorrow ({b.date}) at {b.time}. {{}} See you there!".format(
                            "A journal entry beforehand gives your clinician a fresh picture."
                            if is_patient
                            else "The client will appreciate a prepared start."
                        ),
                        notification_type="reminder",
                        read=0,
                        sent_at=datetime.now(UTC).isoformat(),
                    )
                )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("session reminder sweep failed")
    finally:
        db.close()


def _sweep_reminders() -> None:
    db = SessionLocal()
    try:
        now = datetime.now()
        if not (_REMINDER_ACTIVE_FROM_HOUR <= now.hour < _REMINDER_ACTIVE_UNTIL_HOUR):
            return
        today = datetime.now(UTC).date().isoformat()
        patients = db.query(User).filter(User.role == "patient", User.deleted_at.is_(None)).all()
        for p in patients:
            journal_today = (
                db.query(JournalEntry)
                .filter(
                    JournalEntry.patient_username == p.username,
                    JournalEntry.timestamp >= today,
                    JournalEntry.deleted_at.is_(None),
                )
                .first()
            )
            if journal_today:
                continue
            reminder_sent_today = (
                db.query(Notification)
                .filter(
                    Notification.patient_username == p.username,
                    Notification.title == REMINDER_TITLE,
                    Notification.sent_at >= today,
                )
                .first()
            )
            if reminder_sent_today:
                continue
            db.add(
                Notification(
                    patient_username=p.username,
                    title=REMINDER_TITLE,
                    message=REMINDER_MESSAGE,
                    notification_type="reminder",
                    read=0,
                    sent_at=datetime.now(UTC).isoformat(),
                )
            )
            db.commit()
            logger.info("journal reminder queued for %s", p.username)
    except Exception:
        logger.exception("journal reminder sweep failed")
    finally:
        db.close()


async def reminder_loop() -> None:
    loop = asyncio.get_running_loop()
    while True:
        if not await leader.ensure():
            await asyncio.sleep(_REMINDER_LEADER_RETRY_SECONDS)
            continue
        try:
            await loop.run_in_executor(None, _sweep_reminders)
        except Exception:
            logger.exception("journal reminder loop error")
        try:
            await loop.run_in_executor(None, _sweep_session_reminders)
        except Exception:
            logger.exception("session reminder loop error")
        await asyncio.sleep(_REMINDER_CHECK_SECONDS)
