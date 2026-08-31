PYTHON ?= python
PIP ?= $(PYTHON) -m pip
COMPOSE ?= docker compose

.PHONY: \
	init migration migrate clean install install-dev run dev env test lint check \
	bootstrap-admin \
	docker-build docker-up docker-restart docker-down docker-logs docker-ps docker-migrate \
	patch-apply patch-export

init:
	aerich init -t app.db.tortoise.TORTOISE_ORM
	aerich init-db

migration:
	aerich migrate

migrate:
	aerich upgrade

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

lint:
	ruff check app main.py tools tests

check: lint test

run:
	$(PYTHON) main.py

dev:
	DEBUG=true $(PYTHON) main.py

env:
	@if test -f .env; then \
		echo ".env already exists"; \
	else \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi

ADMIN_EMAIL ?=

bootstrap-admin:
	@test -n "$(ADMIN_EMAIL)" || { echo "Usage: make bootstrap-admin ADMIN_EMAIL=user@example.com" >&2; exit 2; }
	$(PYTHON) -m tools.bootstrap_admin --email "$(ADMIN_EMAIL)"

# Docker workflow -------------------------------------------------------------
docker-build:
	$(COMPOSE) build

docker-up: env
	$(COMPOSE) up --build -d --remove-orphans
	@echo "API: http://localhost:$${APP_PORT:-8000}"

docker-restart: env
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) up --build -d --remove-orphans
	@echo "API: http://localhost:$${APP_PORT:-8000}"

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f api

docker-ps:
	$(COMPOSE) ps

docker-migrate: env
	$(COMPOSE) run --rm migrate


# Patch workflow --------------------------------------------------------------
PATCH ?= changes.patch
BASE ?= HEAD

patch-apply:
	@test -f "$(PATCH)" || { echo "Patch file not found: $(PATCH)" >&2; exit 2; }
	git apply --check "$(PATCH)"
	git apply --index "$(PATCH)"
	@echo "Applied and staged: $(PATCH)"

patch-export:
	@mkdir -p "$$(dirname "$(PATCH)")"
	@if test -n "$$(git ls-files --others --exclude-standard)"; then \
		echo "Warning: untracked files are not included. Run 'git add <file>' first if they belong in the patch." >&2; \
	fi
	@git diff --binary --full-index "$(BASE)" -- > "$(PATCH)"
	@test -s "$(PATCH)" || { rm -f "$(PATCH)"; echo "No changes relative to $(BASE)." >&2; exit 1; }
	@echo "Exported patch: $(PATCH) (base: $(BASE))"
