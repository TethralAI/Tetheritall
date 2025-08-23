SHELL := /usr/bin/bash

.PHONY: install run test clean docker-build docker-run setup-db migrate

# Development
install:
	pip install -r requirements.txt

run:
	uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	uvicorn api.server:app --host 0.0.0.0 --port 8000

# Database
setup-db:
	alembic upgrade head

migrate:
	alembic revision --autogenerate -m "$(message)"
	alembic upgrade head

# Testing
test:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=. --cov-report=html

# Docker
docker-build:
	docker build -t tetheritall .

docker-run:
	docker run -p 8000:8000 tetheritall

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov

# Services
run-redis:
	docker run -d -p 6379:6379 --name redis redis:7-alpine

run-nats:
	docker run -d -p 4222:4222 --name nats nats:latest

# Setup
setup-local:
	cp env.example .env
	pip install -r requirements.txt
	alembic upgrade head

# Health checks
health:
	curl http://localhost:8000/health

metrics:
	curl http://localhost:8000/metrics
