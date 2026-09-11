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
   - This is PDF text extraction, not OCR. Westford's circled holiday dates and colored
     calendar cells are not automatically extracted. Holiday review is a manual step.
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
   - `holiday_rules.yaml`: authoritative holiday dates/week-shifts and reviewed coverage
   - Overrides always win and are logged.

5. **Write DB**
   - Westford's holiday file binds the review to the PDF's SHA256 and coverage dates.
     A changed PDF or expired review fails the build before replacing the previous DB.
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
- Use `towns/westford_ma/holiday_rules.yaml` as the source of truth.
- For date-based shifts, add entries under `shift_holidays`.
- Do not put a delayed holiday in `no_collection_dates`: that skips the pickup entirely.
- Daily refreshes do not discover holiday changes. Review the actual calendar page:
  circles mean delays; triangles are special collection events, not delays.
- The service caps calendar events at `valid_through`; after expiration `/healthz`
  returns 503 and calendar requests fail rather than inventing future pickup dates.
- `/version` exposes `schedule_review` as well as the DB generation timestamp. Monitor
  updater failures and the generation timestamp; a working API alone does not prove
  that the daily updater is running. A successful refresh may still use cached PDFs
  after a network failure, which is logged as a warning.

**4) URL changed (e.g., 2027 guide)**
- Update `towns/westford_ma/town.yaml`:
  - `sources.routes_pdf_url`
  - `sources.schedule_pdf_url`
- Run updater with `--force-refresh`.
- Confirm the new PDFs are cached and that parsing succeeds.

## When Westford Publishes a New Guide

1. Find the new URLs on the Westford site.
2. Update `towns/westford_ma/town.yaml`.
3. Download/render the new guide and visually review all months, week colors, and holidays.
   Set the new `shift_holidays`, `valid_from`, and `valid_through` in `holiday_rules.yaml`.
   Only after that review, set `reviewed_source_sha256` to the SHA256 of the downloaded PDF.
   Use `shasum -a 256 <downloaded-guide.pdf>` on macOS or `sha256sum` on Linux.
4. Run the updater with `--force-refresh`.
5. If parsing fails:
   - Add overrides for the failing entries.
   - Update parser patterns as needed.
6. Update the regression fixture and verify holiday weeks before and after the cutoff,
   Saturday pickups, and the final covered date. Run `pytest` and `ruff check .`.
7. Deploy both the application and the town configuration. The VPS bind-mounts
   `/opt/town-collection-cal/towns`; a new image alone does not replace these host files.
8. Rebuild the production DB and verify `/version`, `/debug`, and `/town.ics` publicly.
   Check the systemd updater timer and its last successful run.

The July 2026-June 2027 review and regression fixture provenance are recorded in
[`WESTFORD_2026_2027_REVIEW.md`](WESTFORD_2026_2027_REVIEW.md).
