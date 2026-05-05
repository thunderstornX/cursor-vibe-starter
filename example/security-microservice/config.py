"""Typed runtime configuration.

The service refuses to start if the JWT secret is shorter than 32
bytes. That's a deliberate hard line — no defaulting to "changeme",
no warning logs you'll never see in prod. Either you set the env, or
the process exits 1 before the first request ever lands."""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                       extra="ignore")

    app_name: str = "security-microservice"
    env: str = Field(default="dev", pattern="^(dev|stage|prod)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARN|ERROR)$")
    port: int = 8080

    jwt_secret: str = Field(...,
                             min_length=32,
                             description="HMAC secret for JWT signing — must be >=32 bytes")
    jwt_alg: str = Field(default="HS256", pattern="^HS(256|384|512)$")
    jwt_expire_minutes: int = Field(default=60, ge=5, le=24 * 60)

    redis_url: str = Field(default="redis://localhost:6379/0")
    rate_limit_per_minute: int = Field(default=30, ge=1, le=10_000)

    @field_validator("jwt_secret")
    @classmethod
    def _no_placeholder_secret(cls, v: str) -> str:
        # Catch the common "I forgot to set this" cases at startup.
        suspicious = {"replace-me", "changeme", "secret", "test-secret"}
        if any(s in v.lower() for s in suspicious):
            raise ValueError(
                "JWT_SECRET looks like a placeholder. Refusing to start. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        return v


def get_settings() -> Settings:
    """Used by FastAPI Depends; lazy so unit tests can patch env first."""
    return Settings()  # type: ignore[call-arg]
