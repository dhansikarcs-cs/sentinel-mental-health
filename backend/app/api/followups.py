import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_file_upload
from app.core.structured_errors import ErrorCode, err
from app.events import get_event_bus
from app.models.followup import FollowupTask
from app.models.user import User
from app.repositories import FollowupRepository
from app.schemas.followup import FollowupCreate, FollowupResponse, FollowupUpdate

UPLOAD_DIR = "data/followup_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PROOF_DIR = "data/followup_proofs"
os.makedirs(PROOF_DIR, exist_ok=True)

router = APIRouter(prefix="/followups", tags=["followups"])


def _assert_owner(task: FollowupTask, user: User) -> None:
    """Patients may only touch their own tasks; psychologists their own assignments."""
    if user.role == "psychologist" and task.psychologist_username != user.username:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")
    if user.role != "psychologist" and task.patient_username != user.username:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")


@router.post("", response_model=FollowupResponse)
def create_followup(
    entry: FollowupCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = FollowupTask(
        id=str(uuid.uuid4())[:8],
        patient_username=entry.patient_username,
        psychologist_username=user.username,
        title=entry.title,
        description=entry.description,
        status="pending",
        assigned_at=datetime.now(UTC).isoformat(),
        due_date=entry.due_date or "",
    )
    repo.add(task)
    get_event_bus().emit(
        "followup:created",
        task_id=task.id,
        psych=user.username,
        patient_username=entry.patient_username,
        title=entry.title,
    )
    return task


@router.get("", response_model=list[FollowupResponse])
def get_followups(
    status: str = Query("", description="Comma-separated statuses, e.g. pending,completed"),
    patient: str = Query("", description="Psychologists: filter by client username"),
    due_before: str = Query("", description="YYYY-MM-DD — only tasks due on/before this date"),
    overdue: bool = Query(False, description="Only pending tasks past their due date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Follow-up tasks with optional filters.

    Patients always get their own tasks; psychologists get their assignments.
    Filters compose: status + overdue + due_before can be combined, and the
    patient filter is clinician-only (patients can never widen their scope).
    """
    repo = FollowupRepository(db)
    if user.role == "psychologist":
        tasks = repo.get_for_psychologist(user.username)
    else:
        tasks = repo.get_for_patient(user.username)

    if user.role == "psychologist" and patient:
        tasks = [t for t in tasks if t.patient_username == patient]

    if status:
        wanted = {s.strip().lower() for s in status.split(",") if s.strip()}
        tasks = [t for t in tasks if (t.status or "").lower() in wanted]

    today = datetime.now(UTC).date().isoformat()
    if overdue:
        tasks = [t for t in tasks if t.status == "pending" and t.due_date and t.due_date < today]
    if due_before:
        tasks = [t for t in tasks if t.due_date and t.due_date <= due_before]

    return tasks


@router.put("/{task_id}", response_model=FollowupResponse)
def update_followup(
    task_id: str, update: FollowupUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")
    _assert_owner(task, user)
    now = datetime.now(UTC).isoformat()
    grade_changed = False
    feedback_changed = False
    if update.status:
        task.status = update.status
        if update.status == "completed":
            task.completed_at = now
    if "grade" in update.model_fields_set and update.grade:
        if user.role == "psychologist" or update.grade == "none":
            if task.grade != update.grade:
                grade_changed = user.role == "psychologist"
            task.grade = update.grade
        if user.role == "psychologist":
            task.approved_by = user.username
            task.approved_at = now
    if "feedback" in update.model_fields_set and user.role == "psychologist":
        if task.feedback != (update.feedback or ""):
            feedback_changed = True
        task.feedback = update.feedback or ""
    if grade_changed:
        task.grade_updated_at = now
    if feedback_changed:
        task.feedback_updated_at = now
    db.commit()
    db.refresh(task)

    if user.role == "psychologist" and (grade_changed or feedback_changed):
        from app.services.notify import create_notification

        create_notification(
            db,
            patient_username=task.patient_username,
            title="📋 Follow-up evaluated",
            message=f"Your clinician updated your follow-up “{task.title}”. Check it in Follow-ups.",
            notification_type="info",
        )

    get_event_bus().emit(
        "followup:updated",
        task_id=task_id,
        patient_username=task.patient_username,
        user=user.username,
        status=update.status,
        grade=update.grade,
        feedback=task.feedback,
    )
    return task


@router.get("/stats")
def followup_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Small rollup for the filter bar chips: counts by status + overdue."""
    repo = FollowupRepository(db)
    if user.role == "psychologist":
        tasks = repo.get_for_psychologist(user.username)
    else:
        tasks = repo.get_for_patient(user.username)
    today = datetime.now(UTC).date().isoformat()
    return {
        "total": len(tasks),
        "pending": sum(1 for t in tasks if t.status == "pending"),
        "completed": sum(1 for t in tasks if t.status == "completed"),
        "overdue": sum(1 for t in tasks if t.status == "pending" and t.due_date and t.due_date < today),
    }


@router.post("/{task_id}/upload")
async def upload_followup_file(
    task_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")
    _assert_owner(task, user)
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "file")[1]
    fname = f"{task_id}{ext}"
    dest = os.path.join(UPLOAD_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    task.file_path = dest
    db.commit()
    db.refresh(task)
    return ok(data={"file_path": dest, "task_id": task_id})


@router.post("/{task_id}/upload-proof")
async def upload_followup_proof(
    task_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")
    _assert_owner(task, user)
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "file")[1]
    fname = f"proof_{task_id}{ext}"
    dest = os.path.join(PROOF_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    task.file_path = dest
    task.status = "completed"
    task.completed_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(task)
    return ok(data={"file_path": dest, "task_id": task_id})


@router.get("/{task_id}/download")
def download_followup_file(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task or not task.file_path:
        raise err(404, ErrorCode.FOLLOWUP_NOT_FOUND, "Followup not found")
    _assert_owner(task, user)
    if not os.path.exists(task.file_path):
        raise err(404, ErrorCode.ATTACHMENT_NOT_FOUND, "File not found on disk")
    return FileResponse(task.file_path, filename=os.path.basename(task.file_path))
