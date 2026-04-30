"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# ── Auth ──────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    device_serial: str = Field(description="Serial number of the physical meter")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_admin: bool
    is_active: bool = True
    device_id: Optional[int] = None

    model_config = {"from_attributes": True}

class UserAdminOut(UserOut):
    total_energy_kwh: float = 0.0
    device_count: int = 0


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Circuit ───────────────────────────────────────────────────

class CircuitOut(BaseModel):
    id: int
    device_id: int
    label: str
    circuit_index: int
    is_on: bool
    is_shed: bool

    model_config = {"from_attributes": True}


class CircuitCommand(BaseModel):
    is_on: bool


# ── Device ────────────────────────────────────────────────────

class DeviceOut(BaseModel):
    id: int
    serial_number: str
    name: str
    is_on: bool
    threshold_kwh: float
    kwh_price: float
    currency: str
    system_status: str
    comm_mode: str
    circuits: List[CircuitOut] = []

    model_config = {"from_attributes": True}


class DeviceCommand(BaseModel):
    is_on: bool


class ThresholdUpdate(BaseModel):
    threshold_kwh: float = Field(gt=0)


class DeviceSettingsUpdate(BaseModel):
    kwh_price: Optional[float] = Field(None, gt=0)
    threshold_kwh: Optional[float] = Field(None, gt=0)
    name: Optional[str] = None
    currency: Optional[str] = None


# ── Measurement ───────────────────────────────────────────────

class MeasurementCreate(BaseModel):
    """Payload sent by the ESP32 / simulator."""
    device_serial: str
    voltage: float
    current: float
    power: float
    energy: float
    circuit_index: Optional[int] = None       # 1, 2, or None (global)
    system_status: Optional[str] = None       # normal | alert | shedding
    comm_mode: Optional[str] = None           # wifi | gsm


class MeasurementOut(BaseModel):
    id: int
    device_id: int
    circuit_id: Optional[int] = None
    timestamp: datetime
    voltage: float
    current: float
    power: float
    energy: float

    model_config = {"from_attributes": True}


# ── Alert ─────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    device_id: int
    circuit_id: Optional[int] = None
    timestamp: datetime
    severity: str
    threshold_percent: Optional[int] = None
    message: str
    acknowledged: bool

    model_config = {"from_attributes": True}


class AlertCreate(BaseModel):
    """Payload sent by ESP32 for direct alerts."""
    device_serial: str
    message: str
    severity: str = "warning"
    circuit_index: Optional[int] = None


# ── Billing ───────────────────────────────────────────────────

class BillingOut(BaseModel):
    id: int
    device_id: int
    period_start: datetime
    period_end: datetime
    energy_kwh: float
    amount: float
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingGenerate(BaseModel):
    period_start: datetime
    period_end: datetime


# ── SMS Log ───────────────────────────────────────────────────

class SmsLogCreate(BaseModel):
    """Payload sent by ESP32 when an SMS is received/sent."""
    device_serial: str
    direction: str             # "incoming" | "outgoing"
    phone_number: str = ""
    content: str               # "ON1", "SEUIL=500", etc.
    status: str = "executed"   # "executed" | "rejected" | "pending"


class SmsLogOut(BaseModel):
    id: int
    device_id: int
    timestamp: datetime
    direction: str
    phone_number: str
    content: str
    status: str

    model_config = {"from_attributes": True}
