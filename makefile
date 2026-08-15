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

run:
	python main.py

build-docker:
	docker build -t monitoring:latest .

run-docker:
	echo "running docker"
	docker run --rm -p 8001:8000 --name monitoring -d monitoring:latest

stop-docker:
	echo "stop docker"
	docker stop -f monitoring

install:
	pip install -r requirements.txt

ADMIN_EMAIL ?=

bootstrap-admin:
	@test -n "$(ADMIN_EMAIL)" || { echo "Usage: make bootstrap-admin ADMIN_EMAIL=user@example.com" >&2; exit 2; }
	python -m tools.bootstrap_admin --email "$(ADMIN_EMAIL)"

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
