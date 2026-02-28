import json
from datetime import UTC, datetime
from typing import Optional

from mistralai import Mistral
from pydantic import BaseModel

from app.models.workflow import ConversationMessage, TriggerType


class OrchestratorResponse(BaseModel):
    message: str
    ready: bool = False
    workflow_request: Optional[dict] = None


class OrchestratorAgent:
    def __init__(self, config):
        self.config = config
        self.client = Mistral(api_key=config.mistral_api_key)
        self.model = "mistral-large-latest"
        self.conversation_history: list[dict] = []
        self.system_prompt = """You are an AI assistant helping users create automation workflows.
Your role is to:
1. Understand the user's automation request through natural conversation
2. Ask clarifying questions to determine:
   - Which services they want to integrate (e.g., Gmail, Slack, Zapier, Discord, Twitter)
   - What trigger type they need (schedule, webhook, or manual)
   - Specific scheduling details if applicable (cron expression)
   - The desired workflow steps and their configuration

3. When you have gathered sufficient information about the automation request, call the generate_workflow tool with the collected details.

Be conversational and helpful. Ask one or two clarifying questions at a time rather than overwhelming the user."""

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_workflow",
                    "description": "Generate a workflow definition based on the collected requirements",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request_summary": {
                                "type": "string",
                                "description": "A concise summary of what the user wants to automate"
                            },
                            "services": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of services to integrate (e.g., 'Gmail', 'Slack', 'Discord')"
                            },
                            "trigger_type": {
                                "type": "string",
                                "enum": ["schedule", "webhook", "manual"],
                                "description": "Type of trigger for the workflow"
                            },
                            "trigger_config": {
                                "type": "object",
                                "description": "Configuration for the trigger (e.g., cron expression for schedule)"
                            }
                        },
                        "required": ["request_summary", "services", "trigger_type", "trigger_config"]
                    }
                }
            }
        ]

    async def chat(self, user_message: str) -> OrchestratorResponse:
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                tools=self.tools,
                tool_choice="auto",
                max_tokens=2048
            )

            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                if tool_call.function.name == "generate_workflow":
                    workflow_args = json.loads(tool_call.function.arguments)

                    self.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message.content or ""
                    })

                    return OrchestratorResponse(
                        message="Workflow generation initiated with your requirements.",
                        ready=True,
                        workflow_request=workflow_args
                    )

            text_content = assistant_message.content or ""
            self.conversation_history.append({
                "role": "assistant",
                "content": text_content
            })

            return OrchestratorResponse(
                message=text_content,
                ready=False,
                workflow_request=None
            )

        except Exception as e:
            error_message = f"Error communicating with Mistral AI: {str(e)}"
            return OrchestratorResponse(
                message=error_message,
                ready=False,
                workflow_request=None
            )

    def reset(self) -> None:
        self.conversation_history.clear()

    def get_conversation_history(self) -> list[ConversationMessage]:
        return [
            ConversationMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=datetime.now(tz=UTC)
            )
            for msg in self.conversation_history
        ]
