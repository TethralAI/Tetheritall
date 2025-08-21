# IoT API Discovery Orchestrator

End-to-end multi-agent system to discover, test, and orchestrate IoT devices via documentation mining, network scanning, proxy controller integration, and automation.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

CockroachDB (optional): set `database_url` in `.env`, e.g. `postgresql+psycopg2://user:pass@host:26257/db?sslmode=require`.

Migrations:
```bash
alembic upgrade head
```

## Key Endpoints
- POST /scan/device
- GET /tasks/{task_id}
- WS /updates
- POST /capabilities (normalize discovered endpoints into capabilities)
- POST /automation/rules

## Consent & Testing Mode
- Set `IOT_DISCOVERY_TESTING=1` to bypass consent in dev.

## Components
- agents: documentation hunter, network scanner, coordinator
- tools: discovery, control (HTTP/MQTT), proxy controllers, zigbee/zwave probes
- automation: simple rule engine
- api: FastAPI surface
- libs/capabilities: capability interfaces and adapter registry (Phase 1)

## Capability adapters (Phase 1)

- New typed capability interfaces live under `libs/capabilities/schemas.py`.
- Provider adapters are registered at startup via `libs/capabilities/register_providers.py`.
- Added capability endpoints (backward-compatible) under `/capability/{provider}/{external_id}/...` for:
  - Switchable: `/switch/on`, `/switch/off`
  - Dimmable: `/dimmer/set` with `{ level: 0-100 }`
  - ColorControl: `/color/hsv` and `/color/temp`

Initial providers wired:
- `smartthings` via cloud API
- `zigbee2mqtt` via MQTT publish (best-effort)

Existing endpoints remain unchanged and compatible.