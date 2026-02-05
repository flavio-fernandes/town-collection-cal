# Parsing and Troubleshooting

This document explains how the updater fetches and parses town PDFs, and how to troubleshoot parsing failures (including URL updates for new calendar years).

## How Parsing Works

1. **Load town config**
   - `towns/<town_id>/town.yaml` supplies source URLs and parser plugin paths.

2. **Download with cache**
   - `town_collection_cal.common.http_cache.fetch_with_cache` downloads the PDFs to `data/cache/`.
   - It stores ETag/Last-Modified metadata in `<filename>.meta.json`.
   - Use `--force-refresh` to bypass cache.
   - If the network fetch fails but a cached file exists, the updater will reuse the cached file.

3. **Parse PDFs**
   - The updater invokes two parsers:
     - **Routes parser**: `parsers.routes_parser` (e.g., `westford_routes:parse_routes`)
     - **Schedule parser**: `parsers.schedule_parser` (e.g., `westford_guide:parse_schedule`)
   - Each parser receives a **local file path** and the **source URL**.
   - Parsers return:
     - Parsed data
     - A structured error list (if any)

4. **Apply overrides**
   - `street_aliases.yaml`: normalize + map aliases
   - `route_overrides.yaml`: add/patch/delete routes
   - `holiday_overrides.yaml`: authoritative holiday dates/week-shifts
   - Overrides always win and are logged.

5. **Write DB**
   - Output is written atomically to `data/generated/<town_id>.json`.
   - If parsing fails, the updater does **not** overwrite the previous DB.

## Update/Run Commands

Build DB:
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache
```

Enable parser debug logging (shows matched lines and anchor info):
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache \
  --log-level DEBUG
```

Force refresh (ignore cached PDFs):
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache \
  --force-refresh
```

Validate only (no DB write):
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache \
  --validate-only
```

## Where to Inspect Inputs

After a run, check:
- `data/cache/routes.pdf`
- `data/cache/schedule.pdf`
- `data/cache/routes.pdf.meta.json`
- `data/cache/schedule.pdf.meta.json`

To inspect extracted text quickly:
```bash
python - <<'PY'
from pathlib import Path
import pdfplumber

path = Path("data/cache/routes.pdf")
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages, start=1):
        print(f"--- page {i} ---")
        print(page.extract_text() or "")
PY
```

## Common Failures and Fixes

**1) “No routes parsed”**
- PDF layout changed (columns merged, headers moved).
- Fix:
  - Inspect extracted text (see snippet above).
  - Add or patch entries in `towns/westford_ma/route_overrides.yaml`.
  - Update the parser in `src/town_collection_cal/updater/parsers/westford_routes.py`.

**2) “No anchor week found”**
- Schedule PDF text pattern changed.
- Fix:
  - Inspect extracted text.
  - Update the regex in `westford_guide.py`.
  - Or set anchor explicitly in `town.yaml` under `rules.recycling` (preferred if parser is brittle).

**3) Holiday behavior is wrong**
- Use `towns/westford_ma/holiday_overrides.yaml` as the source of truth.

**4) URL changed (e.g., 2027 guide)**
- Update `towns/westford_ma/town.yaml`:
  - `sources.routes_pdf_url`
  - `sources.schedule_pdf_url`
- Run updater with `--force-refresh`.
- Confirm the new PDFs are cached and that parsing succeeds.

## When Westford Publishes a New Guide

1. Find the new URLs on the Westford site.
2. Update `towns/westford_ma/town.yaml`.
3. Run the updater with `--force-refresh`.
4. If parsing fails:
   - Add overrides for the failing entries.
   - Update parser patterns as needed.
5. Update `holiday_overrides.yaml` for the new year.
