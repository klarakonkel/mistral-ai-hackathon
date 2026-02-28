import json
from typing import Optional

from mistralai import Mistral

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTrigger,
    TriggerType,
)


WORKFLOW_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Workflow name"},
        "description": {
            "type": "string",
            "description": "Workflow description",
        },
        "trigger": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["schedule", "webhook", "manual"],
                },
                "cron": {"type": ["string", "null"]},
                "webhook_url": {"type": ["string", "null"]},
            },
            "required": ["type"],
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "action": {"type": "string"},
                    "params": {"type": "object"},
                    "output": {"type": ["string", "null"]},
                    "depends_on": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                },
                "required": ["id", "action"],
            },
            "minItems": 1,
            "maxItems": 10,
        },
    },
    "required": ["name", "trigger", "steps"],
}

EXAMPLE_WORKFLOW = {
    "name": "Daily Trend Summary",
    "description": "Fetch trending topics and summarize them",
    "trigger": {"type": "schedule", "cron": "0 9 * * *"},
    "steps": [
        {
            "id": "step_1",
            "action": "web_search",
            "params": {"query": "trending AI news"},
            "output": "search_results",
        },
        {
            "id": "step_2",
            "action": "llm_summarize",
            "params": {
                "content": "{{step_1.search_results}}",
                "style": "professional",
            },
            "output": "summary",
            "depends_on": ["step_1"],
        },
    ],
}


class WorkflowGenerator:
    def __init__(self, config):
        self.config = config
        self.mistral_client = Mistral(api_key=config.mistral_api_key)
        self.ft_model_name = config.ft_model_name

    async def generate(
        self,
        request_summary: str,
        services: list[str],
        trigger_type: str,
        trigger_config: dict,
    ) -> WorkflowDefinition:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            request_summary, services, trigger_type, trigger_config
        )

        if self.ft_model_name:
            try:
                response = await self._generate_with_model(
                    system_prompt, user_prompt, self.ft_model_name
                )
                return self._parse_and_validate(response)
            except Exception:
                pass

        response = await self._generate_with_model(
            system_prompt, user_prompt, "mistral-large-latest"
        )
        return self._parse_and_validate(response)

    async def _generate_with_model(
        self, system_prompt: str, user_prompt: str, model_name: str
    ) -> str:
        message = await self.mistral_client.chat.complete_async(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return message.choices[0].message.content

    def _build_system_prompt(self) -> str:
        return f"""You are a workflow generation AI for VoiceFlow.
Your task is to generate valid JSON workflows based on user requirements.

Output ONLY valid JSON matching this schema:
{json.dumps(WORKFLOW_SCHEMA, indent=2)}

Example workflow:
{json.dumps(EXAMPLE_WORKFLOW, indent=2)}

Rules:
- Each step must have a unique id
- Steps can depend on previous steps via depends_on
- Use template syntax {{{{step_id.output}}}} to reference previous outputs
- Actions: web_search, llm_summarize, api_call, browser_action, composio_action
- Trigger types: schedule (needs cron), webhook (needs webhook_url), manual
- Do not include any text outside JSON
- Validate step count does not exceed 10"""

    def _build_user_prompt(
        self,
        request_summary: str,
        services: list[str],
        trigger_type: str,
        trigger_config: dict,
    ) -> str:
        return f"""Generate a workflow for the following request:

Request: {request_summary}
Services to use: {", ".join(services)}
Trigger type: {trigger_type}
Trigger config: {json.dumps(trigger_config)}

Generate the complete workflow definition as JSON only."""

    def _parse_and_validate(self, response: str) -> WorkflowDefinition:
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from model: {e}")

        trigger_data = data.get("trigger", {})
        trigger = WorkflowTrigger(
            type=TriggerType(trigger_data.get("type", "manual")),
            cron=trigger_data.get("cron"),
            webhook_url=trigger_data.get("webhook_url"),
        )

        steps = [
            WorkflowStep(
                id=step.get("id"),
                action=step.get("action"),
                params=step.get("params", {}),
                output=step.get("output"),
                depends_on=step.get("depends_on"),
            )
            for step in data.get("steps", [])
        ]

        workflow = WorkflowDefinition(
            name=data.get("name", "Untitled Workflow"),
            description=data.get("description"),
            trigger=trigger,
            steps=steps,
        )

        return workflow
