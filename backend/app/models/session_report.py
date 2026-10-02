from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class SessionReport(Base):
    """A structured one-page session report a clinician files per session.

    Distinct from the freeform ClinicalNote: reports are fielded (presenting
    concerns, mental state, interventions, risk, progress, homework, plan)
    so they can be rendered as a clean printable page, edited field-by-field,
    and exported. All clinical free-text is encrypted like the rest of the
    clinical record. Attachments live on disk; the path is stored here.
    """

    __tablename__ = "session_reports"
    __table_args__ = (
        Index("ix_sreport_patient", "patient_username"),
        Index("ix_sreport_psych", "psychologist_username"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)

    # Report metadata
    session_date = Column(String, nullable=False)  # YYYY-MM-DD
    session_type = Column(String, default="Standard session")  # intake / review / crisis / telehealth...
    duration_min = Column(Integer, default=50)
    title = Column(String, default="")

    # Structured one-page content (encrypted)
    presenting_concerns = Column(EncryptedText, default="")
    mental_state = Column(EncryptedText, default="")  # MSE: appearance, mood, affect, speech, cognition
    interventions = Column(EncryptedText, default="")  # what was done this session
    risk_assessment = Column(EncryptedText, default="")  # risk level + reasoning
    progress_note = Column(EncryptedText, default="")  # vs last session
    homework = Column(EncryptedText, default="")
    plan = Column(EncryptedText, default="")  # next session plan / referrals
    clinician_summary = Column(Text, default="")  # optional one-liner shown in lists (encrypted)

    # Attachment (e.g. signed PDF, worksheet scan)
    file_path = Column(String, default="")
    file_name = Column(String, default="")

    # Approval chain
    approved_by = Column(String, default="")
    approved_at = Column(String, default="")
    created_at = Column(String, default="")
    updated_at = Column(String, default="")
