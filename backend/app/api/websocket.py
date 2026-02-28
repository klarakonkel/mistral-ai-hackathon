import base64
import json
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.config import Settings
from app.services.character import CharacterService
from app.services.orchestrator import OrchestratorAgent
from app.services.voice import VoiceService
from app.services.workflow_gen import WorkflowGenerator
from app.services.executor import WorkflowExecutor

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_WS_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_WS_TEXT_BYTES = 16 * 1024  # 16 KB
MAX_CONNECTIONS = 50
_active_connections = 0


def _init_services():
    try:
        settings = Settings()
    except Exception:
        return None
    return {
        "orchestrator": OrchestratorAgent(settings),
        "workflow_generator": WorkflowGenerator(settings),
        "workflow_executor": WorkflowExecutor(settings),
        "voice_service": VoiceService(settings),
        "character_service": CharacterService(),
    }


async def _handle_chat(text: str, services: dict, websocket: WebSocket) -> None:
    response = await services["orchestrator"].chat(text)

    await websocket.send_json({
        "type": "response",
        "data": {"message": response.message, "ready": response.ready},
    })

    if response.ready and response.workflow_request:
        try:
            workflow = await services["workflow_generator"].generate(
                request_summary=response.workflow_request.get("request_summary", ""),
                services=response.workflow_request.get("services", []),
                trigger_type=response.workflow_request.get("trigger_type", "manual"),
                trigger_config=response.workflow_request.get("trigger_config", {}),
            )
            execution = await services["workflow_executor"].execute(workflow)
            xp_result = services["character_service"].award_xp(workflow)

            await websocket.send_json({
                "type": "workflow",
                "data": {
                    "workflow": workflow.model_dump(),
                    "execution": execution.model_dump(),
                },
            })
            await websocket.send_json({"type": "xp_update", "data": xp_result})
        except Exception as e:
            logger.error("Workflow processing failed: %s", e, exc_info=True)
            await websocket.send_json({"type": "error", "data": "Workflow processing failed"})

    try:
        audio = await services["voice_service"].synthesize(
            response.message, services["character_service"].character_state.voice_config
        )
        if audio:
            await websocket.send_json({
                "type": "audio",
                "data": {"audio": base64.b64encode(audio).decode("utf-8")},
            })
    except Exception as e:
        logger.error("TTS error: %s", e, exc_info=True)


@router.websocket("/voice")
async def websocket_voice(websocket: WebSocket, token: str = Query(default="")):
    global _active_connections

    # Auth check
    try:
        settings = Settings()
    except Exception:
        await websocket.close(code=1011)
        return

    if settings.kotoflow_api_key:
        if not token or not secrets.compare_digest(token, settings.kotoflow_api_key):
            await websocket.close(code=4001)
            return

    # Connection limit
    if _active_connections >= MAX_CONNECTIONS:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    _active_connections += 1

    services = _init_services()
    if not services:
        await websocket.send_json({"type": "error", "data": "Services not available"})
        await websocket.close(code=1000)
        _active_connections -= 1
        return

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                audio_data = message["bytes"]
                if len(audio_data) > MAX_WS_AUDIO_BYTES:
                    await websocket.send_json({"type": "error", "data": "Audio too large (max 5MB)"})
                    continue
                try:
                    text = await services["voice_service"].transcribe(audio_data)
                    await websocket.send_json({"type": "transcription", "data": {"text": text}})
                    await _handle_chat(text, services, websocket)
                except Exception as e:
                    logger.error("Voice processing error: %s", e, exc_info=True)
                    await websocket.send_json({"type": "error", "data": "Voice processing failed"})

            elif "text" in message and message["text"]:
                raw_text = message["text"]
                if len(raw_text) > MAX_WS_TEXT_BYTES:
                    await websocket.send_json({"type": "error", "data": "Message too large"})
                    continue
                try:
                    data = json.loads(raw_text)
                    if data.get("type") == "chat":
                        msg = data.get("message", "")
                        if len(msg) > 4000:
                            await websocket.send_json({"type": "error", "data": "Message too long"})
                            continue
                        await _handle_chat(msg, services, websocket)
                    elif data.get("type") == "reset":
                        services["orchestrator"].reset()
                        await websocket.send_json({"type": "reset_ack", "data": {"status": "reset"}})
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "data": "Invalid JSON"})
                except Exception as e:
                    logger.error("Message processing error: %s", e, exc_info=True)
                    await websocket.send_json({"type": "error", "data": "Processing failed"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        _active_connections -= 1
