from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dates import compute_age
from app.core.dependencies import require_role
from app.core.structured_errors import ErrorCode, err
from app.events import get_event_bus
from app.models.clinical_note import ClinicalNote
from app.models.crisis import CrisisState
from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User
from app.repositories import PatientRepository

router = APIRouter(prefix="/psychologists", tags=["psychologists"])


@router.get("/directory")
def get_clinic_directory(
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Admin/psychologist oversight: list all clinicians and clients in the clinic(s).
    Read-only — no contact data, roles and clinic codes only."""
    repo = PatientRepository(db)
    if user.role == "admin":
        psychs = repo.get_psychologists("")
        clients = db.query(User).filter(User.role == "patient", User.deleted_at.is_(None)).order_by(User.username).all()
    else:
        psychs = repo.get_psychologists(user.clinic_code or "")
        clients = (
            db.query(User)
            .filter(
                User.role == "patient",
                User.clinic_code == (user.clinic_code or ""),
                User.deleted_at.is_(None),
            )
            .order_by(User.username)
            .all()
        )
    return {
        "psychologists": [
            {
                "username": p.username,
                "name": p.name,
                "clinic": p.clinic_code or "",
                "specialisation": p.occupation or "",
            }
            for p in psychs
        ],
        "clients": [
            {
                "username": c.username,
                "name": c.name,
                "age": compute_age(c.dob),
                "clinic": c.clinic_code or "",
                "assigned_psych": c.assigned_psych or "",
                "created_at": c.created_at or "",
            }
            for c in clients
        ],
    }


@router.get("/patients")
def get_assigned_patients(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    patients = repo.get_assigned_patients(user.username)
    return [
        {
            "username": p.username,
            "name": p.name,
            "age": compute_age(p.dob),
            "dob": p.dob or "",
            "occupation": p.occupation,
            "clinic": p.clinic_code or "",
            "onboarding_step": p.onboarding_step or 0,
        }
        for p in patients
    ]


@router.get("/caseload-health")
def get_caseload_health(
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """One-call caseload health check for the clinician.

    Per assigned client: engagement over the last 7 days (journals + moods),
    pending follow-ups, and whether a crisis is active right now — plus a
    summary so the doctor can triage their day at a glance. Rows are sorted
    worst-first: active crises, then disengaged clients, then the rest.
    """
    query = db.query(User).filter(User.role == "patient", User.deleted_at.is_(None))
    if user.role == "admin":
        patients = query.order_by(User.username).all()
    else:
        patients = query.filter(User.assigned_psych == user.username).order_by(User.username).all()

    now = datetime.now(UTC)
    week_ago = (now - timedelta(days=7)).isoformat()
    today = now.date()

    rows: list[dict] = []
    total_pending = 0
    active_crisis_count = 0
    disengaged_count = 0

    for p in patients:
        journals_7d = (
            db.query(JournalEntry)
            .filter(JournalEntry.patient_username == p.username, JournalEntry.timestamp >= week_ago)
            .count()
        )
        moods_7d = (
            db.query(MoodLog).filter(MoodLog.patient_username == p.username, MoodLog.timestamp >= week_ago).count()
        )
        pending = (
            db.query(FollowupTask)
            .filter(FollowupTask.patient_username == p.username, FollowupTask.status == "pending")
            .count()
        )
        crisis = (
            db.query(CrisisState).filter(CrisisState.patient_username == p.username, CrisisState.active == 1).first()
        )

        last_journal = (
            db.query(JournalEntry.timestamp)
            .filter(JournalEntry.patient_username == p.username)
            .order_by(JournalEntry.timestamp.desc())
            .first()
        )
        last_mood = (
            db.query(MoodLog.timestamp)
            .filter(MoodLog.patient_username == p.username)
            .order_by(MoodLog.timestamp.desc())
            .first()
        )
        last_activity = ""
        for candidate in (last_journal, last_mood):
            ts = candidate[0] if candidate else ""
            if ts and ts > last_activity:
                last_activity = ts

        days_quiet = None
        if last_activity:
            try:
                days_quiet = max(0, (now - datetime.fromisoformat(last_activity)).days)
            except (ValueError, TypeError):
                days_quiet = None

        checkins_7d = journals_7d + moods_7d
        if crisis:
            attention = "crisis"
        elif checkins_7d == 0:
            attention = "disengaged"
        elif days_quiet is None or days_quiet >= 5:
            attention = "watch"
        else:
            attention = "ok"

        if crisis:
            active_crisis_count += 1
        if attention == "disengaged":
            disengaged_count += 1
        total_pending += pending

        rows.append(
            {
                "username": p.username,
                "name": p.name,
                "age": compute_age(p.dob),
                "crisis_active": bool(crisis),
                "journals_7d": journals_7d,
                "moods_7d": moods_7d,
                "checkins_7d": checkins_7d,
                "pending_followups": pending,
                "last_activity": last_activity,
                "days_quiet": days_quiet,
                "attention": attention,
            }
        )

    order = {"crisis": 0, "disengaged": 1, "watch": 2, "ok": 3}
    rows.sort(key=lambda r: (order.get(r["attention"], 4), -r["checkins_7d"]))

    return {
        "summary": {
            "total_clients": len(rows),
            "active_crises": active_crisis_count,
            "disengaged": disengaged_count,
            "pending_followups": total_pending,
            "checked_in_today": sum(1 for r in rows if r["last_activity"][:10] == today.isoformat()),
        },
        "clients": rows,
    }


@router.get("/available")
def get_available_psychologists(clinic: str = "", db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    return [
        {
            "username": p.username,
            "name": p.name,
            "professional_code": p.professional_code or "",
            "clinic": p.clinic_code or "",
            "specialisation": p.occupation or "",
        }
        for p in repo.get_psychologists(clinic)
    ]


@router.post("/notes")
def save_clinical_note(
    payload: dict = None,
    patient_username: str = "",
    raw_notes: str = "",
    approved: bool = False,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    # Accept both the JSON body the frontend sends ({patient_username, raw_notes,
    # approved?}) and the legacy query-param form.
    if payload:
        patient_username = payload.get("patient_username", patient_username)
        raw_notes = payload.get("raw_notes", raw_notes)
        approved = payload.get("approved", approved)
    now = datetime.now(UTC).isoformat()
    note = ClinicalNote(
        psychologist_username=user.username,
        patient_username=patient_username,
        raw_notes=raw_notes,
        ai_synthesis=raw_notes,
        timestamp=now,
        approved_by=user.username if approved else "",
        approved_at=now if approved else "",
    )
    db.add(note)
    db.commit()
    get_event_bus().emit(
        "clinical_note:saved",
        psych=user.username,
        patient_username=patient_username,
        approved=approved,
    )
    return {"message": "Saved", "id": note.id}


@router.put("/notes/{note_id}/approve")
def approve_clinical_note(
    note_id: int, user: User = Depends(require_role("psychologist", "admin")), db: Session = Depends(get_db)
):
    note = db.query(ClinicalNote).filter(ClinicalNote.id == note_id).first()
    if not note:
        raise err(404, ErrorCode.NOTE_NOT_FOUND, "Clinical note not found")
    now = datetime.now(UTC).isoformat()
    note.approved_by = user.username
    note.approved_at = now
    db.commit()
    get_event_bus().emit("clinical_note:approved", psych=user.username, note_id=note_id)
    return {"message": "Approved", "id": note_id}


@router.put("/notes/{note_id}")
def edit_clinical_note(
    note_id: int,
    payload: dict = None,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Edit a past report/clinical note. The authoring psychologist or an admin may edit."""
    note = db.query(ClinicalNote).filter(ClinicalNote.id == note_id).first()
    if not note:
        raise err(404, ErrorCode.NOTE_NOT_FOUND, "Note not found")
    if user.role != "admin" and note.psychologist_username != user.username:
        raise err(403, ErrorCode.REPORT_FORBIDDEN, "Only the author or an admin can edit this note")
    raw = (payload or {}).get("raw_notes", "").strip()
    if not raw:
        raise err(400, ErrorCode.NOTE_EMPTY, "Note content cannot be empty")
    note.raw_notes = raw
    note.ai_synthesis = raw
    note.timestamp = datetime.now(UTC).isoformat()
    db.commit()
    get_event_bus().emit("clinical_note:edited", psych=user.username, note_id=note_id)
    return {"message": "Updated", "id": note_id}


@router.get("/notes")
def get_clinical_notes(
    patient: str = "",
    q: str = Query("", description="Full-text search across note contents"),
    date_from: str = Query("", description="YYYY-MM-DD inclusive"),
    date_to: str = Query("", description="YYYY-MM-DD inclusive"),
    approved: str = Query("", description="'yes', 'no', or empty for all"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Saved clinical notes with filters: client, free-text, date range, approval."""
    query = db.query(ClinicalNote)
    if user.role != "admin":
        query = query.filter(ClinicalNote.psychologist_username == user.username)
    if patient:
        query = query.filter(ClinicalNote.patient_username == patient)
    if date_from:
        query = query.filter(ClinicalNote.timestamp >= date_from)
    if date_to:
        query = query.filter(ClinicalNote.timestamp <= f"{date_to}~")  # tilde sorts after any time-of-day
    if approved == "yes":
        query = query.filter(ClinicalNote.approved_by != "")
    elif approved == "no":
        query = query.filter(ClinicalNote.approved_by == "")
    if q:
        # EncryptedText can't be LIKE-searched server-side in a portable way,
        # so filter the decrypted fields in Python over the scoped set.
        needle = q.lower()
        rows = query.order_by(ClinicalNote.timestamp.desc()).limit(200).all()
        rows = [n for n in rows if needle in (n.raw_notes or "").lower() or needle in (n.ai_synthesis or "").lower()]
        return [
            {
                "id": n.id,
                "patient": n.patient_username,
                "ai_synthesis": n.ai_synthesis,
                "raw_notes": n.raw_notes,
                "timestamp": n.timestamp,
                "approved_by": n.approved_by,
                "approved_at": n.approved_at,
            }
            for n in rows[:limit]
        ]
    notes = query.order_by(ClinicalNote.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "patient": n.patient_username,
            "ai_synthesis": n.ai_synthesis,
            "raw_notes": n.raw_notes,
            "timestamp": n.timestamp,
            "approved_by": n.approved_by,
            "approved_at": n.approved_at,
        }
        for n in notes
    ]
