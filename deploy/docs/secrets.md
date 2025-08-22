# Secrets and Config

- Namespace: `iot`
- Required secrets:
  - `gateway-secrets`: keys `api_token`, `jwt_secret`, `jwks_url`, `mtls_ca`, `mtls_client_cert`, `mtls_client_key`
  - `app-db-url`: key `DATABASE_URL`

Options:
- External Secrets Operator or sealed-secrets recommended.
- For local dev, override env via Helm values or compose env.
