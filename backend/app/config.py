import re
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mistral_api_key: str = ""
    elevenlabs_api_key: str = ""
    composio_api_key: str = ""
    wandb_api_key: str = ""
    wandb_project: str = "kotoflow"
    ft_model_name: Optional[str] = None
    kotoflow_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_domains: list[str] = [
        "api.mistral.ai",
        "api.elevenlabs.io",
        "api.composio.dev",
        "api.wandb.ai",
    ]

    @field_validator("ft_model_name")
    @classmethod
    def validate_ft_model_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_.:\-/]{1,128}$", v):
            raise ValueError(f"Invalid model name: {v!r}")
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError("Wildcard '*' is not allowed in cors_origins with credentials")
        return v

    model_config = {"env_file": ".env"}
