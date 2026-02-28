from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mistral_api_key: str = ""
    elevenlabs_api_key: str = ""
    composio_api_key: str = ""
    wandb_api_key: str = ""
    wandb_project: str = "kotoflow"
    ft_model_name: Optional[str] = None
    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_domains: list[str] = [
        "api.mistral.ai",
        "api.elevenlabs.io",
        "api.composio.dev",
        "api.wandb.ai",
    ]

    model_config = {"env_file": ".env"}
