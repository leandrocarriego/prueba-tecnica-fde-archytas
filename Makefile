# Plataforma Cordillera — development commands.
#
# Target descriptions (## ...) are in Spanish on purpose: they are what
# `make help` prints to the team. Comments are in English, like the rest of the
# configuration.
#
# pyenv exports VIRTUAL_ENV pointing at an old Python in this environment and uv
# warns on every command; drop it from make's environment.
unexport VIRTUAL_ENV

# One Compose file. With no profile it brings up the infrastructure; `full`
# brings up the whole stack in containers. `ALL` is for down/logs/build, which
# have to reach everything regardless of how it was started.
COMPOSE := docker compose
ALL := --profile full --profile deploy --profile tools

.PHONY: help dev full tools up down logs build clean \
        test test-unit test-integration test-cov lint format \
        playwright-install db-migrate db-revision \
        frontend-api-types backend-shell frontend-shell \
        pre-commit-install pre-commit-run \
        diagrams diagrams-check client-docs deploy

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Development environment ──────────────────────────────────────────────────

dev: ## Levantar solo la infraestructura (Postgres + RabbitMQ); backend y frontend van nativos
	$(COMPOSE) up -d
	@echo ""
	@echo "Infraestructura levantada:"
	@echo "  PostgreSQL: localhost:$${POSTGRES_PORT:-5432}"
	@echo "  RabbitMQ:   localhost:5672 (panel: http://localhost:15672)"
	@echo ""
	@echo "Backend y frontend se ejecutan a mano:"
	@echo "  Backend:  cd backend && uv run uvicorn app.main:app --reload"
	@echo "  Frontend: cd frontend && npm run dev"

full: ## Levantar TODO en contenedores en esta maquina, sin Traefik (profile full)
	$(COMPOSE) --profile full up -d --build
	@echo ""
	@echo "Stack completo levantado (local, sin reverse proxy):"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo ""
	@echo "Recordá aplicar las migraciones:  make db-migrate"

# Runs ON THE SERVER, not from a laptop: it needs the shared `traefik` network
# and a .env with DOMAIN. See README -> Deploy.
deploy: ## Levantar el stack detras de Traefik (profile deploy) — se corre EN el VPS
	@test -n "$$DOMAIN" || grep -q "^DOMAIN=" .env 2>/dev/null || \
		{ echo "Falta DOMAIN: es el dominio que publica Traefik. Definilo en .env."; exit 1; }
	@docker network inspect traefik >/dev/null 2>&1 || \
		{ echo "No existe la red 'traefik'. Este target corre en el servidor, no en tu maquina."; exit 1; }
	$(COMPOSE) --profile deploy up -d --build
	@echo ""
	@echo "Levantado. Traefik publica el dominio de DOMAIN en cuanto emita el certificado."
	@echo "Recorda aplicar las migraciones:  make db-migrate"

tools: ## Levantar Flower para inspeccionar las tasks de Celery (profile tools)
	$(COMPOSE) --profile tools up -d
	@echo "Flower: http://localhost:5555"

up: dev ## Alias de dev

down: ## Detener todos los servicios
	$(COMPOSE) $(ALL) down

logs: ## Ver logs de todos los servicios
	$(COMPOSE) $(ALL) logs -f

build: ## Construir las imágenes Docker
	$(COMPOSE) $(ALL) build

clean: ## Borrar contenedores, volúmenes y recursos huérfanos
	$(COMPOSE) $(ALL) down -v
	docker system prune -f

# ── Tests ───────────────────────────────────────────────────────────────────

test: ## Ejecutar todos los tests
	cd backend && uv run pytest

# --no-cov on the subsets: `--cov-fail-under=80` lives in pyproject's addopts and
# measures the WHOLE suite, so applying it to a slice fails even when every test
# passes (the unit slice alone reaches ~71%). Coverage is a property of the full
# suite: `make test` and CI are what verify it.
test-unit: ## Ejecutar solo los tests unitarios
	cd backend && uv run pytest -m unit --no-cov

test-integration: ## Ejecutar solo los tests de integración
	cd backend && uv run pytest -m integration --no-cov

test-cov: ## Ejecutar los tests con reporte de cobertura
	cd backend && uv run pytest --cov=app --cov-report=html --cov-report=term-missing

# ── Calidad de código ───────────────────────────────────────────────────────

lint: ## Verificar formato y linting (Ruff en el backend, ESLint/Prettier en el frontend)
	cd backend && uv run ruff format --check app tests && uv run ruff check app tests
	cd frontend && npm run lint && npm run format:check

format: ## Formatear el código (Ruff en el backend, Prettier en el frontend)
	cd backend && uv run ruff format app tests && uv run ruff check --fix app tests
	cd frontend && npm run format

# `uvx` runs pre-commit from an ephemeral environment: `uv pip install` needs an
# active venv (there is none at the root) and the pip fallback is blocked by
# PEP 668 on a managed Python.
pre-commit-install: ## Instalar los hooks de pre-commit
	uvx pre-commit install --hook-type pre-commit --hook-type commit-msg

pre-commit-run: ## Ejecutar pre-commit sobre todos los archivos
	uvx pre-commit run --all-files

# ── Extracción (Playwright) ─────────────────────────────────────────────────

playwright-install: ## Instalar el navegador Chromium que usa la extracción
	cd backend && uv run playwright install chromium

# ── Base de datos ───────────────────────────────────────────────────────────

db-migrate: ## Aplicar las migraciones pendientes (alembic upgrade head)
	cd backend && uv run alembic upgrade head

db-revision: ## Crear una migración nueva (usar: make db-revision MESSAGE="descripción")
	cd backend && uv run alembic revision --autogenerate -m "$(MESSAGE)"

# ── Utilities ───────────────────────────────────────────────────────────────

frontend-api-types: ## Generar los tipos TypeScript desde el OpenAPI del backend
	cd frontend && npm run generate-api-types:dev

backend-shell: ## Abrir una shell en el contenedor del backend (requiere `make full` o `make deploy`)
	$(COMPOSE) $(ALL) exec backend /bin/bash

# El frontend es un servicio distinto en cada modo, asi que se prueban los dos.
frontend-shell: ## Abrir una shell en el contenedor del frontend (requiere `make full` o `make deploy`)
	@$(COMPOSE) $(ALL) exec frontend /bin/sh 2>/dev/null || \
		$(COMPOSE) $(ALL) exec frontend_deploy /bin/sh

# ── Spec diagrams (Mermaid) ─────────────────────────────────────────────────
# RUTA narrows the work to one feature:
#   make diagrams RUTA=docs/specs/001-portal-extraction

diagrams-check: ## Validar que todos los .mmd compilan (esto es lo que corre en CI)
	scripts/diagrams/validate.sh $(RUTA)

diagrams: diagrams-check ## Validar y regenerar el README.md de los diagramas + las imagenes en dist/diagramas/
	scripts/diagrams/export.sh $(RUTA)

# ── Client deliverable ──────────────────────────────────────────────────────
# Only what the client has to read and sign: the brief and each spec.md, as PDF,
# with the business diagrams as SVG (vector, so it zooms without pixelating).
# Internal artefacts — plan, tasks, contracts, data-model — never ship.
# FEATURE narrows it to one: make client-docs FEATURE=001-portal-extraction

client-docs: ## Exportar a PDF la documentación cara al cliente, con los diagramas en SVG
	cd backend && uv run python ../scripts/docs/export_client.py $(FEATURE)
