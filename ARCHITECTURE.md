# Architecture -- town-collection-cal

Repo: https://github.com/flavio-fernandes/town-collection-cal

Goal: provide an iCalendar (ICS) feed for trash + recycling pickup dates for a town, using a two-phase design:
1) Ingest town source documents and build a local database (source of truth)
2) Serve ICS and debug endpoints using that database

Initial target: Westford, MA (but the repo must be town-agnostic and configurable)

References (Westford):
- Routes by street name PDF: https://westfordma.gov/DocumentCenter/View/2949/Trash-and-Recycling-Routes-by-Street-Name-PDF
- Recycling guide PDF (contains blue/green pattern and holidays): https://westfordma.gov/DocumentCenter/View/16672/Recycling-Guide-2025-2026


## Non-goals
- Do not rely on scraping fragile HTML pages (unless a town has no better option).
- Do not embed a single address or a single street in code.
- Do not require Home Assistant specific code inside the service. Home Assistant will consume the ICS URL.


## High-level user stories
1) As a resident, I can pass my full address and get an ICS that contains:
   - Trash pickup dates
   - Recycling pickup dates
2) As a power user, I can bypass address resolution and explicitly specify my recycling color (BLUE/GREEN) and pickup weekday, to build an ICS without street mapping.
3) As a developer, I can clone this repo for another town, change configuration files (not code), and have the same service for that town.
4) As an operator, I can run this with Docker and/or a simple venv and a cron-style updater.
5) As a maintainer, I can patch parsing changes and edge cases via data overrides, not code edits.


## Design principles
- Two-part architecture: updater (build DB) and service (serve DB).
- Config-driven: all town-specific behavior must live in configuration, data, or plugins.
- Minimize hardcoding: URLs, rules, timezone, names, and special cases should come from config.
- Data-first overrides: when parsing is brittle, store corrections in YAML overrides.
- Deterministic outputs: the same DB and inputs produce the same ICS.
- Testability: unit tests for parsing, resolution, scheduling, ICS formatting, and config validation.
- “Future proof”: explicit versioning of DB schema and metadata, safe defaults, compatibility checks.
- Validate all config and DB inputs before use, with flexible defaults where reasonable.


## Repo layout (proposed)
```
.
├── README.md
├── ARCHITECTURE.md                 <-- this document (or docs/ARCHITECTURE.md)
├── pyproject.toml
├── src/
│   └── town_collection_cal/
│       ├── common/
│       │   ├── address.py           (address parsing helpers)
│       │   ├── normalize.py         (street normalization)
│       │   ├── http_cache.py        (ETag/Last-Modified fetch + sha)
│       │   └── ics.py               (ICS building utilities)
│       ├── config/
│       │   ├── schema.py            (pydantic config models)
│       │   └── loader.py            (load config from file/env)
│       ├── updater/
│       │   ├── __main__.py          (CLI: build-db)
│       │   ├── build_db.py          (orchestrator)
│       │   ├── parsers/
│       │   │   ├── westford_routes.py   (parser plugin example)
│       │   │   └── westford_guide.py    (parser plugin example)
│       │   └── overrides.py         (merge overrides into parsed results)
│       └── service/
│           ├── app.py               (Flask app factory)
│           ├── db.py                (load + validate DB)
│           ├── resolver.py          (address -> route mapping)
│           └── schedule.py          (compute pickup events)
├── towns/
│   └── westford_ma/
│       ├── town.yaml                (town config)
│       ├── holiday_rules.yaml       (holiday weeks/dates overrides)
│       ├── street_aliases.yaml      (alias mapping)
│       └── route_overrides.yaml     (manual route patches)
├── data/
│   ├── cache/                       (download cache)
│   └── generated/                   (DB output directory)
├── scripts/
│   ├── run_dev.sh
│   └── update_db.sh
└── tests/
    ├── test_config.py
    ├── test_resolver.py
    ├── test_schedule.py
    ├── test_ics.py
    └── parsers/
        ├── test_westford_routes.py
        └── test_westford_guide.py
```

Notes:
- Everything under `towns/<town_id>/` is expected to be editable by another town.
- The Westford parsers can be the default example plugins.


## Configuration model
Configuration should be a YAML file per town, validated with pydantic.
Example: `towns/westford_ma/town.yaml`

Key ideas:
- The service should load a town config by `TOWN_ID` and/or `TOWN_CONFIG_PATH`.
- Minimal required config:
  - Town name
  - Timezone
  - Source URLs (routes and schedule/guide)
  - Parser plugin names
  - ICS output defaults (days ahead)
  - Rule model (recycling cadence definition, holiday rules)
  - Global defaults should be supported (with town overrides where needed)

Suggested config fields (sketch):
- `town_id`: string (e.g., `westford_ma`)
- `town_name`: string
- `timezone`: string (IANA)
- `sources`:
  - `routes_pdf_url`: string
  - `schedule_pdf_url`: string
- `parsers`:
  - `routes_parser`: dotted import path or known plugin id
  - `schedule_parser`: dotted import path or known plugin id
- `ics`:
  - `calendar_name_template`: string (supports tokens)
  - `default_days_ahead`: int (global default: 365)
  - `max_days_ahead`: int
- `rules`:
  - `recycling`:
    - `mode`: `alternating_week` | `fixed_dates` | `none`
    - if `alternating_week`:
      - `anchor_week_sunday`: date
      - `anchor_color`: BLUE|GREEN
  - `holidays`:
    - `policy_mode`: `yaml_overrides` | `parser_extracted`
    - `no_collection_dates`: optional
    - `shift_holidays`: optional list of holiday dates
- `overrides_paths`:
  - `holiday_rules_yaml`
  - `street_aliases_yaml`
  - `route_overrides_yaml`

Why config validation matters:
- Another town should be able to adjust YAML and get immediate, clear errors on startup if something is missing or invalid.
- Validation should be flexible and provide safe defaults when fields are omitted, but must always run before use.
- Prefer Pydantic models and validation only (no separate JSON Schema artifacts).


## Database (DB) output model
The updater writes a JSON DB file (source of truth for the service).

DB should include:
- `schema_version`
- `meta`:
  - `generated_at`
  - `town_id`
  - `sources` (URLs + sha256 of fetched files)
  - optional: git commit hash of generator version
- `calendar_policy`:
  - anchor data and any rule info needed at runtime
- `holiday_policy`:
  - `no_collection_dates`: dates that are skipped entirely
  - `shift_holidays`: dates that shift pickups on/after the holiday by +1 day
- `aliases`:
  - normalized alias mappings
- `routes`:
  - one or more entries per street
  - include constraints (parity/range) and flags
- optional: `street_index` to speed up lookups

The DB must be stable enough to allow:
- building the DB offline
- running the service purely from the DB without network access


## Part 1 -- Updater details

### Responsibilities
- Download source documents (PDFs) with caching.
- Parse them via a town-specific parser plugin.
- Merge town overrides (YAML).
- Produce a validated DB.
- Write DB outputs atomically (temp file then replace) to avoid clobbering a good DB.

### Parser plugin interface
- There are two separate parsers per town: a routes parser and a schedule parser.
- Parsers receive file paths and source URLs (not just raw bytes).
- Parsers return structured outputs plus a structured error list (not just exceptions).
- Parsing failures must not disrupt the previously generated DB:
  - do not overwrite the existing DB on failure
  - log errors clearly for diagnosis

### Caching
`http_cache` should store:
- content file (e.g., routes.pdf)
- metadata file with ETag/Last-Modified
- sha256 digest for auditability

### Parsing strategy (Westford example)
- Routes PDF:
  - Extract street rows containing: street name, collection weekday, recycling week color (blue/green/tba)
  - Handle cases like:
    - even#/odd# parity
    - range blocks (# 1-99)
    - “no municipal collection”
    - multi-entry lines when PDF text extraction merges columns
- Guide PDF:
  - Extract rule text that defines an anchor:
    - “week of <Month> <d1>-<d2> is BLUE/GREEN”
  - Determine anchor Sunday for that week
  - Store anchor in DB

### Known brittle area: holidays
The printed “O” marker (or similar) used in calendar grids often does not survive text extraction.
Therefore:
- default to `holiday_rules.yaml` for correctness
- allow future enhancement where a parser extracts holiday data more reliably if feasible

### Overrides
- `street_aliases.yaml`: normalize and map input variants to canonical streets
- `route_overrides.yaml`: add or patch route rows if parsing breaks due to PDF formatting
- `holiday_rules.yaml`: keep holiday behavior correct across seasons
Rules:
- Overrides always win.
- Overrides must support deletion of parsed entries.
- All override applications must be clearly logged.

### Updater CLI
Required command:
- `python -m town_collection_cal.updater build-db --town towns/westford_ma/town.yaml --out data/generated/westford_ma.json`

Optional flags:
- `--cache-dir`
- `--force-refresh`
- `--validate-only`


## Part 2 -- Service details

### Responsibilities
- Load DB and config on startup
- Provide an ICS endpoint
- Provide debug and introspection endpoints
- Handle address-based resolution OR explicit bypass options
Additional service behavior:
- If the DB is missing, treat it as a fatal error and halt (unless auto-update is explicitly enabled).
- Cache the DB in memory and support live reload.
  - Live reload should use file mtime polling on an interval that is safe for performance (default >= 10s, configurable).

### Endpoints (required)
- `GET /healthz` -> `{ ok: true }`
- `GET /version` -> DB meta + schema version
- `GET /streets` -> list of known streets or a count (for troubleshooting)
- `GET /debug` -> resolved route + next pickup dates + preview list
- `GET /town.ics` (or `GET /collection.ics`) -> the actual ICS feed

### Core endpoint: `GET /town.ics`
Must support two input modes:

Mode A (address-driven):
- Query params:
  - `address=` full address string OR `street=` and `number=`
- The service resolves:
  - weekday (trash) and recycling color from routes DB
  - then generates events

Mode B (explicit bypass, no address required):
- Query params:
  - `color=BLUE|GREEN` (explicit recycling color for the route)
  - `weekday=Monday|Tuesday|Wednesday|Thursday|Friday` (trash pickup weekday)
  - Optional: `types=` `trash,recycling` (default both)
  - Optional: `days=` bounded by config
- In this mode:
  - no street resolution is needed
  - useful if the user already knows their color/day, or if the town has no street mapping

Important:
- Mode B must still use the town’s recycling cadence rule (anchor week) from the DB/config.
- Mode B should be well documented as “advanced usage”.

Additional params (both modes):
- `days=` (default from config, bounded by max)
- `types=` comma list `trash,recycling`

Error handling requirements:
- Clear 4xx errors with actionable messages.
- If address resolution fails:
  - include suggestions (fuzzy match list)
  - indicate when a street requires a number due to multiple routes

### Address resolution
- Parse using `usaddress` (best effort)
- Normalize street with a deterministic normalizer
- Provide a common default normalization set (suffix expansion, punctuation, directionals).
- Make normalization logic easy to update or extend later.
- Apply `street_aliases` mapping
- Match exact normalized key in routes
- Apply range/parity constraints if present
- If no match, return suggestions (RapidFuzz) but do not silently pick wrong streets
- Return top 10 suggestions by default; make the count configurable and documented.
- Use a reasonable default similarity threshold (e.g., 85); keep it configurable and documented.

### Event generation rules
- For each week within `[today, today + days]`:
  - Determine trash day (weekday)
  - Determine recycling day if week color matches route color
- Holiday rules:
  - If “no pickup day”, skip (highest priority).
  - Otherwise if a week contains a holiday shift date for this route color, shift pickups on or after that holiday date by +1 day.
  - If multiple holidays are in the same week, use the earliest date (no cascading).
  - Allow Friday pickups to shift to Saturday; do not carry into the next week.
- Events must be all-day (`VALUE=DATE`) and timezone-safe
Other rules:
- Recycling week definition uses US Sunday-week semantics (week starts on Sunday).
- “today” is local timezone midnight.

### ICS output requirements
- RFC 5545 friendly formatting
- Stable UID generation (seeded by type + date + town id)
- `X-WR-CALNAME` should be configurable
- `PRODID` should identify this project and optionally town id
Additional ICS rules:
- Event summary should be `${TOWN} Trash` or `${TOWN} Recycling` (town name from config).
- If trash and recycling fall on the same date, merge into a single event for that date.
- Merged event summary should be `${TOWN} Trash + Recycling`.
- No required `DESCRIPTION`, `LOCATION`, or `CATEGORIES` fields.


## Agent in the cloud (for Home Assistant usage)

### Why
Home Assistant HACS integrations (like waste_collection_schedule) often need either:
- a native scraper implementation per town, or
- a stable URL that provides schedule data (ICS is ideal)

This repo provides the stable URL for the town as:
- `https://<host>/town.ics?...`

### Recommended deployment model
- Run this service as a small container on a VPS, home server, or a cloud function style environment.

Options:
1) Docker container (simplest)
2) Cloud Run / ECS / any container platform
3) Minimal VM with systemd

Updater options:
- Run updater on container start (simple, but updates only on restarts)
- Run updater via a scheduled job:
  - cron on the host
  - GitHub Actions + commit new DB artifacts (if desired)
  - scheduled Cloud Run job / Lambda / etc.

Configuration:
- mount `towns/<town_id>/` as config volume
- set env:
  - `TOWN_ID=westford_ma`
  - `TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml`
  - `DB_PATH=/app/data/generated/westford_ma.json`

Service start logic:
- if DB missing, fail with a clear message (fatal) unless auto-update is explicitly enabled


## Integration with HACS waste_collection_schedule
- This repo’s output is ICS, which Home Assistant can ingest using:
  - the built-in Calendar integration (URL-based calendar), or
  - waste_collection_schedule’s ICS source (if available), or
  - a thin custom source adapter that reads from the ICS URL

If waste_collection_schedule does not support ICS directly for the desired features:
- Provide a minimal “adapter” mode:
  - `GET /schedule.json` returning a simple list of upcoming events
  - Keep ICS as the primary output, JSON as optional


## Security and privacy
- The service should not store user addresses permanently.
- Logs must avoid printing full address by default (or redact house numbers).
- Rate limiting is optional but recommended if exposed publicly.
- If used internally only, protect via reverse proxy auth or network ACLs.


## Testing strategy (required)
Unit tests:
- Config validation:
  - missing fields
  - invalid enums (weekday, color)
  - invalid URLs
- Normalization:
  - “Boston Rd” == “Boston Road”
- Resolver:
  - exact match
  - alias match
  - parity match
  - range match
  - requires number case
  - suggestions on miss
- Schedule:
  - alternating week calculation from anchor
  - trash weekly generation
  - recycling week filtering
  - holiday overrides apply shift and skip
- ICS:
  - basic correctness: headers, VEVENT, DTSTART/DTEND, UID stability

Parser tests:
- Use fixtures (small PDF snippets if possible) or snapshot text extraction.
- At minimum:
  - westford_routes parser handles representative rows and tricky patterns
  - westford_guide parser extracts anchor consistently

CI:
- GitHub Actions: run ruff + pytest on PRs and pushes to main

Documentation tests:
- Smoke test instructions should be runnable in CI (optional but nice):
  - build DB
  - start server
  - curl endpoints


## Documentation requirements
README must include:
- What the project is
- How to run locally (venv)
- How to run with Docker
- How to update the DB
- How to call endpoints (examples)
- How to add a new town:
  - create `towns/<town_id>/town.yaml`
  - provide source URLs
  - choose an existing parser plugin or implement a new parser module
  - run updater, then run service
- Home Assistant usage:
  - how to add the ICS URL as a calendar
  - example URL with query params for both modes

Town config docs:
- `towns/westford_ma/` should have comments in YAML and maybe a short `README.md` explaining:
  - where URLs came from
  - what overrides do
  - expected update cadence


## Open questions / planned enhancements
- Holiday extraction:
  - if a town provides a structured list of holiday impacts, prefer that
  - otherwise keep `holiday_rules.yaml` as the canonical method
- Support towns that do not use alternating blue/green:
  - `fixed_dates` mode where the schedule parser provides explicit recycling dates
- Add `GET /resolve` endpoint returning route details without schedule (optional)
- Add `GET /schedule.json` (optional) for easy client consumption
- TODO: Non-PDF source types (CSV/HTML) when a real need arises


## Implementation checklist for Codex
1) Create the repo skeleton and packaging (`pyproject.toml`, src layout).
2) Implement config schema (pydantic) and loader.
3) Implement http cache fetcher with sha.
4) Implement DB schema and validator.
5) Implement updater CLI:
   - load config
   - fetch sources
   - call parser plugins
   - merge overrides
   - write DB
6) Implement Flask service:
   - load config + DB
   - implement endpoints
   - implement both input modes for `/town.ics`
7) Implement tests + CI
8) Write docs in the repo style of cafe-hass:
   - clean, practical, copy-paste friendly
   - minimal magic
   - “how to extend” section is first-class


## API examples (target)
Address-driven:
- `/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886`
- `/debug?address=3%20Boston%20Road,%20Westford,%20MA%2001886`

Street-driven:
- `/town.ics?street=Boston%20Road&number=65`

Explicit bypass:
- `/town.ics?weekday=Thursday&color=BLUE`
- `/town.ics?weekday=Thursday&color=BLUE&types=trash`
- `/debug?weekday=Thursday&color=BLUE`

All requests can include:
- `days=120` (bounded by config)


## Quality bar
- Prefer correctness over clever scraping.
- Prefer explicit errors over silent wrong answers.
- Prefer config + data overrides over code edits.
- Prefer small, composable modules with tests.
- Document everything a new town would need to change, step by step.


## Codex prompt (short)
You are Codex working inside this repo: https://github.com/flavio-fernandes/town-collection-cal

Implement a town-agnostic Flask service that publishes an iCalendar (ICS) feed for trash + recycling pickup dates.
Use a 2-part design:
- Updater: downloads and parses town source documents, merges YAML overrides, and writes a validated JSON database.
- Service: loads the JSON DB and serves ICS + debug endpoints.

Requirements:
1) Make the project config-driven. All town specifics must be in `towns/<town_id>/` and validated via pydantic.
2) Implement the main endpoint `/town.ics` supporting 2 modes:
   - Mode A: resolve from `address=` (or `street=` + `number=`) using the routes mapping in the DB.
   - Mode B: bypass address and accept explicit `weekday=` and `color=BLUE|GREEN` to generate an ICS without street mapping.
3) Keep parsing robust:
   - Cache downloads (ETag/Last-Modified) and store sha256 in DB metadata.
   - Prefer YAML overrides for brittle items (especially holidays).
4) Provide endpoints: `/healthz`, `/version`, `/streets`, `/debug`, `/town.ics`.
5) Provide clean docs and tests. Add GitHub Actions CI running ruff + pytest.
6) Match the style quality bar of https://github.com/flavio-fernandes/cafe-hass:
   - clear README, step-by-step setup, minimal magic, and practical examples.

Initial town implementation:
- Add `towns/westford_ma/` with `town.yaml` plus overrides placeholders.
- Implement Westford parsers for:
  - Routes PDF: https://westfordma.gov/DocumentCenter/View/2949/Trash-and-Recycling-Routes-by-Street-Name-PDF
  - Recycling guide PDF: https://westfordma.gov/DocumentCenter/View/16672/Recycling-Guide-2025-2026
- Make it easy for another town to clone by only editing config and override files.

Deliverables:
- Repo skeleton + Python package + CLI updater + Flask app + tests + docs.
- Ensure all behavior is documented and tested, with guard clauses for edge cases.
