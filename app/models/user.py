"""User ORM model."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, unique=True)
