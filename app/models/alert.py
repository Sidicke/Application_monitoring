"""Alert ORM model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    circuit_id = Column(Integer, ForeignKey("circuits.id"), nullable=True)  # NULL = global alert
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    severity = Column(String(16), default="warning")  # info | warning | critical
    threshold_percent = Column(Integer, nullable=True)  # 80, 90, or 100
    message = Column(String(512), nullable=False)
    acknowledged = Column(Boolean, default=False)
