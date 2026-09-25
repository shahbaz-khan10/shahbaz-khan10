SHELL := /bin/bash
PY    := auth-service/Backend/.venv/bin/python
COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------ infra
infra-up: ## Start DB + Redis (for local backend dev)
	$(COMPOSE) --profile infra up -d

infra-down: ## Stop DB + Redis
	$(COMPOSE) --profile infra down

app-up: ## Build and start the full stack (app profile)
	$(COMPOSE) --profile app up -d --build

app-down: ## Stop the full stack
	$(COMPOSE) --profile app down

logs: ## Tail all service logs
	$(COMPOSE) --profile app logs -f

# ------------------------------------------------------------------ backend
backend-install: ## Create venv and install backend deps
	python -m venv auth-service/Backend/.venv
	auth-service/Backend/.venv/bin/pip install -r auth-service/Backend/requirements.txt

backend-migrate: ## Apply migrations
	cd auth-service/Backend/src && ../.venv/bin/python manage.py migrate

backend-seed: ## Seed catalog, org and masters data
	cd auth-service/Backend/src && ../.venv/bin/python manage.py seed_catalog
	cd auth-service/Backend/src && ../.venv/bin/python manage.py seed_org
	cd auth-service/Backend/src && ../.venv/bin/python manage.py seed_masters

backend-run: ## Run the API locally (http://127.0.0.1:8000)
	cd auth-service/Backend/src && ../.venv/bin/python manage.py runserver 0.0.0.0:8000

backend-check: ## Django system checks
	cd auth-service/Backend/src && ../.venv/bin/python manage.py check

backend-test: ## Run the pytest suite
	cd auth-service/Backend/src && ../.venv/bin/python -m pytest

# ------------------------------------------------------------------ frontend
frontend-install: ## Install frontend deps
	cd ams/frontend && npm install

frontend-dev: ## Run the Next.js app locally (http://127.0.0.1:3000)
	cd ams/frontend && npm run dev

frontend-build: ## Production build
	cd ams/frontend && npm run build

# ------------------------------------------------------------------ ops
setup: backend-install frontend-install ## Install everything for local dev

test: backend-test ## Run backend tests