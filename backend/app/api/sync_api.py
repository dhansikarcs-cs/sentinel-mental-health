from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.input_validator import validate_journal_content
from app.events import get_event_bus
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User
from app.workers.ai_worker import analyze_journal_background

router = APIRouter(prefix="/sync", tags=["offline_sync"])


class OfflineJournalEntry(BaseModel):
    raw_content: str
    timestamp: str
    client_id: str = ""


class OfflineMoodEntry(BaseModel):
    date: str
    emoji: str
    label: str
    timestamp: str
    client_id: str = ""


@router.post("/journals")
def sync_offline_journals(
    entries: list[OfflineJournalEntry],
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    synced = []
    for entry in entries:
        validate_journal_content(entry.raw_content)
        # raw_content is encrypted with a random IV per write, so equality can
        # only be checked on decrypted values in Python — never in a SQL filter.
        # Narrow by (patient, timestamp) first, then compare plaintext.
        candidates = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.patient_username == user.username,
                JournalEntry.timestamp == entry.timestamp,
                JournalEntry.deleted_at.is_(None),
            )
            .all()
        )
        existing = next((j for j in candidates if (j.raw_content or "") == entry.raw_content), None)
        if existing:
            synced.append({"client_id": entry.client_id, "server_id": existing.id, "status": "duplicate"})
            continue

        journal = JournalEntry(
            patient_username=user.username,
            raw_content=entry.raw_content,
            summary="",
            clinical_summary="",
            ai_source="pending",
            emotions="",
            timestamp=entry.timestamp,
        )
        db.add(journal)
        db.flush()
        synced.append({"client_id": entry.client_id, "server_id": journal.id, "status": "created"})

        get_event_bus().emit(
            "journal:submitted",
            journal_id=journal.id,
            patient_username=user.username,
            raw_content=entry.raw_content,
            timestamp=journal.timestamp,
        )

        background_tasks.add_task(
            analyze_journal_background,
            journal_id=journal.id,
            raw_content=entry.raw_content,
            patient_username=user.username,
        )

    db.commit()
    return {"synced": synced, "count": len(synced)}


@router.post("/moods")
def sync_offline_moods(
    entries: list[OfflineMoodEntry],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    synced = []
    for entry in entries:
        existing = (
            db.query(MoodLog)
            .filter(
                MoodLog.patient_username == user.username,
                MoodLog.date == entry.date,
            )
            .first()
        )
        if existing:
            synced.append({"client_id": entry.client_id, "server_id": existing.id, "status": "duplicate"})
            continue

        mood = MoodLog(
            patient_username=user.username,
            date=entry.date,
            emoji=entry.emoji,
            label=entry.label,
            timestamp=entry.timestamp,
        )
        db.add(mood)
        db.flush()
        synced.append({"client_id": entry.client_id, "server_id": mood.id, "status": "created"})

    db.commit()
    return {"synced": synced, "count": len(synced)}
