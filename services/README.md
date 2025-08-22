Services (Phase 2)
==================

This directory contains auxiliary services introduced in Phase 2.

- integrations: exposes capability endpoints and provider health; current API may proxy to it when enabled via feature flag
- api-gateway: thin gateway enforcing API key, Redis rate limits, outbound allowlist, and basic schema validation; proxies to integrations and automation

Environment/config:
- INTEGRATIONS_BASE_URL or `integrations_base_url` in app settings (e.g., http://localhost:8100)
- PROXY_CAPABILITIES_VIA_INTEGRATIONS or `proxy_capabilities_via_integrations=true`
- API_TOKEN (gateway)
- REDIS_URL (gateway rate limiting)
- OUTBOUND_ALLOWLIST (comma-separated domains allowed for outbound calls)

Run:
```bash
uvicorn services.integrations.server:app --reload --port 8100
uvicorn services.api_gateway.server:app --reload --port 8001
```

Production notes:
- Redis HA: use Sentinel or Redis Cluster; set `REDIS_URL` to sentinel service or cluster endpoints. Configure persistence (AOF/RDB) and backups (e.g., daily RDB snapshots).
- Backups/restore: snapshot `dump.rdb` routinely; test restore drills quarterly.
- Helm charts include resources, HPA, and PDB defaults; tune values per environment.

# Services modular layout (scaffolding)

- api-gateway: Front door (auth/rate limit/allowlist/schema validation). For now, existing FastAPI in iot-api-discovery plays this role.
- automation-engine: Rules, schedules, evaluation.
- integrations: Provider adapters; capability-based plugins.
- discovery-import: Documentation hunter, HA importer, mapping/migration.
- mapping-migration: Dynamic mapping, UI schemas, rewriters.
- scheduler: Cheap-charge and other jobs.
- security: RBAC, consent, audit.
- edge: LAN-only adapters/processing.
- insights: Behavioral/analytics agents.
- llm-interface: Frontend LLM tool endpoints and prompt/guardrail mgmt.

This directory is a placeholder to organize independent deployables; code remains under iot-api-discovery until extraction.
