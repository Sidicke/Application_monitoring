"""Commands router — remote ON/OFF control (global + per-circuit)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.circuit import Circuit
from app.models.user import User
from app.schemas.schemas import DeviceCommand, DeviceOut, CircuitCommand, CircuitOut
from app.services.auth_service import get_current_user
from app.services.ws_manager import manager

router = APIRouter(prefix="/commands", tags=["Commands"])


@router.post("/{device_id}", response_model=DeviceOut)
async def send_command(
    device_id: int,
    cmd: DeviceCommand,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send global ON/OFF command to a device."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    if user.device_id != device.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    device.is_on = cmd.is_on
    
    # Load circuits and propagate state
    cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id))
    circuits = cq.scalars().all()
    for c in circuits:
        c.is_on = cmd.is_on
        
    await db.flush()

    # Notify connected clients
    await manager.broadcast(device.id, {
        "type": "command",
        "data": {"is_on": device.is_on},
    })

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


@router.post("/{device_id}/circuit/{circuit_index}", response_model=CircuitOut)
async def send_circuit_command(
    device_id: int,
    circuit_index: int,
    cmd: CircuitCommand,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send ON/OFF command to a specific circuit (Chambre 1 or 2)."""
    # Verify user owns the device
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    if user.device_id != device.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    # Find circuit
    cq = await db.execute(
        select(Circuit).where(
            Circuit.device_id == device_id,
            Circuit.circuit_index == circuit_index,
        )
    )
    circuit = cq.scalar_one_or_none()
    if not circuit:
        raise HTTPException(status_code=404, detail=f"Circuit {circuit_index} non trouvé")

    circuit.is_on = cmd.is_on
    await db.flush()

    # Notify connected clients
    await manager.broadcast(device.id, {
        "type": "circuit_command",
        "data": {
            "circuit_index": circuit.circuit_index,
            "is_on": circuit.is_on,
            "label": circuit.label,
        },
    })

    return circuit


@router.get("/{device_id}/status", response_model=DeviceOut)
async def get_device_status(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current device status with circuits."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")

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
