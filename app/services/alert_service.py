"""Alert service — checks thresholds on total measurements (3-tier: 80/90/100%)."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import math

from app.models.alert import Alert
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.circuit import Circuit
from app.services.ws_manager import manager


async def check_threshold(db: AsyncSession, device: Device, ignore_energy: float = 0.0) -> Alert | None:
    """
    Create an alert if total energy reaches 80%, 90% or 100% of the device threshold.
    Returns the alert if created, otherwise None.
    """
    if device.threshold_kwh <= 0:
        return None

    # 1. Calculate total energy from all circuits of this device
    # We take the latest energy reading per circuit and sum them
    subq = (
        select(
            Measurement.circuit_id,
            func.max(Measurement.timestamp).label("max_ts")
        )
        .where(Measurement.device_id == device.id)
        .group_by(Measurement.circuit_id)
        .subquery()
    )

    energy_result = await db.execute(
        select(Measurement.energy)
        .join(subq, (Measurement.circuit_id == subq.c.circuit_id) & (Measurement.timestamp == subq.c.max_ts))
    )
    energies = energy_result.scalars().all()
    total_energy = sum(e for e in energies if e is not None)

    ratio = total_energy / device.threshold_kwh

    if ratio < 0.8:
        # Below 80% — normal (reset status if needed)
        # We don't reset every tick to save DB writes unless necessary, handled elsewhere
        if device.system_status != "normal":
            device.system_status = "normal"
            cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id, Circuit.circuit_index == 2))
            circuit2 = cq.scalar_one_or_none()
            if circuit2 and circuit2.is_shed:
                circuit2.is_shed = False
                await manager.broadcast(device.id, {
                    "type": "circuit_command",
                    "data": {
                        "circuit_index": circuit2.circuit_index,
                        "is_on": circuit2.is_on,
                        "is_shed": False,
                        "label": circuit2.label,
                    }
                })
            await db.flush()
        return None

    # Load Circuit 2 for shedding logic
    cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id, Circuit.circuit_index == 2))
    circuit2 = cq.scalar_one_or_none()

    # Determine current tier
    if ratio >= 1.0:
        current_tier = 100
        severity = "critical"
        message = f"⚡ DÉLESTAGE ! Énergie globale : {total_energy:.2f} kWh (seuil : {device.threshold_kwh:.2f} kWh — 100%)"
        target_status = "shedding"
        if circuit2:
            circuit2.is_on = False
            circuit2.is_shed = True
            await manager.broadcast(device.id, {
                "type": "circuit_command",
                "data": {
                    "circuit_index": circuit2.circuit_index,
                    "is_on": False,
                    "is_shed": True,
                    "label": circuit2.label,
                }
            })
    elif ratio >= 0.9:
        current_tier = 90
        severity = "warning"
        message = f"⚠️ Attention : {total_energy:.2f} kWh consommés, 90% du seuil global de {device.threshold_kwh:.2f} kWh"
        target_status = "alert"
        if circuit2 and circuit2.is_shed:
            circuit2.is_shed = False
            await manager.broadcast(device.id, {
                "type": "circuit_command",
                "data": {
                    "circuit_index": circuit2.circuit_index,
                    "is_on": circuit2.is_on,
                    "is_shed": False,
                    "label": circuit2.label,
                }
            })
    else:
        current_tier = 80
        severity = "info"
        message = f"ℹ️ Énergie globale à {total_energy:.2f} kWh, 80% du seuil de {device.threshold_kwh:.2f} kWh"
        target_status = "alert"
        if circuit2 and circuit2.is_shed:
            circuit2.is_shed = False
            await manager.broadcast(device.id, {
                "type": "circuit_command",
                "data": {
                    "circuit_index": circuit2.circuit_index,
                    "is_on": circuit2.is_on,
                    "is_shed": False,
                    "label": circuit2.label,
                }
            })

    # 2. Prevent spam: Find the latest alert for this device
    last_alert_q = await db.execute(
        select(Alert)
        .where(Alert.device_id == device.id)
        .order_by(Alert.timestamp.desc())
        .limit(1)
    )
    last_alert = last_alert_q.scalar_one_or_none()

    # We alert IF: No alert exists OR the last alert was a different tier (so we alert when crossing a new tier)
    if not last_alert or last_alert.threshold_percent != current_tier:
        # Prevent old alerts causing issues (e.g. if we went from 100 back to 0, then to 80, we want to alert)
        # Assuming energy only goes up, tier only goes up.
        alert = Alert(
            device_id=device.id,
            severity=severity,
            threshold_percent=current_tier,
            message=message,
        )
        device.system_status = target_status
        db.add(alert)
        await db.flush()
        return alert

    # If already alerted for this tier, just update status if it drifted
    if device.system_status != target_status:
        device.system_status = target_status
        await db.flush()

    return None
