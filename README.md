# Town Collection Cal

Town-agnostic service that publishes an iCalendar (ICS) feed for trash and recycling pickup dates.

It uses a two-phase design:
1. **Updater**: downloads town source documents, parses them, applies YAML overrides, and writes a validated JSON database.
2. **Service**: loads the JSON database and serves ICS + debug endpoints.

## Quick Start (Local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Optional address parsing (recommended):
```bash
pip install -e ".[dev,address]"
```

Notes:
- On Python 3.14, the `usaddress` extra is skipped because `python-crfsuite` does not provide wheels and often fails to build.
- If you need `usaddress` parsing on macOS, install Xcode CLI tools: `xcode-select --install`, then use Python 3.13 or install `usaddress` manually.

Build the DB:
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache
```

Run the service:
```bash
export TOWN_ID=westford_ma
export TOWN_CONFIG_PATH=$(pwd)/towns/westford_ma/town.yaml
export DB_PATH=$(pwd)/data/generated/westford_ma.json
export FLASK_APP=town_collection_cal.service.app:create_app
python -m flask run --host 0.0.0.0 --port 5000
```

## Docker
Development image (includes optional address parsing):
```bash
docker build -f Dockerfile.dev -t town-collection-cal:dev .
docker run --rm -p 5000:5000 \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e DB_PATH=/app/data/generated/westford_ma.json \
  -v "$PWD/towns:/app/towns" \
  -v "$PWD/data:/app/data" \
  town-collection-cal:dev
```

Production image (includes optional address parsing):
```bash
docker build -t town-collection-cal:prod .
docker run --rm -p 5000:5000 \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e DB_PATH=/app/data/generated/westford_ma.json \
  -v "$PWD/towns:/app/towns" \
  -v "$PWD/data:/app/data" \
  town-collection-cal:prod
```

## Endpoints
- `GET /healthz` -> `{ ok: true }`
- `GET /version` -> DB meta + schema version
- `GET /streets` -> count of streets (use `?full=true` for list)
- `GET /debug` -> resolved route + next pickup dates + preview list
- `GET /town.ics` -> ICS feed

## `/town.ics` usage

### Mode A: Address-driven
```text
/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886
/town.ics?street=Boston%20Road&number=65
```

### Mode B: Explicit bypass (no address required)
```text
/town.ics?weekday=Thursday&color=BLUE
/town.ics?weekday=Thursday&color=BLUE&types=trash
```

### Shared params
- `days=` number of days ahead (default 365, capped by config)
- `types=` comma list: `trash,recycling`

## Adding a New Town
1. Create `towns/<town_id>/town.yaml`.
2. Provide source URLs and parser plugin paths.
3. Add overrides:
   - `street_aliases.yaml`
   - `route_overrides.yaml`
   - `holiday_overrides.yaml`
4. Run the updater, then start the service.

## Overrides Format
`route_overrides.yaml` supports:
```yaml
add:
  - street: "Example Street"
    weekday: "Thursday"
    recycling_color: "BLUE"
    parity: "odd"
    range: [1, 99]
delete:
  - street: "Example Street"
    weekday: "Thursday"
patch:
  - street: "Example Street"
    weekday: "Thursday"
    recycling_color: "GREEN"
```

`holiday_overrides.yaml` supports:
```yaml
no_collection_dates:
  - "2025-07-04"
delay_anchor_week_sundays:
  - "2025-12-28"
```

## Development
```bash
ruff check .
pytest
```

## Postman
Import `postman/town-collection-cal.postman_collection.json`.

## Parsing and Troubleshooting
See `docs/PARSING.md`.

## Home Assistant
Add the ICS URL as a calendar source:
```
https://<host>/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886
```
