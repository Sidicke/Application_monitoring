"""Seed script — creates initial data with multi-circuit support."""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine, Base, async_session
from app.models.user import User
from app.models.device import Device
from app.models.circuit import Circuit
from app.models.sms_log import SmsLog
from app.models.measurement import Measurement
from app.models.alert import Alert


async def seed():
    # Create all tables (this only creates new tables like circuits and sms_logs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Add new columns to existing tables (ignoring errors if they already exist, in isolated transactions)
    queries = [
        "ALTER TABLE devices ADD COLUMN system_status VARCHAR(16) DEFAULT 'normal'",
        "ALTER TABLE devices ADD COLUMN comm_mode VARCHAR(8) DEFAULT 'wifi'",
        "ALTER TABLE measurements ADD COLUMN circuit_id INTEGER REFERENCES circuits(id)",
        "ALTER TABLE alerts ADD COLUMN circuit_id INTEGER REFERENCES circuits(id)",
        "ALTER TABLE alerts ADD COLUMN threshold_percent INTEGER",
        "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"
    ]
    
    for q in queries:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(q))
        except Exception: 
            pass

    async with async_session() as session:
        async with session.begin():
            # Check if device already exists
            from sqlalchemy import select
            result = await session.execute(select(Device).where(Device.serial_number == "SIM-001"))
            device = result.scalar_one_or_none()

            if device is None:
                device = Device(
                    serial_number="SIM-001",
                    name="Compteur principal",
                    is_on=True,
                    threshold_kwh=5000.0,
                    kwh_price=110.0,
                    currency="XOF",
                    system_status="normal",
                    comm_mode="wifi",
                )
                session.add(device)
                await session.flush()
                print(f"✅ Device SIM-001 created (id={device.id})")
            else:
                # Update existing device with new fields
                device.system_status = device.system_status or "normal"
                device.comm_mode = device.comm_mode or "wifi"
                await session.flush()
                print(f"Device SIM-001 already exists (id={device.id})")

            # Create circuits
            result = await session.execute(select(Circuit).where(Circuit.device_id == device.id))
            existing_circuits = result.scalars().all()

            if not existing_circuits:
                c1 = Circuit(device_id=device.id, label="Chambre 1", circuit_index=1, is_on=True, is_shed=False)
                c2 = Circuit(device_id=device.id, label="Chambre 2", circuit_index=2, is_on=True, is_shed=False)
                session.add(c1)
                session.add(c2)
                await session.flush()
                print(f"Circuit 'Chambre 1' created (id={c1.id})")
                print(f"Circuit 'Chambre 2' created (id={c2.id})")
            else:
                print(f"Circuits already exist ({len(existing_circuits)} found)")

            # Create admin user
            from passlib.context import CryptContext
            pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

            result = await session.execute(select(User).where(User.email == "admin@iot.com"))
            if result.scalar_one_or_none() is None:
                admin = User(
                    email="admin@iot.com",
                    hashed_password=pwd_ctx.hash("admin123"),
                    full_name="Administrateur Système",
                    is_admin=True,
                    device_id=device.id,
                )
                session.add(admin)
                print("Admin user created (admin@iot.com / admin123)")
            else:
                print("Admin user already exists")

            # Create test user
            result = await session.execute(select(User).where(User.email == "user@iot.com"))
            if result.scalar_one_or_none() is None:
                user = User(
                    email="user@iot.com",
                    hashed_password=pwd_ctx.hash("user"),
                    full_name="Utilisateur Test",
                    is_admin=False,
                    device_id=device.id,
                )
                session.add(user)
                print("Test user created (user@iot.com / user)")
            else:
                print("Test user already exists")

    print("\nSeed completed successfully!")
    print("   Admin: admin@iot.com / admin")
    print("   User:  user@iot.com / user")
    print("   Device: SIM-001 (Chambre 1 + Chambre 2)")


if __name__ == "__main__":
    asyncio.run(seed())
