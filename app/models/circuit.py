"""Circuit ORM model — represents an individual circuit (Chambre 1, Chambre 2)."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base


class Circuit(Base):
    __tablename__ = "circuits"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    label = Column(String(64), nullable=False)           # "Chambre 1", "Chambre 2"
    circuit_index = Column(Integer, nullable=False)      # 1 or 2
    is_on = Column(Boolean, default=True)                # Current ON/OFF state
    is_shed = Column(Boolean, default=False)             # Shed by ESP32 (load shedding)
