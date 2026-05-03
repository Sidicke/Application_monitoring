"""Billing router — view and generate invoices."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.schemas import BillingOut, BillingGenerate
from app.services.auth_service import get_current_user
from app.services.billing_service import generate_bill

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/{device_id}", response_model=List[BillingOut])
async def get_billing_history(
    device_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.device_id != device_id:
        raise HTTPException(status_code=403, detail="Accès refusé : cet historique ne vous appartient pas")
        
    from app.models.billing import Billing
    result = await db.execute(
        select(Billing)
        .where(Billing.device_id == device_id)
        .order_by(desc(Billing.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/{device_id}/generate", response_model=BillingOut, status_code=201)
async def create_bill(
    device_id: int,
    data: BillingGenerate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé")
    
    if user.device_id != device.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
        
    bill = await generate_bill(db, device, data.period_start, data.period_end)
    return bill
