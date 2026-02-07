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

## Website (Frontend)
The repository now includes a static web app in `web/` that helps residents generate subscription URLs without exposing addresses in the final URL.

Quick start:
```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Recommended full local stack:
```bash
docker compose up --build
```

Then open:
- Web UI: `http://localhost:5173`
- Backend API is reachable through the web dev server proxy on the same origin (`http://localhost:5173`).

Port-conflict options:
- Change web host port:
  - `HOST_WEB_PORT=5180 docker compose up --build`
- Expose backend directly on host only when needed:
  - `docker compose -f docker-compose.yml -f docker-compose.backend-host.yml up --build`
- Change direct backend host port:
  - `HOST_BACKEND_PORT=5001 docker compose -f docker-compose.yml -f docker-compose.backend-host.yml up --build`

## Endpoints
- `GET /healthz` -> `{ ok: true }`
- `GET /version` -> service version + DB meta + schema version
- `GET /streets` -> count of streets (use `?full=true` for list)
- `GET /debug` -> resolved route + next pickup dates + preview list
- `GET /town.ics` -> ICS feed
- `GET /resolve` -> resolve address/route without generating schedule

## `/town.ics` usage

### Mode A: Address-driven
```text
/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886
/town.ics?street=Boston%20Road&number=65
```

Resolve-only:
```text
/resolve?street=Boston%20Road&number=65
```

### Mode B: Explicit bypass (no address required)
```text
/town.ics?weekday=Thursday&color=BLUE
/town.ics?weekday=Thursday&color=BLUE&types=trash
```

Website behavior note:
- the UI always emits Mode B subscription URLs (privacy-friendly).
- address inputs are only used for route resolution and preview.

### Shared params
- `days=` number of days ahead (default 365, capped by config)
- `types=` comma list: `trash,recycling`

## Adding a New Town
1. Create `towns/<town_id>/town.yaml`.
2. Provide source URLs and parser plugin paths.
3. Add overrides:
   - `street_aliases.yaml`
   - `route_overrides.yaml`
   - `holiday_rules.yaml`
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

`holiday_rules.yaml` supports:
```yaml
no_collection_dates:
  - "2025-07-04"
shift_holidays:
  - "2025-07-04"
  - "2025-09-01"
  - "2025-12-25"
```

## Development
```bash
ruff check .
pytest
```

Unified workflow via `make` (recommended):
```bash
make bootstrap-py
make bootstrap-web
make check
```

Other useful targets:
- `make test-py`
- `make test-web`
- `make build-web`
- `make audit-py`
- `make audit-web`
- `make help`

## Sanity Check
```bash
make sanity
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
