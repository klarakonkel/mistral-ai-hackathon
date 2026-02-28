import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.config import Settings
from app.models.workflow import WorkflowDefinition, WorkflowTrigger, WorkflowStep, TriggerType
from app.models.character import VoiceConfig
from app.services.character import CharacterService
from app.main import app


@pytest.fixture
def settings():
    return Settings(
        mistral_api_key="test-mistral-key",
        elevenlabs_api_key="test-elevenlabs-key",
        composio_api_key="test-composio-key",
        wandb_api_key="",
        wandb_project="kotoflow-test",
        cors_origins=["http://localhost:3000"],
        allowed_domains=[
            "api.mistral.ai",
            "api.elevenlabs.io",
            "api.composio.dev",
            "api.wandb.ai",
        ],
    )


@pytest.fixture
def sample_workflow():
    return WorkflowDefinition(
        name="Test Workflow",
        description="A test workflow for testing",
        trigger=WorkflowTrigger(type=TriggerType.manual),
        steps=[
            WorkflowStep(
                id="step_1", action="send_email",
                params={"to": "test@example.com", "subject": "Test"},
                output="email_result",
            ),
            WorkflowStep(
                id="step_2", action="send_slack_message",
                params={"message": "Test message"},
                output="slack_result",
            ),
            WorkflowStep(
                id="step_3", action="create_task",
                params={"title": "Test task"},
                depends_on=["step_1"],
            ),
        ],
    )


@pytest.fixture
def character_service():
    service = CharacterService()
    return service


@pytest.fixture
def test_client():
    return TestClient(app)
