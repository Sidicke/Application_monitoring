"""WebSocket router for real-time measurement streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


import logging

logger = logging.getLogger(__name__)

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(device_id, websocket)
    from app.database import async_session
    from app.schemas.schemas import MeasurementCreate, AlertCreate
    from app.routers.measurements import ingest_measurement, update_device_hardware_state
    from app.routers.alerts import create_hardware_alert

    try:
        while True:
            try:
                text = await websocket.receive_text()
                import json
                data = json.loads(text)
                
                msg_type = data.get("type")
                payload = data.get("data")
                
                # Handle state updates from hardware via WebSocket
                if msg_type == "hardware_state_update":
                    async with async_session() as db:
                        try:
                            # payload has device_serial and the state
                            device_serial = payload.get("device_serial")
                            if device_serial:
                                await update_device_hardware_state(device_serial, payload, db)
                                await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"WS DB Error state: {e}")
                            
                elif msg_type == "telemetry":
                    async with async_session() as db:
                        try:
                            m_data = MeasurementCreate(**payload)
                            await ingest_measurement(data=m_data, db=db)
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"WS DB Error telemetry: {e}")
                            
                elif msg_type == "alert":
                    async with async_session() as db:
                        try:
                            a_data = AlertCreate(**payload)
                            await create_hardware_alert(data=a_data, db=db)
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"WS DB Error alert: {e}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON via WS from device {device_id}: {text}")
            except WebSocketDisconnect:
                break # Client disconnected normally
            except Exception as e:
                logger.error(f"Error processing WS message for {device_id}: {e}")
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(device_id, websocket)

