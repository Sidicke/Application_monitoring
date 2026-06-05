"""WebSocket router for real-time measurement streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


import logging
import json

logger = logging.getLogger(__name__)

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(device_id, websocket)
    from app.database import async_session
    from app.schemas.schemas import MeasurementCreate, AlertCreate
    from app.routers.measurements import ingest_measurement, update_device_hardware_state
    from app.routers.alerts import create_hardware_alert

    import asyncio
    try:
        while True:
            try:
                # Wait for message with 25s timeout for keepalive
                text = await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
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

            except asyncio.TimeoutError:
                # Keepalive loop
                try:
                    await websocket.send_text(json.dumps({"type": "ping", "timestamp": str(asyncio.get_event_loop().time())}))
                except Exception as e:
                    logger.warning(f"Failed to send keepalive ping to device {device_id}: {e}")
                    break # Connection dead

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON via WS from device {device_id}: {text}")
            except WebSocketDisconnect:
                break # Client disconnected normally
            except Exception as e:
                logger.error(f"Error processing WS message for {device_id}: {e}")
                break
                
    except Exception as outer_e:
        logger.error(f"WS outer exception for {device_id}: {outer_e}")
    finally:
        manager.disconnect(device_id, websocket)

