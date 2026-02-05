from __future__ import annotations

import argparse
import logging
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from town_collection_cal.common.db_model import (
    SCHEMA_VERSION,
    CalendarPolicy,
    Database,
    HolidayPolicy,
    MetaInfo,
    RouteEntry,
    SourceMeta,
)
from town_collection_cal.common.http_cache import fetch_with_cache
from town_collection_cal.common.normalize import normalize_street_name
from town_collection_cal.config.loader import load_town_config
from town_collection_cal.updater.overrides import (
    apply_alias_overrides,
    apply_holiday_overrides,
    apply_route_overrides,
)
from town_collection_cal.updater.parsers.types import RoutesParseResult, ScheduleParseResult

logger = logging.getLogger(__name__)


def _load_callable(path: str) -> Callable[..., Any]:
    if ":" not in path:
        raise ValueError(f"Parser must be in module:function format: {path}")
    module_name, func_name = path.split(":", 1)
    module = import_module(module_name)
    func = getattr(module, func_name)
    if not callable(func):
        raise ValueError(f"Parser target is not callable: {path}")
    return func


def _git_commit() -> str | None:
    if env_commit := os.getenv("GIT_COMMIT"):
        return env_commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _build_street_index(routes: list[RouteEntry]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for idx, route in enumerate(routes):
        index.setdefault(route.street_normalized, []).append(idx)
    return index


def _coerce_calendar_policy(
    config_rules: Any, schedule_result: ScheduleParseResult
) -> CalendarPolicy:
    config_recycling = config_rules.recycling
    mode = config_recycling.mode.value
    anchor_sunday = (
        config_recycling.anchor_week_sunday
        or schedule_result.calendar_policy.anchor_week_sunday
    )
    anchor_color = (
        config_recycling.anchor_color or schedule_result.calendar_policy.anchor_color
    )
    return CalendarPolicy(
        recycling_mode=mode,
        anchor_week_sunday=anchor_sunday,
        anchor_color=anchor_color,
    )


def _coerce_holiday_policy(
    config_rules: Any, schedule_result: ScheduleParseResult
) -> HolidayPolicy:
    holidays = config_rules.holidays
    no_collection = list(holidays.no_collection_dates) or list(
        schedule_result.holiday_policy.no_collection_dates
    )
    delay_weeks = list(holidays.delay_anchor_week_sundays) or list(
        schedule_result.holiday_policy.delay_anchor_week_sundays
    )
    return HolidayPolicy(
        no_collection_dates=no_collection,
        delay_anchor_week_sundays=delay_weeks,
        shift_by_one_day=holidays.shift_by_one_day,
    )


def _resolve_override_path(town_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    return (town_dir / value).resolve()


def build_db(
    town_config_path: Path,
    out_path: Path,
    cache_dir: Path,
    *,
    force_refresh: bool = False,
    validate_only: bool = False,
) -> Database:
    config, town_dir = load_town_config(town_config_path)

    cache_dir = cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    routes_cache = fetch_with_cache(
        config.sources.routes_pdf_url,
        cache_dir,
        "routes.pdf",
        force_refresh=force_refresh,
    )
    schedule_cache = fetch_with_cache(
        config.sources.schedule_pdf_url,
        cache_dir,
        "schedule.pdf",
        force_refresh=force_refresh,
    )

    routes_parser = _load_callable(config.parsers.routes_parser)
    schedule_parser = _load_callable(config.parsers.schedule_parser)

    routes_result: RoutesParseResult = routes_parser(routes_cache.path, routes_cache.url)
    schedule_result: ScheduleParseResult = schedule_parser(schedule_cache.path, schedule_cache.url)

    parser_errors = list(routes_result.errors) + list(schedule_result.errors)
    if parser_errors:
        msg = "Parsing errors:\n" + "\n".join(f"- {e}" for e in parser_errors)
        logger.error(msg)
        raise ValueError(msg)

    alias_path = _resolve_override_path(
        town_dir, config.overrides_paths.street_aliases_yaml
    )
    holiday_path = _resolve_override_path(
        town_dir, config.overrides_paths.holiday_overrides_yaml
    )
    route_overrides_path = _resolve_override_path(
        town_dir, config.overrides_paths.route_overrides_yaml
    )

    aliases = apply_alias_overrides({}, alias_path)
    holiday_policy = _coerce_holiday_policy(config.rules, schedule_result)
    holiday_policy = apply_holiday_overrides(holiday_policy, holiday_path)

    routes = apply_route_overrides(routes_result.routes, route_overrides_path)

    calendar_policy = _coerce_calendar_policy(config.rules, schedule_result)
    if calendar_policy.recycling_mode == "alternating_week":
        if not calendar_policy.anchor_week_sunday or not calendar_policy.anchor_color:
            raise ValueError("Missing anchor data for alternating_week recycling mode")

    # Ensure street_normalized is present and aligned
    for route in routes:
        route.street_normalized = normalize_street_name(route.street)

    db = Database(
        schema_version=SCHEMA_VERSION,
        meta=MetaInfo(
            generated_at=datetime.now(UTC),
            town_id=config.town_id,
            sources={
                "routes": SourceMeta(
                    url=routes_cache.url,
                    sha256=routes_cache.sha256,
                    etag=routes_cache.etag,
                    last_modified=routes_cache.last_modified,
                ),
                "schedule": SourceMeta(
                    url=schedule_cache.url,
                    sha256=schedule_cache.sha256,
                    etag=schedule_cache.etag,
                    last_modified=schedule_cache.last_modified,
                ),
            },
            git_commit=_git_commit(),
        ),
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
        aliases=aliases,
        routes=routes,
        street_index=_build_street_index(routes),
    )

    if validate_only:
        return db

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(db.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(out_path)
    logger.info("DB written to %s", out_path)
    return db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build town collection DB")
    parser.add_argument("--town", required=True, help="Path to town.yaml")
    parser.add_argument("--out", required=True, help="Output DB JSON path")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--force-refresh", action="store_true", help="Force re-download sources")
    parser.add_argument("--validate-only", action="store_true", help="Validate only, no output")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")

    build_db(
        Path(args.town),
        Path(args.out),
        Path(args.cache_dir),
        force_refresh=args.force_refresh,
        validate_only=args.validate_only,
    )
    return 0
