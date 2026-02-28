import asyncio
import re
from datetime import UTC, datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from mistralai import Mistral

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowExecution,
    WorkflowExecutionStatus,
)


ALLOWED_DOMAINS = [
    "api.mistral.ai",
    "api.elevenlabs.io",
    "api.composio.dev",
    "api.wandb.ai",
    "api.openai.com",
    "api.anthropic.com",
]

COMPOSIO_ACTIONS = {
    "send_email",
    "create_calendar_event",
    "list_emails",
    "create_task",
    "send_slack_message",
}


class WorkflowExecutor:
    def __init__(self, config):
        self.config = config
        self.mistral_client = Mistral(api_key=config.mistral_api_key)
        self.allowed_domains = getattr(config, "allowed_domains", ALLOWED_DOMAINS)

    async def execute(self, workflow: WorkflowDefinition) -> WorkflowExecution:
        execution = WorkflowExecution(workflow=workflow)
        execution.status = WorkflowExecutionStatus.running

        try:
            step_results = {}
            executed_steps = set()

            for step in workflow.steps:
                if not self._check_dependencies(step, executed_steps):
                    continue

                context = {"previous_results": step_results}
                result = await self._execute_step(step, context)
                step_results[step.id] = result

                if step.output:
                    step_results[f"{step.id}.{step.output}"] = result

                executed_steps.add(step.id)

            execution.step_results = step_results
            execution.status = WorkflowExecutionStatus.completed
            execution.completed_at = datetime.now(tz=UTC)
        except Exception as e:
            execution.status = WorkflowExecutionStatus.failed
            execution.step_results = {"error": str(e)}
            execution.completed_at = datetime.now(tz=UTC)

        return execution

    def _check_dependencies(self, step: WorkflowStep, executed_steps: set) -> bool:
        if not step.depends_on:
            return True
        return all(dep in executed_steps for dep in step.depends_on)

    async def _execute_step(self, step: WorkflowStep, context: dict) -> Any:
        if step.action in COMPOSIO_ACTIONS:
            return await self._execute_composio(step, context)

        action_handlers = {
            "api_call": self._execute_api_call,
            "browser_action": self._execute_browser,
            "llm_summarize": self._execute_llm_summarize,
            "web_search": self._execute_web_search,
        }

        handler = action_handlers.get(step.action)
        if handler:
            return await handler(step, context)

        return {"status": "unknown_action", "action": step.action}

    async def _execute_composio(self, step: WorkflowStep, context: dict) -> dict:
        params = self._interpolate_params(step.params, context)

        return {
            "status": "success",
            "action": step.action,
            "params": params,
            "result": f"Composio action '{step.action}' executed",
        }

    async def _execute_api_call(self, step: WorkflowStep, context: dict) -> dict:
        params = self._interpolate_params(step.params, context)

        url = params.get("url", "")
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        if not self._is_domain_allowed(domain):
            return {
                "status": "error",
                "error": f"Domain {domain} not in allowlist",
            }

        try:
            method = params.get("method", "GET").upper()
            headers = params.get("headers", {})
            body = params.get("body")

            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=body, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=body, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"status": "error", "error": f"Unsupported method {method}"}

                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response": response.json() if response.headers.get("content-type") == "application/json" else response.text,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _execute_browser(self, step: WorkflowStep, context: dict) -> dict:
        params = self._interpolate_params(step.params, context)

        return {
            "status": "success",
            "action": "browser_action",
            "params": params,
            "result": "Browser action executed (mock)",
        }

    async def _execute_llm_summarize(self, step: WorkflowStep, context: dict) -> dict:
        params = self._interpolate_params(step.params, context)

        content = params.get("content", "")
        style = params.get("style", "neutral")

        try:
            message = await self.mistral_client.chat.complete_async(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a helpful summarizer. Summarize in {style} style.",
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following content:\n\n{content}",
                    },
                ],
            )

            summary = message.choices[0].message.content

            return {
                "status": "success",
                "summary": summary,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _execute_web_search(self, step: WorkflowStep, context: dict) -> dict:
        params = self._interpolate_params(step.params, context)

        query = params.get("query", "")

        return {
            "status": "success",
            "query": query,
            "results": [
                {
                    "title": f"Result for '{query}'",
                    "url": "https://example.com",
                    "snippet": "Mock search result",
                }
            ],
        }

    def _is_domain_allowed(self, domain: str) -> bool:
        return domain in self.allowed_domains

    def _interpolate_params(self, params: dict, context: dict) -> dict:
        result = {}
        for key, value in params.items():
            result[key] = self._interpolate(value, context)
        return result

    def _interpolate(self, value: Any, context: dict) -> Any:
        if isinstance(value, str):
            pattern = r"\{\{([^}]+)\}\}"
            matches = re.findall(pattern, value)

            for match in matches:
                keys = match.split(".")
                resolved = self._resolve_path(keys, context)
                if resolved is not None:
                    value = value.replace(f"{{{{{match}}}}}", str(resolved))

            return value
        elif isinstance(value, dict):
            return {k: self._interpolate(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._interpolate(item, context) for item in value]

        return value

    def _resolve_path(self, keys: list[str], context: dict) -> Any:
        current = context.get("previous_results", {})

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None

            if current is None:
                return None

        return current
