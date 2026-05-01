import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.device import Device
from app.models.circuit import Circuit
from app.services.auth_service import hash_password

async def seed_admin():
    async with SessionLocal() as db:
        # 1. Create Admin Device
        admin_serial = "MONITOR-ADMIN-001"
        result = await db.execute(select(Device).where(Device.serial_number == admin_serial))
        device = result.scalar_one_or_none()
        
        if not device:
            print(f"Creating admin device: {admin_serial}...")
            device = Device(
                serial_number=admin_serial,
                name="Compteur Admin",
                threshold_kwh=500.0,
                kwh_price=0.15
            )
            db.add(device)
            await db.flush()
            
            # Add circuits
            c1 = Circuit(device_id=device.id, label="Chambre 1", circuit_index=1)
            c2 = Circuit(device_id=device.id, label="Chambre 2", circuit_index=2)
            db.add_all([c1, c2])
            print("Circuits created.")

        # 2. Create Admin User
        admin_email = "admin@monitoring.bj"
        result = await db.execute(select(User).where(User.email == admin_email))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print(f"Creating admin user: {admin_email}...")
            admin = User(
                email=admin_email,
                hashed_password=hash_password("admin2026!"),
                full_name="Administrateur Système",
                is_admin=True,
                device_id=device.id
            )
            db.add(admin)
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

        await db.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    from sqlalchemy import select
    asyncio.run(seed_admin())
