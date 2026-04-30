"""Billing ORM model."""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime, timezone
from app.database import Base


class Billing(Base):
    __tablename__ = "billings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    energy_kwh = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="XOF")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
