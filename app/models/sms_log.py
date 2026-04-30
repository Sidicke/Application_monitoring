"""SmsLog ORM model — journal of SMS commands sent/received via SIM800L."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone
from app.database import Base


class SmsLog(Base):
    __tablename__ = "sms_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    direction = Column(String(16), nullable=False)       # "incoming" | "outgoing"
    phone_number = Column(String(32), default="")
    content = Column(String(256), nullable=False)        # "ON1", "OFF2", "SEUIL=500"
    status = Column(String(16), default="executed")      # "executed" | "rejected" | "pending"
