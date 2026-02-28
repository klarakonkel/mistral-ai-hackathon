import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import Settings
from app.models.character import CharacterState
from app.models.workflow import WorkflowDefinition, WorkflowExecution
from app.services.character import CharacterService
from app.services.executor import WorkflowExecutor
from app.services.orchestrator import OrchestratorAgent, OrchestratorResponse
from app.services.voice import VoiceService
from app.services.workflow_gen import WorkflowGenerator

logger = logging.getLogger(__name__)

router = APIRouter()

_settings: Optional[Settings] = None
_orchestrator: Optional[OrchestratorAgent] = None
_workflow_generator: Optional[WorkflowGenerator] = None
_workflow_executor: Optional[WorkflowExecutor] = None
_voice_service: Optional[VoiceService] = None
_character_service: Optional[CharacterService] = None


def _get_services():
    global _settings, _orchestrator, _workflow_generator, _workflow_executor, _voice_service, _character_service

    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            _settings = None

    if _orchestrator is None and _settings:
        _orchestrator = OrchestratorAgent(_settings)

    if _workflow_generator is None and _settings:
        _workflow_generator = WorkflowGenerator(_settings)

    if _workflow_executor is None and _settings:
        _workflow_executor = WorkflowExecutor(_settings)

    if _voice_service is None and _settings:
        _voice_service = VoiceService(_settings)

    if _character_service is None:
        _character_service = CharacterService()

    return {
        "settings": _settings,
        "orchestrator": _orchestrator,
        "workflow_generator": _workflow_generator,
        "workflow_executor": _workflow_executor,
        "voice_service": _voice_service,
        "character_service": _character_service,
    }


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    ready: bool
    workflow: Optional[WorkflowDefinition] = None
    character_state: CharacterState


class WorkflowGenerateRequest(BaseModel):
    request_summary: str
    services: list[str]
    trigger_type: str
    trigger_config: dict


class WorkflowExecuteRequest(BaseModel):
    workflow: WorkflowDefinition


class WorkflowExecuteResponse(BaseModel):
    execution: WorkflowExecution
    xp_result: dict
    character_state: CharacterState


class WorkflowFeedbackRequest(BaseModel):
    user_request: str
    workflow: WorkflowDefinition
    feedback_type: str
    edited: Optional[dict] = None


class VoiceTranscribeResponse(BaseModel):
    text: str


class VoiceSynthesizeRequest(BaseModel):
    text: str


class HealthResponse(BaseModel):
    status: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    services = _get_services()
    if not services["orchestrator"]:
        raise HTTPException(status_code=500, detail="Orchestrator service not available")

    try:
        orchestrator_response: OrchestratorResponse = await services["orchestrator"].chat(request.message)

        workflow = None
        if orchestrator_response.ready and orchestrator_response.workflow_request:
            try:
                workflow = await services["workflow_generator"].generate(
                    request_summary=orchestrator_response.workflow_request.get("request_summary"),
                    services=orchestrator_response.workflow_request.get("services", []),
                    trigger_type=orchestrator_response.workflow_request.get("trigger_type"),
                    trigger_config=orchestrator_response.workflow_request.get("trigger_config", {}),
                )
            except Exception as e:
                logger.error(f"Workflow generation failed: {e}")
                workflow = None

        character_state = services["character_service"].character_state

        return ChatResponse(
            message=orchestrator_response.message,
            ready=orchestrator_response.ready,
            workflow=workflow,
            character_state=character_state,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/reset")
async def chat_reset():
    services = _get_services()
    if not services["orchestrator"]:
        raise HTTPException(status_code=500, detail="Orchestrator service not available")

    try:
        services["orchestrator"].reset()
        return {"status": "reset"}
    except Exception as e:
        logger.error(f"Reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/generate", response_model=WorkflowDefinition)
async def workflow_generate(request: WorkflowGenerateRequest):
    services = _get_services()
    if not services["workflow_generator"]:
        raise HTTPException(status_code=500, detail="Workflow generator service not available")

    try:
        workflow = await services["workflow_generator"].generate(
            request_summary=request.request_summary,
            services=request.services,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
        )
        return workflow
    except Exception as e:
        logger.error(f"Workflow generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/execute", response_model=WorkflowExecuteResponse)
async def workflow_execute(request: WorkflowExecuteRequest):
    services = _get_services()
    if not services["workflow_executor"]:
        raise HTTPException(status_code=500, detail="Workflow executor service not available")

    try:
        execution = await services["workflow_executor"].execute(request.workflow)

        xp_result = services["character_service"].award_xp(request.workflow)
        character_state = services["character_service"].character_state

        return WorkflowExecuteResponse(
            execution=execution,
            xp_result=xp_result,
            character_state=character_state,
        )

    except Exception as e:
        logger.error(f"Workflow execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/feedback")
async def workflow_feedback(request: WorkflowFeedbackRequest):
    try:
        feedback_data = {
            "user_request": request.user_request,
            "workflow": request.workflow.model_dump(),
            "feedback_type": request.feedback_type,
            "edited": request.edited,
        }

        logger.info(f"Feedback received: {request.feedback_type}")

        return {"status": "feedback_collected", "feedback": feedback_data}

    except Exception as e:
        logger.error(f"Feedback collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/character", response_model=CharacterState)
async def get_character():
    services = _get_services()
    try:
        return services["character_service"].character_state
    except Exception as e:
        logger.error(f"Character retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(file: UploadFile = File(...)):
    services = _get_services()
    if not services["voice_service"]:
        raise HTTPException(status_code=500, detail="Voice service not available")

    try:
        audio_data = await file.read()
        text = await services["voice_service"].transcribe(audio_data)

        if not text:
            raise ValueError("Transcription returned empty result")

        return VoiceTranscribeResponse(text=text)

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/synthesize")
async def voice_synthesize(request: VoiceSynthesizeRequest):
    services = _get_services()
    if not services["voice_service"]:
        raise HTTPException(status_code=500, detail="Voice service not available")

    try:
        voice_config = services["character_service"].character_state.voice_config
        audio_bytes = await services["voice_service"].synthesize(request.text, voice_config)

        if not audio_bytes:
            raise ValueError("Synthesis returned empty audio")

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"},
        )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
