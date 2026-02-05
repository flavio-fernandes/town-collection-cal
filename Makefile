.PHONY: sanity

TOWN_ID ?= westford_ma
TOWN_CONFIG_PATH ?= towns/$(TOWN_ID)/town.yaml
DB_PATH ?= data/generated/$(TOWN_ID).json
CACHE_DIR ?= data/cache

sanity:
	python -m town_collection_cal.updater build-db --town $(TOWN_CONFIG_PATH) --out $(DB_PATH) --cache-dir $(CACHE_DIR)
	python scripts/validate_db.py --db $(DB_PATH)
