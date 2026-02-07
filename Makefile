SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: sanity run-prod-hardened update-db \
	help bootstrap-py bootstrap-web \
	lint-py test-py lint-web test-web build-web \
	check test-all

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
WEB_DIR ?= web
NODE_IMAGE ?= node:20-bookworm

WEB_DOCKER_RUN = docker run --rm -t --user "$$(id -u):$$(id -g)" -v "$$(pwd)/$(WEB_DIR):/app" -w /app $(NODE_IMAGE)

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
		"  make build-web     - build web app" \
		"  make check         - lint + test (py + web)" \
		"  make test-all      - test suites only (py + web)"

bootstrap-py:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,address]"

bootstrap-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm install; \
	else \
		$(WEB_DOCKER_RUN) sh -lc "npm install"; \
	fi

lint-py:
	$(RUFF) check .

test-py:
	$(PYTEST)

lint-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run lint; \
	else \
		$(WEB_DOCKER_RUN) sh -lc "npm install && npm run lint"; \
	fi

test-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run test; \
	else \
		$(WEB_DOCKER_RUN) sh -lc "npm install && npm run test"; \
	fi

build-web:
	@if command -v npm >/dev/null 2>&1; then \
		cd $(WEB_DIR) && npm run build; \
	else \
		$(WEB_DOCKER_RUN) sh -lc "npm install && npm run build"; \
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
