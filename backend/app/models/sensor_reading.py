from sqlalchemy import Column, Float, ForeignKey, Integer, String

from app.core.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    device_id = Column(String, default="")

    # NULL means "not measured". No fabricated defaults or derived values.
    heart_rate = Column(Integer, nullable=True)
    rmssd = Column(Float, nullable=True)
    sdnn = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)

    logged_at = Column(String, nullable=False)
