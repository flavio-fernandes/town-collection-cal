from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path

import pdfplumber

from town_collection_cal.common.db_model import CalendarPolicy, HolidayPolicy
from town_collection_cal.updater.parsers.types import ScheduleParseResult

ANCHOR_PATTERN = re.compile(
    r"week of\s+([A-Za-z]+)\s+(\d{1,2})\s*-\s*(\d{1,2}).*?\b(BLUE|GREEN)\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

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


def _infer_year(text: str) -> int:
    years = [int(y) for y in YEAR_PATTERN.findall(text)]
    if years:
        return min(years)
    return datetime.now().year


def _anchor_sunday(some_day: date) -> date:
    offset = (some_day.weekday() + 1) % 7
    return some_day.fromordinal(some_day.toordinal() - offset)


def parse_schedule(path: str | Path, url: str) -> ScheduleParseResult:
    path = Path(path)
    text = _extract_text(path)
    errors: list[str] = []

    match = ANCHOR_PATTERN.search(text)
    if not match:
        errors.append(f"No anchor week found in {url}")
        calendar_policy = CalendarPolicy(recycling_mode="alternating_week")
        holiday_policy = HolidayPolicy()
        return ScheduleParseResult(
            calendar_policy=calendar_policy, holiday_policy=holiday_policy, errors=errors
        )

    month_name = match.group(1)
    day_start = int(match.group(2))
    color = match.group(4).upper()

    year = _infer_year(text)
    anchor_date = date.fromisoformat(f"{year}-{_month_number(month_name):02d}-{day_start:02d}")
    anchor_sunday = _anchor_sunday(anchor_date)
    logger.debug(
        "Parsed anchor week from %s: month=%s day=%s color=%s anchor_sunday=%s",
        url,
        month_name,
        day_start,
        color,
        anchor_sunday.isoformat(),
    )

    calendar_policy = CalendarPolicy(
        recycling_mode="alternating_week",
        anchor_week_sunday=anchor_sunday,
        anchor_color=color,
    )
    holiday_policy = HolidayPolicy()
    return ScheduleParseResult(
        calendar_policy=calendar_policy, holiday_policy=holiday_policy, errors=errors
    )


def _month_number(name: str) -> int:
    lookup = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    key = name.strip().lower()
    if key not in lookup:
        raise ValueError(f"Unknown month name: {name}")
    return lookup[key]
