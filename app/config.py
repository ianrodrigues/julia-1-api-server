"""Validated configuration, shared by the HTTP server and model lifecycle."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

JULIA_REVISION = "a85b127321d580d65176c89ced8273f305745d85"


class Settings(BaseSettings):
    """Read environment variables, then optional local .env defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_id: str = Field(default="SupersonicLabs/Julia-1", min_length=1)
    model_revision: str = Field(default=JULIA_REVISION, min_length=1)
    device: str = Field(default="cpu", pattern=r"^(cpu|cuda(?::[0-9]+)?)$")
    max_length: int = Field(default=8192, ge=64, le=8192)
    head_length: int = Field(default=512, ge=16)
    cpu_threads: int = Field(default=4, ge=1)
    host: str = Field(default="0.0.0.0", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)
    max_pending_requests: int = Field(default=16, ge=1, le=1024)

    @model_validator(mode="after")
    def validate_context_budget(self) -> "Settings":
        """Reserve state and special-token space beyond the question head."""
        if self.head_length + 4 >= self.max_length:
            raise ValueError("HEAD_LENGTH + 4 must be smaller than MAX_LENGTH")
        return self
