"""Persisted conversation turns with the Azure AI Foundry hosted agent.

Messages are stored ENCRYPTED at rest (EncryptedText, same Fernet scheme as
journal content) — chat transcripts are sensitive clinical-adjacent data.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("ix_agent_user_created", "username", "created_at"),
        Index("ix_agent_thread", "username", "thread_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    thread_id = Column(String, default="default")
    role = Column(String, nullable=False)  # user | assistant
    content = Column(EncryptedText, nullable=False)
    provider = Column(String, default="azure_agent")  # azure_agent | ollama | azure | groq | rule
    created_at = Column(String, nullable=False)
