"""SMS log router — journal of SMS commands received/sent by ESP32 via SIM800L."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.device import Device
from app.models.sms_log import SmsLog
from app.schemas.schemas import SmsLogCreate, SmsLogOut
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/log", response_model=SmsLogOut, status_code=201)
async def log_sms(data: SmsLogCreate, db: AsyncSession = Depends(get_db)):
    """ESP32 reports an incoming/outgoing SMS (no auth — device uses serial)."""
    result = await db.execute(select(Device).where(Device.serial_number == data.device_serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")

    sms = SmsLog(
        device_id=device.id,
        direction=data.direction,
        phone_number=data.phone_number,
        content=data.content,
        status=data.status,
    )
    db.add(sms)
    await db.flush()
    return sms


@router.get("/{device_id}", response_model=List[SmsLogOut])
async def get_sms_logs(
    device_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return SMS command history for a device."""
    result = await db.execute(
        select(SmsLog)
        .where(SmsLog.device_id == device_id)
        .order_by(desc(SmsLog.timestamp))
        .limit(limit)
    )
    return result.scalars().all()
