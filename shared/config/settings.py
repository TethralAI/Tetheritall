from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./iot_discovery.db")
    github_token: str | None = None
    request_timeout_seconds: int = 20
    max_concurrent_requests: int = 10
    rate_limit_per_second: float = 2.0
    # API auth and rate limiting
    api_token: str | None = "test-api-key"
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
    # Zigbee2MQTT broker
    z2m_broker: str | None = None
    z2m_port: int = 1883
    z2m_username: str | None = None
    z2m_password: str | None = None
    # Smartcar
    smartcar_client_id: str | None = None
    smartcar_client_secret: str | None = None
    smartcar_redirect_uri: str | None = None
    # LLM (OpenAI-compatible)
    openai_api_key: str | None = None
    openai_base_url: str | None = None  # default https://api.openai.com/v1
    openai_model: str = "gpt-4o-mini"
    # LLM guardrails and budgets (lite)
    org_id_header: str = "X-Org-Id"
    llm_budgets: str | None = None  # e.g., "default:1000,orgA:500"
    llm_deterministic: bool = True
    llm_allowed_tools: str | None = None  # comma-separated
    # Infra
    redis_url: str | None = None
    # Outbound security
    outbound_allowlist: str | None = None  # comma-separated hostnames or domains
    outbound_cidrs: str | None = None  # comma-separated CIDR blocks
    # Edge agent and telemetry
    edge_lan_only: bool = True
    telemetry_opt_in: bool = False
    telemetry_namespace: str | None = None
    # Energy/EV protocols (OCPI) - feature flagged
    enable_ocpi: bool = False
    ocpi_base_url: str | None = None
    ocpi_token: str | None = None
    # Proxy/capability
    proxy_capabilities_via_integrations: bool = False
    integrations_base_url: str | None = None  # e.g., http://integrations:8100
    proxy_canary_percent: int = 0  # 0-100
    # JWT auth (optional)
    jwt_secret: str | None = None
    jwt_audience: str | None = None
    org_allowlist: str | None = None
    org_denylist: str | None = None
    # Gateway caching hints
    cache_get_prefixes: str | None = None
    cache_ttl_seconds: int = 60
    # LLM denylist
    llm_prompt_denylist: str | None = None
    # Wearables / health (restore for tests)
    oura_client_id: str | None = None
    oura_redirect_uri: str | None = None
    terra_api_key: str | None = None
    
    # ML Configuration
    ml_local_enabled: bool = True
    ml_edge_enabled: bool = True
    ml_cloud_enabled: bool = True
    ml_default_location: str = "local"
    
    # Security Configuration
    security_monitoring_enabled: bool = True
    security_threat_detection_enabled: bool = True
    security_auto_block_enabled: bool = False
    
    # Orchestration Configuration
    orchestration_max_workflows: int = 100
    orchestration_max_concurrent_workflows: int = 10
    
    # Discovery Configuration
    discovery_scan_interval_seconds: int = 300
    discovery_max_concurrent_scans: int = 5
    
    # Monitoring and Observability
    otel_exporter_otlp_endpoint: str | None = None
    prometheus_enabled: bool = True
    
    # Hubitat Maker API (optional)
    hubitat_maker_base_url: str | None = None  # e.g., http://hubitat.local/apps/api/<appId>
    hubitat_maker_token: str | None = None
    # mTLS for outgoing HTTP clients
    mtls_ca_path: str | None = None
    mtls_client_cert_path: str | None = None
    mtls_client_key_path: str | None = None
    # Kafka configuration
    kafka_bootstrap_servers: str | None = None  # e.g., kafka:9092
    
    # Event Bus Configuration (NATS)
    event_bus_backend: str = "nats"
    nats_url: str | None = None
    nats_stream: str = "tetheritall-events"
    events_stream_key: str = "events:stream"
    events_maxlen: int = 10000

    class Config:
        env_file = ".env"


settings = Settings()

