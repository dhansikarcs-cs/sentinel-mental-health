from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rbac import ensure_can_access_patient
from app.core.structured_errors import ErrorCode, err
from app.models.ai_analysis import AIAnalysis
from app.models.user import User
from app.schemas.ai_analysis import AIAnalysisResponse

router = APIRouter(prefix="/ai-analyses", tags=["ai_analyses"])


@router.get("/journal/{journal_id}", response_model=AIAnalysisResponse)
def get_ai_analysis_by_journal(journal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.query(AIAnalysis).filter(AIAnalysis.journal_id == journal_id).first()
    if not result:
        raise err(404, ErrorCode.AI_ANALYSIS_NOT_FOUND, "AI analysis not found")
    ensure_can_access_patient(result.patient_username, user, db)
    return result


@router.get("/patient/{username}", response_model=list[AIAnalysisResponse])
def get_ai_analyses_for_patient(username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_can_access_patient(username, user, db)
    return (
        db.query(AIAnalysis)
        .filter(AIAnalysis.patient_username == username)
        .order_by(AIAnalysis.created_at.desc())
        .limit(50)
        .all()
    )
