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
