# Tetheritall

Orchestration app for IoT discovery, integrations, and API gateway.

Source of truth for Kubernetes manifests is the Helm umbrella chart under `deploy/helm/umbrella`.
Legacy raw manifests and Kustomize overlays are archived under `deploy/infra/`.

Quickstart:

- Local: `make up` (uses `deploy/compose/docker-compose.yml`).
- Kubernetes (dev): `make helm-deps && make helm-render-dev && make helm-install-dev`.

More: see `deploy/docs/` for deployment and secrets guidance.
