"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, measurements, commands, alerts, billing, devices, users, ws, admin, sms
# Import all models so Base.metadata.create_all picks them up
from app.models import circuit, sms_log  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="IoT Energy Monitor API",
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
    return {"status": "ok", "service": "IoT Energy Monitor"}
