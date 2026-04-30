"""Users router — profile management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.schemas import UserOut, UserUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_profile(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
async def update_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    await db.flush()
    return user
