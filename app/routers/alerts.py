"""Alerts router — list, acknowledge, delete."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.schemas import AlertOut, AlertCreate
from app.models.device import Device
from app.models.circuit import Circuit
from app.services.auth_service import get_current_user
from app.services.ws_manager import manager

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/", response_model=AlertOut, status_code=201)
async def create_hardware_alert(
    data: AlertCreate,
    db: AsyncSession = Depends(get_db)
):
    """Receive an alert directly from the hardware (unauthenticated via serial)."""
    result = await db.execute(select(Device).where(Device.serial_number == data.device_serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")

    circuit_id = None
    if data.circuit_index is not None:
        cq = await db.execute(select(Circuit).where(
            Circuit.device_id == device.id, 
            Circuit.circuit_index == data.circuit_index
        ))
        circuit = cq.scalar_one_or_none()
        if circuit:
            circuit_id = circuit.id

    alert = Alert(
        device_id=device.id,
        circuit_id=circuit_id,
        severity=data.severity,
        message=data.message,
    )
    db.add(alert)
    await db.flush()
    await db.commit()

    # Broadcast to App
    await manager.broadcast(device.id, {
        "type": "hardware_alert",
        "data": {
            "id": alert.id,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat()
        }
    })

    return alert


@router.get("/{device_id}", response_model=List[AlertOut])
async def get_alerts(
    device_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.device_id != device_id:
        raise HTTPException(status_code=403, detail="Accès refusé : ces alertes ne vous appartiennent pas")

    result = await db.execute(
        select(Alert)
        .where(Alert.device_id == device_id)
        .order_by(desc(Alert.timestamp))
        .limit(limit)
    )
    return result.scalars().all()


@router.put("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    # Ownership Check
    if user.device_id != alert.device_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
        
    alert.acknowledged = True
    await db.flush()
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
        
    # Ownership Check
    if user.device_id != alert.device_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
        
    await db.delete(alert)
    await db.flush()


@router.delete("/all/{device_id}", status_code=204)
async def delete_all_alerts(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(Alert.__table__.delete().where(Alert.device_id == device_id))
    await db.flush()
