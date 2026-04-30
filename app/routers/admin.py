"""Admin router — manage all users and view global stats."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.models.measurement import Measurement
from app.schemas.schemas import UserOut, UserAdminOut
from app.services.auth_service import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserAdminOut])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Get all users with their total energy consumption (admin only)."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    
    out_users = []
    for user in users:
        total_energy = 0.0
        device_count = 1 if user.device_id else 0
        
        if user.device_id:
            # Get max energy per circuit for this user's device
            subq = (
                select(func.max(Measurement.energy))
                .where(Measurement.device_id == user.device_id)
                .group_by(Measurement.circuit_id)
            )
            energy_result = await db.execute(subq)
            energies = energy_result.scalars().all()
            total_energy = sum(e for e in energies if e is not None)
            
        out_users.append(UserAdminOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            is_active=user.is_active,
            device_id=user.device_id,
            total_energy_kwh=round(total_energy, 2),
            device_count=device_count
        ))
        
    return out_users


@router.patch("/users/{user_id}/status", response_model=UserOut)
async def toggle_user_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Toggle user active status (admin only)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_update = result.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    user_to_update.is_active = not user_to_update.is_active
    await db.flush()
    return user_to_update


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Delete a user (admin only). Cannot delete self."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    await db.delete(user_to_delete)
    await db.flush()
    return


@router.get("/stats")
async def get_global_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Get global platform statistics (admin only)."""
    # Count total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar_one()

    # Count total devices
    devices_result = await db.execute(select(func.count(Device.id)))
    total_devices = devices_result.scalar_one()

    # Count active devices (is_on == True)
    active_devices_result = await db.execute(select(func.count(Device.id)).where(Device.is_on == True))
    active_devices = active_devices_result.scalar_one()

    # Sum total energy consumed across all devices
    subquery = (
        select(
            Measurement.device_id,
            func.max(Measurement.energy).label("max_e")
        )
        .group_by(Measurement.device_id)
        .subquery()
    )
    energy_result = await db.execute(select(func.sum(subquery.c.max_e)))
    total_energy_kwh = energy_result.scalar_one() or 0.0

    return {
        "total_users": total_users,
        "total_devices": total_devices,
        "active_devices": active_devices,
        "total_energy_kwh": round(total_energy_kwh, 2),
    }
