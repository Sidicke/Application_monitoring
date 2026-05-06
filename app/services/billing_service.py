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
    """Generate a billing entry by summing consumption of each circuit."""
    from app.models.circuit import Circuit
    from sqlalchemy import and_

    # Get all circuits for this device
    res_circuits = await db.execute(select(Circuit).where(Circuit.device_id == device.id))
    circuits = res_circuits.scalars().all()

    total_energy_kwh = 0.0

    for circuit in circuits:
        # Calculate consumption for this specific circuit
        result = await db.execute(
            select(
                func.max(Measurement.energy).label("max_energy"),
                func.min(Measurement.energy).label("min_energy"),
            ).where(
                Measurement.device_id == device.id,
                Measurement.circuit_id == circuit.id,
                Measurement.timestamp >= period_start,
                Measurement.timestamp <= period_end,
            )
        )
        row = result.one()
        max_e = row.max_energy or 0.0
        min_e = row.min_energy or 0.0
        
        # Add delta if valid
        if max_e >= min_e:
            total_energy_kwh += (max_e - min_e)

    # Also account for "Global" measurements (circuit_id is NULL)
    result_global = await db.execute(
        select(
            func.max(Measurement.energy).label("max_energy"),
            func.min(Measurement.energy).label("min_energy"),
        ).where(
            Measurement.device_id == device.id,
            Measurement.circuit_id == None,
            Measurement.timestamp >= period_start,
            Measurement.timestamp <= period_end,
        )
    )
    row_g = result_global.one()
    max_g = row_g.max_energy or 0.0
    min_g = row_g.min_energy or 1e9 # High value to detect if any global exists
    
    if max_g > 0 and min_g < 1e9:
         total_energy_kwh += (max_g - min_g)

    amount = total_energy_kwh * device.kwh_price

    # For XOF, we usually round to the whole unit
    rounded_amount = round(amount) if device.currency == "XOF" else round(amount, 2)

    bill = Billing(
        device_id=device.id,
        period_start=period_start,
        period_end=period_end,
        energy_kwh=round(total_energy_kwh, 4),
        amount=float(rounded_amount),
        currency=device.currency,
    )
    db.add(bill)
    await db.flush()
    return bill
