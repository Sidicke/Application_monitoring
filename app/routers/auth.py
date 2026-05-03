"""Authentication router — register & login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.schemas.schemas import UserRegister, UserLogin, Token, UserOut
from app.services.auth_service import hash_password, verify_password, create_access_token

from app.models.circuit import Circuit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check existing user
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    # Find or create device
    result = await db.execute(select(Device).where(Device.serial_number == data.device_serial))
    device = result.scalar_one_or_none()
    
    if device:
        # Check if another user already owns this device
        owner_check = await db.execute(select(User).where(User.device_id == device.id))
        if owner_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ce numéro de série est déjà lié à un compte")
    else:
        # Create new device
        device = Device(serial_number=data.device_serial)
        db.add(device)
        await db.flush()

    # Always ensure default circuits exist for the device
    cq = await db.execute(select(Circuit).where(Circuit.device_id == device.id))
    if not cq.scalars().all():
        c1 = Circuit(device_id=device.id, label="Chambre 1", circuit_index=1)
        c2 = Circuit(device_id=device.id, label="Chambre 2", circuit_index=2)
        db.add_all([c1, c2])

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        device_id=device.id,
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)
