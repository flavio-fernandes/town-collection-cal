from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

from town_collection_cal.common.address import parse_address
from town_collection_cal.common.db_model import Database
from town_collection_cal.common.ics import IcsEvent, build_ics
from town_collection_cal.config.loader import load_from_env
from town_collection_cal.service.db import DbLoader
from town_collection_cal.service.resolver import resolve_route
from town_collection_cal.service.schedule import generate_schedule, local_today
from town_collection_cal.updater.build_db import build_db

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config, town_dir = load_from_env()

    db_path = Path(os.getenv("DB_PATH") or f"data/generated/{config.town_id}.json").resolve()
    if not db_path.exists():
        if config.service.auto_update_on_missing_db:
            logger.info("DB missing; attempting auto-update")
            build_db(
                town_config_path=town_dir / "town.yaml",
                out_path=db_path,
                cache_dir=Path(os.getenv("CACHE_DIR") or "data/cache"),
                force_refresh=False,
                validate_only=False,
            )
        else:
            raise FileNotFoundError(f"DB file missing: {db_path}")

    db_loader = DbLoader(db_path, config.service.reload_interval_seconds)

    app = Flask(__name__)
    app.config["TOWN_CONFIG"] = config
    app.config["DB_LOADER"] = db_loader

    @app.get("/healthz")
    def healthz() -> Any:
        return jsonify({"ok": True})

    @app.get("/version")
    def version() -> Any:
        db = db_loader.get_db()
        return jsonify(
            {
                "schema_version": db.schema_version,
                "meta": db.meta.model_dump(),
            }
        )

    @app.get("/streets")
    def streets() -> Any:
        db = db_loader.get_db()
        full = request.args.get("full", "").lower() in {"1", "true", "yes"}
        if full:
            return jsonify(sorted({r.street for r in db.routes}))
        return jsonify({"count": len({r.street_normalized for r in db.routes})})

    @app.get("/debug")
    def debug() -> Any:
        db = db_loader.get_db()
        result = _resolve_request(db)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.get("/resolve")
    def resolve() -> Any:
        db = db_loader.get_db()
        result = _resolve_input(db)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    @app.get("/town.ics")
    def town_ics() -> Any:
        db = db_loader.get_db()
        result = _resolve_request(db)
        if "error" in result:
            return jsonify(result), 400

        events = _events_to_ics(
            db=db,
            events=result["events"],
            town_name=config.town_name,
        )
        calendar_name = config.ics.calendar_name_template.format(
            town_name=config.town_name, town_id=config.town_id
        )
        prodid = f"-//town-collection-cal//{config.town_id}//EN"
        ics_text = build_ics(calendar_name, events, prodid)
        return app.response_class(ics_text, mimetype="text/calendar")

    return app


def _resolve_request(db: Database) -> dict[str, Any]:
    config = _get_config()
    try:
        days = _parse_days(config)
        types = _parse_types()
    except ValueError as exc:
        return {"error": str(exc)}

    resolved = _resolve_input(db)
    if "error" in resolved:
        return resolved

    mode = resolved["mode"]
    if mode == "bypass":
        try:
            schedule = _build_schedule(
                db, days, resolved["weekday"], resolved["color"], types
            )
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            **resolved,
            "days": days,
            "types": sorted(types),
            "events": schedule,
        }

    route = resolved["route"]
    try:
        schedule = _build_schedule(
            db,
            days,
            route["weekday"],
            route.get("recycling_color"),
            types,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        **resolved,
        "days": days,
        "types": sorted(types),
        "events": schedule,
    }


def _resolve_input(db: Database) -> dict[str, Any]:
    config = _get_config()
    mode_b = bool(request.args.get("weekday")) or bool(request.args.get("color"))

    if mode_b:
        weekday = request.args.get("weekday", "")
        color = request.args.get("color", "").upper()
        if not weekday or not color:
            return {"error": "weekday and color are required for bypass mode"}
        if weekday.lower() not in {"monday", "tuesday", "wednesday", "thursday", "friday"}:
            return {"error": "weekday must be Monday-Friday"}
        if color not in {"BLUE", "GREEN"}:
            return {"error": "color must be BLUE or GREEN"}
        return {
            "mode": "bypass",
            "weekday": weekday,
            "color": color,
        }

    address = request.args.get("address")
    street = request.args.get("street")
    number = request.args.get("number")
    if address:
        parsed = parse_address(address)
        street = parsed.street_name
        number = parsed.house_number

    if not street:
        return {"error": "address or street is required"}

    number_int = int(number) if number and str(number).isdigit() else None
    resolved = resolve_route(
        db,
        street,
        number_int,
        suggestion_limit=config.resolver.suggestion_limit,
        fuzzy_threshold=config.resolver.fuzzy_threshold,
    )
    if resolved.error:
        return {
            "error": resolved.error,
            "suggestions": resolved.suggestions,
            "requires_number": resolved.requires_number,
        }
    if not resolved.route:
        return {"error": "Unable to resolve route"}
    if resolved.route.no_collection:
        return {"error": "No municipal collection for this address"}

    return {
        "mode": "address",
        "street": street,
        "number": number_int,
        "route": resolved.route.model_dump(),
    }


def _build_schedule(
    db: Database,
    days: int,
    weekday: str | None,
    color: str | None,
    types: set[str],
) -> list[dict[str, Any]]:
    if not weekday:
        raise ValueError("Resolved route missing weekday")
    start_date = local_today(_get_config().timezone)
    schedule = generate_schedule(
        start_date=start_date,
        days=days,
        trash_weekday=weekday,
        recycling_color=color if "recycling" in types else None,
        calendar_policy=db.calendar_policy,
        holiday_policy=db.holiday_policy,
    )
    normalized = []
    for event in schedule:
        kept = event.types & types
        if not kept:
            continue
        normalized.append(
            {
                "date": event.date.isoformat(),
                "types": sorted(kept),
            }
        )
    return normalized


def _events_to_ics(
    db: Database, events: list[dict[str, Any]], town_name: str
) -> list[IcsEvent]:
    ics_events: list[IcsEvent] = []
    for event in events:
        event_date = _parse_date(event["date"])
        types = set(event["types"])
        summary = _summary_for_types(town_name, types)
        uid_seed = f"{db.meta.town_id}|{'+'.join(sorted(types))}|{event_date.isoformat()}"
        ics_events.append(IcsEvent(date=event_date, summary=summary, uid_seed=uid_seed))
    return ics_events


def _summary_for_types(town_name: str, types: set[str]) -> str:
    if types == {"trash", "recycling"}:
        return f"{town_name} Trash + Recycling"
    if "recycling" in types and "trash" not in types:
        return f"{town_name} Recycling"
    return f"{town_name} Trash"


def _parse_date(value: str) -> Any:
    return datetime.fromisoformat(value).date()


def _parse_days(config: Any) -> int:
    raw = request.args.get("days")
    if not raw:
        return config.ics.default_days_ahead
    try:
        days = int(raw)
    except ValueError as exc:
        raise ValueError("days must be an integer") from exc
    if days < 1:
        raise ValueError("days must be > 0")
    return min(days, config.ics.max_days_ahead)


def _parse_types() -> set[str]:
    raw = request.args.get("types")
    if not raw:
        return {"trash", "recycling"}
    types = {t.strip().lower() for t in raw.split(",") if t.strip()}
    if not types <= {"trash", "recycling"}:
        raise ValueError("types must be trash and/or recycling")
    return types


def _get_config() -> Any:
    return current_app().config["TOWN_CONFIG"]


def current_app() -> Flask:
    from flask import current_app as flask_current_app

    return flask_current_app
