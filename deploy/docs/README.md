# Deployment Guide

- Local: `make up` to run via Docker Compose.
- Kubernetes (dev): `make helm-deps && make helm-render-dev` then `make helm-install-dev`.
- Kubernetes (prod): `make helm-deps && make helm-render-prod` then `make helm-install-prod`.

Secrets:
- Configure `gateway` API token and DB secrets via your secrets manager or pre-create `gateway-secrets` and `app-db-url` in namespace `iot`.
- For Terraform/External Secrets, see `secrets.md`.
