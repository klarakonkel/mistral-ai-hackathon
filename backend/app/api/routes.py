import logging
import secrets
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

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
security = HTTPBearer(auto_error=False)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mpeg", "audio/ogg", "audio/mp4"}
MAX_HISTORY_PER_SESSION = 20

_settings: Optional[Settings] = None
_workflow_generator: Optional[WorkflowGenerator] = None
_workflow_executor: Optional[WorkflowExecutor] = None
_voice_service: Optional[VoiceService] = None
_character_service: Optional[CharacterService] = None
_sessions: dict[str, OrchestratorAgent] = {}


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    settings = _get_settings()
    if not settings.kotoflow_api_key:
        return  # No API key configured = open access (dev mode)
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication")
    if not secrets.compare_digest(credentials.credentials, settings.kotoflow_api_key):
        raise HTTPException(status_code=401, detail="Invalid authentication")


def _get_orchestrator(session_id: str) -> OrchestratorAgent:
    settings = _get_settings()
    if session_id not in _sessions:
        _sessions[session_id] = OrchestratorAgent(settings)
    return _sessions[session_id]


def _get_services():
    global _workflow_generator, _workflow_executor, _voice_service, _character_service

    settings = _get_settings()

    if _workflow_generator is None:
        _workflow_generator = WorkflowGenerator(settings)
    if _workflow_executor is None:
        _workflow_executor = WorkflowExecutor(settings)
    if _voice_service is None:
        _voice_service = VoiceService(settings)
    if _character_service is None:
        _character_service = CharacterService()

    return {
        "workflow_generator": _workflow_generator,
        "workflow_executor": _workflow_executor,
        "voice_service": _voice_service,
        "character_service": _character_service,
    }


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default_factory=lambda: str(uuid4()))


class ChatResponse(BaseModel):
    message: str
    ready: bool
    workflow: Optional[WorkflowDefinition] = None
    character_state: CharacterState
    session_id: str


ALLOWED_SERVICES = frozenset([
    "Gmail", "Slack", "Discord", "Twitter", "Google Sheets", "Google Calendar",
    "Notion", "Trello", "GitHub", "Jira", "Linear", "Salesforce", "HubSpot",
    "Zapier", "Airtable", "Dropbox", "OneDrive", "Teams", "Telegram", "WhatsApp",
])


class WorkflowGenerateRequest(BaseModel):
    request_summary: str = Field(..., min_length=1, max_length=500)
    services: list[str] = Field(..., max_length=10)
    trigger_type: str
    trigger_config: dict

    @staticmethod
    def _sanitize_text(text: str) -> str:
        import re
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


class WorkflowExecuteRequest(BaseModel):
    workflow: WorkflowDefinition


class WorkflowExecuteResponse(BaseModel):
    execution: WorkflowExecution
    xp_result: dict
    character_state: CharacterState


class WorkflowFeedbackRequest(BaseModel):
    user_request: str = Field(..., max_length=500)
    workflow: WorkflowDefinition
    feedback_type: str = Field(..., pattern=r"^(accept|reject|edit)$")
    edited: Optional[dict] = None


class VoiceTranscribeResponse(BaseModel):
    text: str


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class HealthResponse(BaseModel):
    status: str


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(_verify_api_key)])
async def chat(request: ChatRequest):
    services = _get_services()
    orchestrator = _get_orchestrator(request.session_id)

    try:
        orchestrator_response: OrchestratorResponse = await orchestrator.chat(request.message)

        workflow = None
        if orchestrator_response.ready and orchestrator_response.workflow_request:
            try:
                workflow = await services["workflow_generator"].generate(
                    request_summary=orchestrator_response.workflow_request.get("request_summary", ""),
                    services=orchestrator_response.workflow_request.get("services", []),
                    trigger_type=orchestrator_response.workflow_request.get("trigger_type", "manual"),
                    trigger_config=orchestrator_response.workflow_request.get("trigger_config", {}),
                )
            except Exception as e:
                logger.error("Workflow generation failed: %s", e)
                workflow = None

        character_state = services["character_service"].character_state

        return ChatResponse(
            message=orchestrator_response.message,
            ready=orchestrator_response.ready,
            workflow=workflow,
            character_state=character_state,
            session_id=request.session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/reset", dependencies=[Depends(_verify_api_key)])
async def chat_reset(session_id: str = ""):
    if session_id and session_id in _sessions:
        _sessions[session_id].reset()
        del _sessions[session_id]
    return {"status": "reset"}


@router.post("/workflow/generate", response_model=WorkflowDefinition, dependencies=[Depends(_verify_api_key)])
async def workflow_generate(request: WorkflowGenerateRequest):
    services = _get_services()
    if not services["workflow_generator"]:
        raise HTTPException(status_code=500, detail="Service unavailable")

    try:
        sanitized_summary = WorkflowGenerateRequest._sanitize_text(request.request_summary)
        workflow = await services["workflow_generator"].generate(
            request_summary=sanitized_summary,
            services=request.services,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
        )
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Workflow generation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Workflow generation failed")


@router.post("/workflow/execute", response_model=WorkflowExecuteResponse, dependencies=[Depends(_verify_api_key)])
async def workflow_execute(request: WorkflowExecuteRequest):
    services = _get_services()
    if not services["workflow_executor"]:
        raise HTTPException(status_code=500, detail="Service unavailable")

    try:
        execution = await services["workflow_executor"].execute(request.workflow)

        xp_result = services["character_service"].award_xp(request.workflow)
        character_state = services["character_service"].character_state

        return WorkflowExecuteResponse(
            execution=execution,
            xp_result=xp_result,
            character_state=character_state,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Workflow execution error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Workflow execution failed")


@router.post("/workflow/feedback", dependencies=[Depends(_verify_api_key)])
async def workflow_feedback(request: WorkflowFeedbackRequest):
    logger.info("Feedback received: %s", request.feedback_type)
    return {"status": "feedback_collected"}


@router.get("/character", response_model=CharacterState, dependencies=[Depends(_verify_api_key)])
async def get_character():
    services = _get_services()
    return services["character_service"].character_state


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse, dependencies=[Depends(_verify_api_key)])
async def voice_transcribe(file: UploadFile = File(...)):
    services = _get_services()
    if not services["voice_service"]:
        raise HTTPException(status_code=500, detail="Service unavailable")

    if file.content_type and file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    try:
        audio_data = await file.read(MAX_AUDIO_BYTES + 1)
        if len(audio_data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Audio file too large (max 10MB)")

        text = await services["voice_service"].transcribe(audio_data)

        if not text:
            raise HTTPException(status_code=422, detail="Transcription returned empty result")

        return VoiceTranscribeResponse(text=text)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Transcription error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")


@router.post("/voice/synthesize", dependencies=[Depends(_verify_api_key)])
async def voice_synthesize(request: VoiceSynthesizeRequest):
    services = _get_services()
    if not services["voice_service"]:
        raise HTTPException(status_code=500, detail="Service unavailable")

    try:
        voice_config = services["character_service"].character_state.voice_config
        audio_bytes = await services["voice_service"].synthesize(request.text, voice_config)

        if not audio_bytes:
            raise HTTPException(status_code=422, detail="Synthesis returned empty audio")

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Synthesis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Voice synthesis failed")


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
