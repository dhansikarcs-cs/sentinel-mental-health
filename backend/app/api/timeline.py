from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rbac import ensure_can_access_patient
from app.models.user import User
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import build_timeline_events, compute_change_metrics

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/{username}", response_model=TimelineResponse)
def get_timeline(
    username: str,
    days: int = Query(30, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Patients may view their own timeline; psychologists/admin may view their clients'.
    ensure_can_access_patient(username, user, db)
    events = build_timeline_events(username, days, db)
    metrics = compute_change_metrics(username, db)

    return TimelineResponse(events=events, metrics=metrics)


@router.get("/{username}/metrics")
def get_change_metrics(
    username: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_can_access_patient(username, user, db)
    return compute_change_metrics(username, db)
