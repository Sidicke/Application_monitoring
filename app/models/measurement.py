"""Measurement ORM model."""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
from app.database import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    circuit_id = Column(Integer, ForeignKey("circuits.id"), nullable=True, index=True)  # NULL = global
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    voltage = Column(Float, nullable=False)       # Volts
    current = Column(Float, nullable=False)       # Amps
    power = Column(Float, nullable=False)         # Watts  (sent by ESP32)
    energy = Column(Float, nullable=False)        # kWh    (sent by ESP32)
    raw_json = Column(JSON, nullable=True)        # Original payload from ESP32
