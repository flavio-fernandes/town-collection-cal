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

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        no_collection = "no municipal collection" in line.lower()
        day_match = DAY_PATTERN.search(line)
        if not day_match and not no_collection:
            continue
        day = day_match.group(1).capitalize() if day_match else None

        color_match = COLOR_PATTERN.search(line)
        color = color_match.group(1).upper() if color_match else None

        parity_match = PARITY_PATTERN.search(line)
        parity = parity_match.group(1).lower() if parity_match else None

        range_match = RANGE_PATTERN.search(line)
        range_min, range_max = None, None
        if range_match:
            range_min = int(range_match.group(1))
            range_max = int(range_match.group(2))

        street = line
        for pattern in (DAY_PATTERN, COLOR_PATTERN, PARITY_PATTERN, RANGE_PATTERN):
            street = pattern.sub(" ", street)
        street = re.sub(r"\s+", " ", street).strip(" -")

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
