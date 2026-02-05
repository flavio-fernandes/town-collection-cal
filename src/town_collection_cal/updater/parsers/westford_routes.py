from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from town_collection_cal.common.db_model import RouteConstraint, RouteEntry
from town_collection_cal.common.normalize import normalize_street_name
from town_collection_cal.updater.parsers.types import RoutesParseResult

DAY_PATTERN = re.compile(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday)\b", re.IGNORECASE)
COLOR_PATTERN = re.compile(r"\b(BLUE|GREEN|TBA)\b", re.IGNORECASE)
PARITY_PATTERN = re.compile(r"\b(ODD|EVEN)\b", re.IGNORECASE)
RANGE_PATTERN = re.compile(r"\b(\d{1,5})\s*-\s*(\d{1,5})\b")

logger = logging.getLogger(__name__)


def _extract_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")
    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def parse_routes(path: str | Path, url: str) -> RoutesParseResult:
    path = Path(path)
    text = _extract_text(path)
    routes: list[RouteEntry] = []
    errors: list[str] = []
    pending_street: str | None = None
    pending_range: tuple[int | None, int | None] | None = None
    pending_parity: str | None = None

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        no_collection = "no municipal collection" in line.lower()
        day_match = DAY_PATTERN.search(line)
        if not day_match and not no_collection:
            # Possible continuation (street-only line)
            if not COLOR_PATTERN.search(line):
                street_only = _clean_street(line)
                if street_only:
                    pending_street = street_only
                    pending_range = _extract_range(line)
                    pending_parity = _extract_parity(line)
            continue
        day = day_match.group(1).capitalize() if day_match else None

        color_match = COLOR_PATTERN.search(line)
        color = color_match.group(1).upper() if color_match else None

        parity = _extract_parity(line)

        range_min, range_max = _extract_range(line)

        street = _clean_street(line)
        if not street and pending_street:
            street = pending_street
            if pending_range and (range_min is None and range_max is None):
                range_min, range_max = pending_range
            if pending_parity and not parity:
                parity = pending_parity
            pending_range = None
            pending_parity = None
        elif street:
            pending_street = None
            pending_range = None
            pending_parity = None

        if not street:
            continue

        constraints = []
        if parity or range_min is not None or range_max is not None:
            constraints.append(
                RouteConstraint(
                    parity=parity,
                    range_min=range_min,
                    range_max=range_max,
                )
            )

        route = RouteEntry(
            street=street,
            street_normalized=normalize_street_name(street),
            weekday=day,
            recycling_color=color,
            no_collection=no_collection,
            constraints=constraints,
            notes=None,
        )
        routes.append(route)
        logger.debug(
            "Parsed route line=%r street=%s weekday=%s color=%s parity=%s range=%s-%s",
            raw_line,
            route.street,
            route.weekday,
            route.recycling_color,
            parity,
            range_min,
            range_max,
        )

    if not routes:
        errors.append(f"No routes parsed from {url}")

    return RoutesParseResult(routes=routes, errors=errors)


def _extract_range(line: str) -> tuple[int | None, int | None]:
    range_match = RANGE_PATTERN.search(line)
    if not range_match:
        return None, None
    return int(range_match.group(1)), int(range_match.group(2))


def _extract_parity(line: str) -> str | None:
    parity_match = PARITY_PATTERN.search(line)
    return parity_match.group(1).lower() if parity_match else None


def _clean_street(line: str) -> str:
    street = line
    for pattern in (DAY_PATTERN, COLOR_PATTERN, PARITY_PATTERN, RANGE_PATTERN):
        street = pattern.sub(" ", street)
    street = re.sub(r"\s+", " ", street).strip(" -")
    street = street.replace(".", "")
    if street.strip() in {"#", ""}:
        return ""
    if street.replace("#", "").strip().isdigit():
        return ""
    return _fix_directional_prefix(street)


def _fix_directional_prefix(street: str) -> str:
    tokens = street.split()
    if len(tokens) < 2:
        return street
    prefix = tokens[0].lower()
    mapping = {
        "n": "North",
        "s": "South",
        "e": "East",
        "w": "West",
        "no": "North",
        "so": "South",
        "ea": "East",
        "we": "West",
        "ne": "Northeast",
        "nw": "Northwest",
        "se": "Southeast",
        "sw": "Southwest",
    }
    if prefix == "no" and tokens[1].lower() == "name":
        return street
    if prefix in mapping:
        return " ".join([mapping[prefix], *tokens[1:]])
    return street
