from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.rbac import ensure_can_access_patient
from app.core.structured_errors import ErrorCode, err
from app.models.emotion_result import EmotionResult
from app.models.user import User
from app.schemas.emotion_result import EmotionResultResponse

router = APIRouter(prefix="/emotion-results", tags=["emotion_results"])


@router.get("/journal/{journal_id}", response_model=EmotionResultResponse)
def get_emotion_result_by_journal(
    journal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    result = db.query(EmotionResult).filter(EmotionResult.journal_id == journal_id).first()
    if not result:
        raise err(404, ErrorCode.EMOTION_RESULT_NOT_FOUND, "Emotion result not found")
    ensure_can_access_patient(result.patient_username, user, db)
    return result


@router.get("/patient/{username}", response_model=list[EmotionResultResponse])
def get_emotion_results_for_patient(
    username: str,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    ensure_can_access_patient(username, user, db)
    return (
        db.query(EmotionResult)
        .filter(EmotionResult.patient_username == username)
        .order_by(EmotionResult.created_at.desc())
        .limit(50)
        .all()
    )
