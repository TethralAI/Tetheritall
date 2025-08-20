from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./iot_discovery.db")
    github_token: str | None = None
    request_timeout_seconds: int = 20
    max_concurrent_requests: int = 10
    rate_limit_per_second: float = 2.0
    # API auth and rate limiting
    api_token: str | None = None
    rate_limit_requests_per_minute: int = 120
    # Cloud integrations
    smartthings_token: str | None = None
    tuya_client_id: str | None = None
    tuya_client_secret: str | None = None
    tuya_base_url: str | None = None  # e.g., https://openapi.tuyaus.com
    # Firebase Cloud Messaging (legacy key)
    fcm_server_key: str | None = None
    # AWS
    aws_region: str | None = None
    aws_s3_bucket: str | None = None
    # HCP Terraform (Terraform Cloud) API
    hcp_terraform_token: str | None = None
    hcp_terraform_org: str | None = None
    hcp_terraform_workspace_id: str | None = None
    # Home Assistant local
    home_assistant_base_url: str | None = None
    home_assistant_token: str | None = None
    # Google Nest SDM
    google_nest_access_token: str | None = None
    # Philips Hue Remote API (generic bearer token)
    hue_remote_token: str | None = None
    # openHAB local
    openhab_base_url: str | None = None
    openhab_token: str | None = None
    # Home Assistant Supervisor (optional)
    ha_supervisor_base_url: str | None = None
    # Z-Wave JS
    zwave_js_url: str | None = None  # e.g., ws://host:3000
    # Alexa Smart Home
    alexa_skill_secret: str | None = None
    # SmartThings OAuth
    smartthings_client_id: str | None = None
    smartthings_client_secret: str | None = None
    smartthings_redirect_uri: str | None = None
    # Tuya OAuth
    tuya_redirect_uri: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()

