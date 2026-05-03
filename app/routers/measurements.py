"""Measurements router — ESP32 data ingestion & history with multi-circuit support."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.device import Device
from app.models.circuit import Circuit
from app.models.measurement import Measurement
from app.schemas.schemas import MeasurementCreate, MeasurementOut
from app.services.alert_service import check_threshold
from app.services.ws_manager import manager

router = APIRouter(prefix="/measurements", tags=["Measurements"])


@router.post("/", response_model=MeasurementOut, status_code=201)
async def ingest_measurement(data: MeasurementCreate, db: AsyncSession = Depends(get_db)):
    """Receive a measurement from ESP32 / simulator (no auth — device uses serial)."""
    result = await db.execute(select(Device).where(Device.serial_number == data.device_serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")

    # Resolve circuit_index → circuit_id
    circuit_id = None
    if data.circuit_index is not None:
        cq = await db.execute(
            select(Circuit).where(
                Circuit.device_id == device.id,
                Circuit.circuit_index == data.circuit_index,
            )
        )
        circuit = cq.scalar_one_or_none()
        if circuit:
            circuit_id = circuit.id

    # Update device system_status & comm_mode if provided by ESP
    if data.system_status:
        device.system_status = data.system_status
    if data.comm_mode:
        device.comm_mode = data.comm_mode

    measurement = Measurement(
        device_id=device.id,
        circuit_id=circuit_id,
        voltage=data.voltage,
        current=data.current,
        power=data.power,
        energy=data.energy,
        raw_json=data.model_dump(),
    )
    db.add(measurement)
    await db.flush()

    # Handle alerts sent by ESP32
    alert = None
    if data.system_status and data.system_status != "normal":
        from app.models.alert import Alert
        severity = "info"
        msg = f"Statut détecté par le boîtier: {data.system_status}"
        percent = None
        
        # Determine gravity based on reported status
        if "80" in data.system_status:
            severity = "info"; percent = 80; msg = "Alerte 80% détectée par le boîtier"
        elif "90" in data.system_status:
            severity = "warning"; percent = 90; msg = "Alerte 90% détectée par le boîtier"
        elif "100" in data.system_status or "shed" in data.system_status:
            severity = "critical"; percent = 100; msg = "Délestage détecté par le boîtier"

        # Create alert entry if it's a new tier
        last_alert_q = await db.execute(
            select(Alert).where(Alert.device_id == device.id).order_by(Alert.timestamp.desc()).limit(1)
        )
        last_alert = last_alert_q.scalar_one_or_none()
        
        if not last_alert or last_alert.threshold_percent != percent:
            alert = Alert(
                device_id=device.id,
                severity=severity,
                threshold_percent=percent,
                message=msg,
            )
            db.add(alert)
            await db.flush()

    # Broadcast to WebSocket clients
    ws_payload = {
        "type": "measurement",
        "data": {
            "voltage": data.voltage,
            "current": data.current,
            "power": data.power,
            "energy": data.energy,
            "circuit_index": data.circuit_index,
            "timestamp": measurement.timestamp.isoformat(),
        },
        "system_status": device.system_status,
        "comm_mode": device.comm_mode,
    }
    if alert:
        ws_payload["alert"] = {
            "id": alert.id,
            "severity": alert.severity,
            "threshold_percent": alert.threshold_percent,
            "message": alert.message,
        }
    await manager.broadcast(device.id, ws_payload)

    return measurement


@router.get("/{device_id}", response_model=List[MeasurementOut])
async def get_measurements(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    circuit_id: Optional[int] = Query(None, description="Filter by circuit ID"),
    start: Optional[datetime] = Query(None, description="Start datetime filter"),
    end: Optional[datetime] = Query(None, description="End datetime filter"),
    db: AsyncSession = Depends(get_db),
):
    """Return recent measurements for a device, with optional circuit and time filters."""
    query = select(Measurement).where(Measurement.device_id == device_id)

    if circuit_id is not None:
        query = query.where(Measurement.circuit_id == circuit_id)
    if start is not None:
        query = query.where(Measurement.timestamp >= start)
    if end is not None:
        query = query.where(Measurement.timestamp <= end)

    query = query.order_by(desc(Measurement.timestamp)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/status/{device_serial}")
async def get_device_control_status(device_serial: str, db: AsyncSession = Depends(get_db)):
    """Return hardware ON/OFF state and config for a device (no auth)."""
    result = await db.execute(select(Device).where(Device.serial_number == device_serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
        
    cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id))
    circuits = cq.scalars().all()
    
    return {
        "is_on": device.is_on,
        "threshold_kwh": device.threshold_kwh,
        "kwh_price": device.kwh_price,
        "circuits": {str(c.circuit_index): c.is_on for c in circuits}
    }


@router.post("/update-state/{device_serial}")
async def update_device_hardware_state(
    device_serial: str, 
    data: dict, 
    db: AsyncSession = Depends(get_db)
):
    """Allow hardware to update its internal state (e.g., physical button pressed)."""
    result = await db.execute(select(Device).where(Device.serial_number == device_serial))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    
    # Update master state if provided
    if "is_on" in data:
        device.is_on = data["is_on"]
        
    # Update individual circuits
    if "circuits" in data:
        for idx_str, state in data["circuits"].items():
            try:
                idx = int(idx_str)
                cq = await db.execute(select(Circuit).where(
                    Circuit.device_id == device.id, 
                    Circuit.circuit_index == idx
                ))
                circuit = cq.scalar_one_or_none()
                if circuit:
                    circuit.is_on = state
            except ValueError:
                continue

    await db.flush()
    await db.commit()
    
    # Broadcast change to all UI clients
    await manager.broadcast(device.id, {
        "type": "hardware_update",
        "data": {
            "is_on": device.is_on,
            "circuits": data.get("circuits", {})
        }
    })
    
    return {"status": "ok"}
