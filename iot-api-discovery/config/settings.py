from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./iot_discovery.db")
    github_token: str | None = None
    request_timeout_seconds: int = 20
    max_concurrent_requests: int = 10
    rate_limit_per_second: float = 2.0

    class Config:
        env_file = ".env"


settings = Settings()

