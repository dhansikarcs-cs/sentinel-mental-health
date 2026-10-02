from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text

from app.core.database import Base


class CopingTool(Base):
    """A personal coping strategy the patient curates and can open during a crisis."""

    __tablename__ = "coping_tool"
    __table_args__ = (Index("ix_coping_patient_username", "patient_username"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="calming")  # calming | distraction | physical | social | professional
    sort_order = Column(Integer, default=0)
    recommended_by = Column(String, default="")  # psychologist username when suggested by a clinician
    created_at = Column(String, nullable=False)
