from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from town_collection_cal.common.db_model import HolidayPolicy, RouteConstraint, RouteEntry
from town_collection_cal.common.normalize import normalize_street_name

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_alias_overrides(
    aliases: dict[str, str], aliases_path: Path | None
) -> dict[str, str]:
    if not aliases_path:
        return aliases
    data = _load_yaml(aliases_path)
    if not data:
        return aliases
    if not isinstance(data, dict):
        raise ValueError(f"Alias overrides must be a mapping: {aliases_path}")
    updated = dict(aliases)
    for raw_alias, raw_target in data.items():
        alias = normalize_street_name(str(raw_alias))
        target = normalize_street_name(str(raw_target))
        updated[alias] = target
        logger.info("Alias override: %s -> %s", alias, target)
    return updated


def apply_holiday_overrides(
    holiday_policy: HolidayPolicy, overrides_path: Path | None
) -> HolidayPolicy:
    if not overrides_path:
        return holiday_policy
    data = _load_yaml(overrides_path)
    if not data:
        return holiday_policy
    if not isinstance(data, dict):
        raise ValueError(f"Holiday overrides must be a mapping: {overrides_path}")
    updated = holiday_policy.model_copy(deep=True)
    if "no_collection_dates" in data:
        updated.no_collection_dates = [date.fromisoformat(d) for d in data["no_collection_dates"]]
        logger.info("Holiday override: replaced no_collection_dates")
    if "shift_holidays" in data:
        shifts: list[date] = []
        raw = data["shift_holidays"] or []
        if not isinstance(raw, list):
            raise ValueError(f"shift_holidays must be a list: {overrides_path}")
        for entry in raw:
            if isinstance(entry, str):
                shifts.append(date.fromisoformat(entry))
            elif isinstance(entry, dict):
                if "date" not in entry:
                    raise ValueError(f"shift_holidays entry missing date: {overrides_path}")
                shifts.append(date.fromisoformat(str(entry["date"])))
            else:
                raise ValueError(
                    f"shift_holidays entry must be string or mapping: {overrides_path}"
                )
        updated.shift_holidays = shifts
        logger.info("Holiday override: replaced shift_holidays")
    return updated


@dataclass(frozen=True)
class _RouteOverrideMatch:
    street_normalized: str
    weekday: str | None
    recycling_color: str | None
    parity: str | None
    range_min: int | None
    range_max: int | None
    no_collection: bool | None


def _parse_match(entry: dict[str, Any]) -> _RouteOverrideMatch:
    street = normalize_street_name(str(entry.get("street", "")))
    if not street:
        raise ValueError("Override entry must include street")
    parity = entry.get("parity")
    range_min, range_max = None, None
    if isinstance(entry.get("range"), (list, tuple)) and len(entry["range"]) == 2:
        range_min, range_max = entry["range"]
    return _RouteOverrideMatch(
        street_normalized=street,
        weekday=entry.get("weekday"),
        recycling_color=entry.get("recycling_color"),
        parity=parity,
        range_min=range_min,
        range_max=range_max,
        no_collection=entry.get("no_collection"),
    )


def _match_route(route: RouteEntry, match: _RouteOverrideMatch) -> bool:
    if route.street_normalized != match.street_normalized:
        return False
    if match.weekday and (route.weekday or "").lower() != match.weekday.lower():
        return False
    if match.recycling_color and (route.recycling_color or "").upper() != (
        match.recycling_color.upper()
    ):
        return False
    if match.no_collection is not None and route.no_collection != match.no_collection:
        return False

    if match.parity or match.range_min is not None or match.range_max is not None:
        for constraint in route.constraints:
            if match.parity and constraint.parity != match.parity:
                continue
            if match.range_min is not None and constraint.range_min != match.range_min:
                continue
            if match.range_max is not None and constraint.range_max != match.range_max:
                continue
            return True
        return False

    return True


def _build_route(entry: dict[str, Any]) -> RouteEntry:
    street = str(entry.get("street", "")).strip()
    if not street:
        raise ValueError("Override entry must include street")
    street_normalized = normalize_street_name(street)
    constraints = []
    parity = entry.get("parity")
    range_min, range_max = None, None
    if isinstance(entry.get("range"), (list, tuple)) and len(entry["range"]) == 2:
        range_min, range_max = entry["range"]
    if parity or range_min is not None or range_max is not None:
        constraints.append(
            RouteConstraint(
                parity=str(parity) if parity else None,
                range_min=range_min,
                range_max=range_max,
            )
        )
    return RouteEntry(
        street=street,
        street_normalized=street_normalized,
        weekday=entry.get("weekday"),
        recycling_color=entry.get("recycling_color"),
        no_collection=bool(entry.get("no_collection", False)),
        constraints=constraints,
        notes=entry.get("notes"),
    )


def apply_route_overrides(
    routes: list[RouteEntry], overrides_path: Path | None
) -> list[RouteEntry]:
    if not overrides_path:
        return routes
    data = _load_yaml(overrides_path)
    if not data:
        return routes
    if not isinstance(data, dict):
        raise ValueError(f"Route overrides must be a mapping: {overrides_path}")

    updated = list(routes)

    for delete_entry in data.get("delete", []) or []:
        match = _parse_match(delete_entry)
        before = len(updated)
        updated = [r for r in updated if not _match_route(r, match)]
        removed = before - len(updated)
        logger.info("Route override delete: %s removed=%s", match.street_normalized, removed)

    for patch_entry in data.get("patch", []) or []:
        match = _parse_match(patch_entry)
        for route in updated:
            if _match_route(route, match):
                if "weekday" in patch_entry:
                    route.weekday = patch_entry["weekday"]
                if "recycling_color" in patch_entry:
                    route.recycling_color = patch_entry["recycling_color"]
                if "no_collection" in patch_entry:
                    route.no_collection = bool(patch_entry["no_collection"])
                logger.info("Route override patch: %s", match.street_normalized)

    for add_entry in data.get("add", []) or []:
        route = _build_route(add_entry)
        updated.append(route)
        logger.info("Route override add: %s", route.street_normalized)

    return updated
