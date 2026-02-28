from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)

from pydantic import BaseModel, Field, field_validator


class TriggerType(str, Enum):
    schedule = "schedule"
    webhook = "webhook"
    manual = "manual"


class WorkflowTrigger(BaseModel):
    type: TriggerType
    cron: Optional[str] = None
    webhook_url: Optional[str] = None


class WorkflowStep(BaseModel):
    id: str
    action: str
    params: dict = Field(default_factory=dict)
    output: Optional[str] = None
    depends_on: Optional[list[str]] = None


class WorkflowDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    steps: list[WorkflowStep]

    @field_validator("steps")
    @classmethod
    def validate_step_count(cls, v: list[WorkflowStep]) -> list[WorkflowStep]:
        if len(v) > 10:
            raise ValueError("Workflow cannot have more than 10 steps")
        return v


class WorkflowExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class WorkflowExecution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workflow: WorkflowDefinition
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.pending
    step_results: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=_utcnow)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant", "system"):
            raise ValueError("role must be one of: user, assistant, system")
        return v
