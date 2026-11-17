from sqlalchemy import Column, Float, Index, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class RingSensorLog(Base):
    __tablename__ = "ring_sensor_log"
    __table_args__ = (
        Index("ix_ring_patient_username", "patient_username"),
        Index("ix_ring_logged_at", "logged_at"),
        Index("ix_ring_device_id", "device_id"),
        Index("uq_ring_device_seq", "device_id", "seq", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, default="")
    patient_username = Column(String, default="")
    # NULL means "not measured". No defaults: a column default would be applied
    # to an explicit None and silently turn missing data back into a fake 0.
    bpm = Column(Integer, nullable=True)
    stress = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    hrv = Column(Integer, nullable=True)
    seq = Column(Integer, nullable=True)
    raw_json = Column(EncryptedText, default="")  # cloud envelope: device_id, seq, source readings, client timestamp
    logged_at = Column(String, nullable=False)
