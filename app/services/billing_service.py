"""Billing service — computes energy cost for a period."""

from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.device import Device
from app.models.billing import Billing


async def generate_bill(
    db: AsyncSession,
    device: Device,
    period_start: datetime,
    period_end: datetime,
) -> Billing:
    """Generate a billing entry for a device over a time range."""
    # Get the max energy reading in the period (cumulative kWh from ESP32)
    result = await db.execute(
        select(
            func.max(Measurement.energy).label("max_energy"),
            func.min(Measurement.energy).label("min_energy"),
        ).where(
            Measurement.device_id == device.id,
            Measurement.timestamp >= period_start,
            Measurement.timestamp <= period_end,
        )
    )
    row = result.one()
    max_e = row.max_energy or 0.0
    min_e = row.min_energy or 0.0
    energy_kwh = max_e - min_e

    amount = energy_kwh * device.kwh_price

    bill = Billing(
        device_id=device.id,
        period_start=period_start,
        period_end=period_end,
        energy_kwh=round(energy_kwh, 4),
        amount=round(amount, 2),
        currency=device.currency,
    )
    db.add(bill)
    await db.flush()
    return bill
