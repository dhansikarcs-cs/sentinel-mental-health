from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class FollowupTemplate(Base):
    """A reusable homework template a psychologist assigns with one tap.

    Templates are private to their author — clinical language is personal.
    Description is encrypted like other clinical free-text (followups).
    """

    __tablename__ = "followup_template"
    __table_args__ = (Index("ix_followup_template_owner", "psychologist_username"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(EncryptedText, default="")
    category = Column(String, default="general")  # general | anxiety | mood | sleep | social | habits
    default_due_days = Column(Integer, default=7)
    times_used = Column(Integer, default=0)
    created_at = Column(String, nullable=False)
