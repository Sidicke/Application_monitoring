"""Devices & thresholds router — with circuit eager loading."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.circuit import Circuit
from app.models.user import User
from app.schemas.schemas import DeviceOut, ThresholdUpdate, DeviceSettingsUpdate, CircuitOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/devices", tags=["Devices"])


async def _device_with_circuits(db: AsyncSession, device: Device) -> DeviceOut:
    """Helper: build DeviceOut with circuits list."""
    cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id))
    circuits = cq.scalars().all()
    return DeviceOut(
        id=device.id,
        serial_number=device.serial_number,
        name=device.name,
        is_on=device.is_on,
        threshold_kwh=device.threshold_kwh,
        kwh_price=device.kwh_price,
        currency=device.currency,
        system_status=device.system_status,
        comm_mode=device.comm_mode,
        circuits=[CircuitOut.model_validate(c) for c in circuits],
    )


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    return await _device_with_circuits(db, device)


@router.put("/{device_id}/threshold", response_model=DeviceOut)
async def update_threshold(
    device_id: int,
    data: ThresholdUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    if user.device_id != device.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    device.threshold_kwh = data.threshold_kwh
    await db.flush()
    return await _device_with_circuits(db, device)


@router.put("/{device_id}/settings", response_model=DeviceOut)
async def update_device_settings(
    device_id: int,
    data: DeviceSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    if user.device_id != device.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if data.kwh_price is not None:
        device.kwh_price = data.kwh_price
    if data.threshold_kwh is not None:
        device.threshold_kwh = data.threshold_kwh
    if data.name is not None:
        device.name = data.name
    if data.currency is not None:
        device.currency = data.currency
    await db.flush()
    return await _device_with_circuits(db, device)
