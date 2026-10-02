from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.structured_errors import ErrorCode, err
from app.models.coping import CopingTool
from app.models.user import User
from app.models.user import User as UserModel
from app.schemas.coping import CopingToolCreate, CopingToolRecommend, CopingToolResponse, CopingToolUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/coping-tools", tags=["coping-tools"])

VALID_CATEGORIES = {"calming", "distraction", "physical", "social", "professional"}


def _own_tool(db: Session, user: User, tool_id: int) -> CopingTool:
    """Load a coping tool the caller owns — never another patient's."""
    tool = db.query(CopingTool).filter(CopingTool.id == tool_id, CopingTool.patient_username == user.username).first()
    if not tool:
        raise err(404, ErrorCode.TOOL_NOT_FOUND, "Coping tool not found")
    return tool


@router.get("", response_model=list[CopingToolResponse])
def list_tools(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(CopingTool)
        .filter(CopingTool.patient_username == user.username)
        .order_by(CopingTool.sort_order.asc(), CopingTool.id.asc())
        .all()
    )


@router.post("", response_model=CopingToolResponse, status_code=201)
def create_tool(
    entry: CopingToolCreate,
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    if entry.category not in VALID_CATEGORIES:
        raise err(400, ErrorCode.VALIDATION_ERROR, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    tool = CopingTool(
        patient_username=user.username,
        title=entry.title.strip(),
        description=entry.description.strip(),
        category=entry.category,
        sort_order=0,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    log_audit(
        "coping_tool_created",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        details=f"category={entry.category}",
        db=db,
    )
    return tool


@router.put("/{tool_id}", response_model=CopingToolResponse)
def update_tool(
    tool_id: int,
    entry: CopingToolUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tool = _own_tool(db, user, tool_id)
    if entry.title is not None:
        tool.title = entry.title.strip()
    if entry.description is not None:
        tool.description = entry.description.strip()
    if entry.category is not None:
        if entry.category not in VALID_CATEGORIES:
            raise err(
                400, ErrorCode.VALIDATION_ERROR, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
            )
        tool.category = entry.category
    if entry.sort_order is not None:
        tool.sort_order = entry.sort_order
    db.commit()
    db.refresh(tool)
    return tool


@router.post("/recommend", response_model=CopingToolResponse, status_code=201)
def recommend_tool(
    entry: CopingToolRecommend,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Clinician recommends a coping strategy for an assigned patient.

    The tool lands directly in the patient's toolbox, stamped with the
    recommending clinician, so it appears (with attribution) during a crisis.
    """
    patient = (
        db.query(UserModel).filter(UserModel.username == entry.patient_username, UserModel.role == "patient").first()
    )
    if not patient:
        raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
    if user.role != "admin" and patient.assigned_psych != user.username:
        raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")
    if entry.category not in VALID_CATEGORIES:
        raise err(400, ErrorCode.VALIDATION_ERROR, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    tool = CopingTool(
        patient_username=patient.username,
        title=entry.title.strip(),
        description=entry.description.strip(),
        category=entry.category,
        sort_order=-1,  # recommended tools float to the top
        recommended_by=user.username,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    log_audit(
        "coping_tool_recommended",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=patient.username,
        details=f"tool_id={tool.id}, category={entry.category}",
        db=db,
    )
    from app.services.notify import create_notification

    create_notification(
        db,
        patient_username=patient.username,
        title="🧰 New coping strategy from your clinician",
        message=f"{user.username} suggested “{tool.title}” for your toolbox. Try it before your next session.",
        notification_type="info",
    )
    return tool


@router.get("/patient/{patient_username}", response_model=list[CopingToolResponse])
def list_patient_tools(
    patient_username: str,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Clinician view of a patient's toolbox (read-only)."""
    patient = db.query(UserModel).filter(UserModel.username == patient_username, UserModel.role == "patient").first()
    if not patient:
        raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
    if user.role != "admin" and patient.assigned_psych != user.username:
        raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")
    return (
        db.query(CopingTool)
        .filter(CopingTool.patient_username == patient_username)
        .order_by(CopingTool.sort_order.asc(), CopingTool.id.asc())
        .all()
    )


@router.delete("/{tool_id}")
def delete_tool(tool_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tool = _own_tool(db, user, tool_id)
    db.delete(tool)
    db.commit()
    log_audit(
        "coping_tool_deleted",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        db=db,
    )
    return ok(message="Coping tool deleted")
