from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rbac import ensure_can_access_patient
from app.core.structured_errors import ErrorCode, err
from app.models.risk_assessment import RiskAssessment
from app.models.user import User
from app.schemas.risk_assessment import RiskAssessmentResponse

router = APIRouter(prefix="/risk-assessments", tags=["risk_assessments"])


@router.get("/journal/{journal_id}", response_model=RiskAssessmentResponse)
def get_risk_assessment_by_journal(
    journal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    result = db.query(RiskAssessment).filter(RiskAssessment.journal_id == journal_id).first()
    if not result:
        raise err(404, ErrorCode.RISK_ASSESSMENT_NOT_FOUND, "Risk assessment not found")
    ensure_can_access_patient(result.patient_username, user, db)
    return result


@router.get("/patient/{username}", response_model=list[RiskAssessmentResponse])
def get_risk_assessments_for_patient(
    username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    ensure_can_access_patient(username, user, db)
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.patient_username == username)
        .order_by(RiskAssessment.created_at.desc())
        .limit(50)
        .all()
    )
