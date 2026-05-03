"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text, select
from app.database import engine, Base
from app.routers import auth, measurements, commands, alerts, billing, devices, users, ws, admin, sms
from app.models.user import User
from app.models.device import Device
from app.models.circuit import Circuit
from app.database import async_session
from app.services.auth_service import hash_password
from app.models import circuit, sms_log  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Patch schema for existing tables (Production parity)
    queries = [
        "ALTER TABLE devices ADD COLUMN IF NOT EXISTS system_status VARCHAR(16) DEFAULT 'normal'",
        "ALTER TABLE devices ADD COLUMN IF NOT EXISTS comm_mode VARCHAR(8) DEFAULT 'wifi'",
        "ALTER TABLE measurements ADD COLUMN IF NOT EXISTS circuit_id INTEGER",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS circuit_id INTEGER",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS threshold_percent INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"
    ]
    async with engine.begin() as conn:
        for q in queries:
            try:
                await conn.execute(text(q))
            except Exception:
                pass
                
    # Ensure at least one admin exists
    async with async_session() as session:
        async with session.begin():
            # Check for any admin
            res = await session.execute(select(User).where(User.is_admin == True))
            if not res.scalar_one_or_none():
                new_admin = User(
                    email="admin@monitoring.bj",
                    hashed_password=hash_password("admin2026!"),
                    full_name="Admin Principal",
                    is_admin=True,
                    device_id=None # Admin has no device
                )
                session.add(new_admin)
                print("Default admin created: admin@monitoring.bj / admin2026!")

    yield
    await engine.dispose()


app = FastAPI(
    title="MONITORING API",
    description="API REST pour la supervision et le contrôle d'énergie électrique",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(measurements.router)
app.include_router(commands.router)
app.include_router(alerts.router)
app.include_router(billing.router)
app.include_router(devices.router)
app.include_router(users.router)
app.include_router(ws.router)
app.include_router(admin.router)
app.include_router(sms.router)


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "MONITORING"}
