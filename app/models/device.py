"""Device ORM model."""

from sqlalchemy import Column, Integer, String, Boolean, Float
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), default="Compteur principal")
    is_on = Column(Boolean, default=True)
    threshold_kwh = Column(Float, default=100.0)
    kwh_price = Column(Float, default=0.12)
    currency = Column(String(8), default="XOF")
    system_status = Column(String(16), default="normal")  # normal | alert | shedding
    comm_mode = Column(String(8), default="wifi")         # wifi | gsm
