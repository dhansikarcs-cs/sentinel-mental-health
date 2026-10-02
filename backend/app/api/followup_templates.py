from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.structured_errors import ErrorCode, err
from app.events import get_event_bus
from app.models.followup import FollowupTask
from app.models.followup_template import FollowupTemplate
from app.models.user import User
from app.schemas.followup_template import (
    AssignFromTemplateRequest,
    FollowupTemplateCreate,
    FollowupTemplateResponse,
    FollowupTemplateUpdate,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/followup-templates", tags=["followup-templates"])

VALID_CATEGORIES = {"general", "anxiety", "mood", "sleep", "social", "habits"}


def _own_template(db: Session, user: User, template_id: int) -> FollowupTemplate:
    """Templates are private to their author — never another clinician's."""
    template = (
        db.query(FollowupTemplate)
        .filter(
            FollowupTemplate.id == template_id,
            FollowupTemplate.psychologist_username == user.username,
        )
        .first()
    )
    if not template:
        raise err(404, ErrorCode.TEMPLATE_NOT_FOUND, "Template not found")
    return template


@router.get("", response_model=list[FollowupTemplateResponse])
def list_templates(
    category: str = "",
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    query = db.query(FollowupTemplate).filter(FollowupTemplate.psychologist_username == user.username)
    if category:
        query = query.filter(FollowupTemplate.category == category)
    return query.order_by(FollowupTemplate.times_used.desc(), FollowupTemplate.id.desc()).all()


@router.post("", response_model=FollowupTemplateResponse, status_code=201)
def create_template(
    entry: FollowupTemplateCreate,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    if entry.category not in VALID_CATEGORIES:
        raise err(400, ErrorCode.VALIDATION_ERROR, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    template = FollowupTemplate(
        psychologist_username=user.username,
        title=entry.title.strip(),
        description=entry.description.strip(),
        category=entry.category,
        default_due_days=entry.default_due_days,
        times_used=0,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=FollowupTemplateResponse)
def update_template(
    template_id: int,
    entry: FollowupTemplateUpdate,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    template = _own_template(db, user, template_id)
    if entry.title is not None:
        template.title = entry.title.strip()
    if entry.description is not None:
        template.description = entry.description.strip()
    if entry.category is not None:
        if entry.category not in VALID_CATEGORIES:
            raise err(
                400, ErrorCode.VALIDATION_ERROR, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
            )
        template.category = entry.category
    if entry.default_due_days is not None:
        template.default_due_days = entry.default_due_days
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    template = _own_template(db, user, template_id)
    db.delete(template)
    db.commit()
    log_audit(
        "followup_template_deleted",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=str(template_id),
        db=db,
    )
    return {"message": "Template deleted"}


@router.post("/{template_id}/assign")
def assign_from_template(
    template_id: int,
    req: AssignFromTemplateRequest,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    """Turn a template into a real follow-up task for a patient, in one tap.

    The patient must be assigned to the calling clinician. The template's
    usage counter increments so the library surfaces most-used tasks first.
    """
    template = _own_template(db, user, template_id)

    patient = db.query(User).filter(User.username == req.patient_username, User.role == "patient").first()
    if not patient:
        raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
    if patient.assigned_psych != user.username:
        raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")

    due_date = req.due_date
    if not due_date and template.default_due_days:
        due_date = (datetime.now(UTC) + timedelta(days=template.default_due_days)).date().isoformat()

    task = FollowupTask(
        id=f"fu{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{template_id}",
        patient_username=patient.username,
        psychologist_username=user.username,
        title=template.title,
        description=template.description,
        status="pending",
        assigned_at=datetime.now(UTC).isoformat(),
        due_date=due_date,
    )
    db.add(task)
    template.times_used += 1
    db.commit()
    db.refresh(task)

    get_event_bus().emit(
        "followup:created",
        task_id=task.id,
        psych=user.username,
        patient_username=patient.username,
        title=task.title,
    )
    log_audit(
        "followup_assigned_from_template",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=patient.username,
        details=f"template={template_id}, task={task.id}",
        db=db,
    )
    return {"task_id": task.id, "title": task.title, "due_date": task.due_date, "times_used": template.times_used}
