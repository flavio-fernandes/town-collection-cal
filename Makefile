SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: sanity run-prod-hardened update-db \
	help bootstrap-py bootstrap-web \
	lint-py test-py lint-web test-web test-web-e2e build-web \
	audit-py audit-web \
	check test-all

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
WEB_DIR ?= web
NODE_IMAGE ?= node:20-bookworm
PLAYWRIGHT_VERSION ?= $(shell awk 'f && /"version"/ {gsub(/[",]/, "", $$2); print $$2; exit} /"node_modules\/@playwright\/test"/ {f=1}' $(WEB_DIR)/package-lock.json)
PLAYWRIGHT_IMAGE ?= mcr.microsoft.com/playwright:v$(PLAYWRIGHT_VERSION)-jammy

WEB_DOCKER_RUN = docker run --rm -t --user "$$(id -u):$$(id -g)" -v "$$(pwd)/$(WEB_DIR):/app" -v /app/node_modules -w /app $(NODE_IMAGE)
WEB_PLAYWRIGHT_DOCKER_RUN = docker run --rm -t --user "$$(id -u):$$(id -g)" --ipc=host -v "$$(pwd)/$(WEB_DIR):/app" -v /app/node_modules -w /app $(PLAYWRIGHT_IMAGE)

TOWN_ID ?= westford_ma
TOWN_CONFIG_PATH ?= towns/$(TOWN_ID)/town.yaml
DB_PATH ?= data/generated/$(TOWN_ID).json
CACHE_DIR ?= data/cache

help:
	@printf '%s\n' \
		"Targets:" \
		"  make bootstrap-py  - create .venv and install Python dev deps" \
		"  make bootstrap-web - install web deps (npm or Docker fallback)" \
		"  make lint-py       - run ruff with .venv" \
		"  make test-py       - run pytest with .venv" \
		"  make lint-web      - run web lint" \
		"  make test-web      - run web unit tests" \
		"  make test-web-e2e  - run web e2e tests (Playwright image)" \
		"  make build-web     - build web app" \
		"  make audit-py      - run Python dependency CVE scan (requires pip-audit)" \
		"  make audit-web     - run npm audit for high+ issues" \
		"  make check         - lint + test (py + web)" \
		"  make test-all      - test suites only (py + web)"

bootstrap-py:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,address]"

bootstrap-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm install; \
	elif command -v docker >/dev/null 2>&1; then \
		$(WEB_DOCKER_RUN) sh -lc "npm ci"; \
	else \
		echo "error: neither npm nor docker is available for web bootstrap" >&2; \
		exit 1; \
	fi

lint-py:
	$(RUFF) check .

test-py:
	$(PYTEST)

lint-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run lint; \
	elif command -v docker >/dev/null 2>&1; then \
		$(WEB_DOCKER_RUN) sh -lc "npm ci && npm run lint"; \
	else \
		echo "error: neither npm nor docker is available for web lint" >&2; \
		exit 1; \
	fi

test-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run test; \
	elif command -v docker >/dev/null 2>&1; then \
		$(WEB_DOCKER_RUN) sh -lc "npm ci && npm run test"; \
	else \
		echo "error: neither npm nor docker is available for web tests" >&2; \
		exit 1; \
	fi

test-web-e2e:
	$(WEB_PLAYWRIGHT_DOCKER_RUN) sh -lc "npm ci && npm run test:e2e"

build-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run build; \
	elif command -v docker >/dev/null 2>&1; then \
		$(WEB_DOCKER_RUN) sh -lc "npm ci && npm run build"; \
	else \
		echo "error: neither npm nor docker is available for web build" >&2; \
		exit 1; \
	fi

audit-py:
	@if $(PYTHON) -c "import pip_audit" >/dev/null 2>&1; then \
		$(PYTHON) -m pip_audit; \
	else \
		echo "error: pip-audit not installed in .venv. Run: $(PIP) install pip-audit" >&2; \
		exit 1; \
	fi

audit-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm audit --audit-level=high; \
	elif command -v docker >/dev/null 2>&1; then \
		$(WEB_DOCKER_RUN) sh -lc "npm ci && npm audit --audit-level=high"; \
	else \
		echo "error: neither npm nor docker is available for web audit" >&2; \
		exit 1; \
	fi

check: lint-py test-py lint-web test-web

test-all: test-py test-web

sanity:
	python -m town_collection_cal.updater build-db --town $(TOWN_CONFIG_PATH) --out $(DB_PATH) --cache-dir $(CACHE_DIR)
	python scripts/validate_db.py --db $(DB_PATH)

update-db:
	python -m town_collection_cal.updater build-db --town $(TOWN_CONFIG_PATH) --out $(DB_PATH) --cache-dir $(CACHE_DIR)

run-prod-hardened:
	bash scripts/run_prod_hardened.sh
