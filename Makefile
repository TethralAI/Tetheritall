SHELL := /usr/bin/bash

.PHONY: up down logs helm-deps helm-render-dev helm-render-prod helm-install-dev helm-install-prod

up:
	docker compose -f deploy/compose/docker-compose.yml up -d

down:
	docker compose -f deploy/compose/docker-compose.yml down -v

logs:
	docker compose -f deploy/compose/docker-compose.yml logs -f

helm-deps:
	cd deploy/helm/umbrella && helm dependency update | cat

helm-render-dev:
	helm template tetheritall deploy/helm/umbrella -n iot -f deploy/helm/umbrella/values-dev.yaml | cat

helm-render-prod:
	helm template tetheritall deploy/helm/umbrella -n iot -f deploy/helm/umbrella/values-prod.yaml | cat

helm-install-dev:
	helm upgrade --install tetheritall deploy/helm/umbrella -n iot --create-namespace -f deploy/helm/umbrella/values-dev.yaml | cat

helm-install-prod:
	helm upgrade --install tetheritall deploy/helm/umbrella -n iot --create-namespace -f deploy/helm/umbrella/values-prod.yaml | cat
