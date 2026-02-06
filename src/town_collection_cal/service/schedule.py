from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from town_collection_cal.common.db_model import CalendarPolicy, HolidayPolicy

WEEKDAY_TO_OFFSET = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
}


@dataclass(frozen=True)
class ScheduleEvent:
    date: date
    types: set[str]


def local_today(tz_name: str) -> date:
    tz = ZoneInfo(tz_name)
    return datetime.now(tz=tz).date()


def _week_sunday(some_day: date) -> date:
    offset = (some_day.weekday() + 1) % 7
    return some_day.fromordinal(some_day.toordinal() - offset)


def _week_color(anchor_sunday: date, anchor_color: str, week_sunday: date) -> str:
    weeks = (week_sunday - anchor_sunday).days // 7
    if weeks % 2 == 0:
        return anchor_color.upper()
    return "GREEN" if anchor_color.upper() == "BLUE" else "BLUE"


def generate_schedule(
    *,
    start_date: date,
    days: int,
    trash_weekday: str,
    recycling_color: str | None,
    calendar_policy: CalendarPolicy,
    holiday_policy: HolidayPolicy,
) -> list[ScheduleEvent]:
    end_date = start_date + timedelta(days=days)
    events: dict[date, set[str]] = {}

    trash_offset = WEEKDAY_TO_OFFSET[trash_weekday.lower()]
    anchor_sunday = calendar_policy.anchor_week_sunday
    anchor_color = calendar_policy.anchor_color

    shift_by_week: dict[date, list[date]] = {}
    if holiday_policy.shift_by_one_day:
        for holiday in holiday_policy.shift_holidays:
            week = _week_sunday(holiday)
            shift_by_week.setdefault(week, []).append(holiday)

    week_start = _week_sunday(start_date)
    current = week_start

    while current <= end_date:
        base_trash_date = current + timedelta(days=trash_offset)
        holiday_cutoff = None
        if holiday_policy.shift_by_one_day:
            dates = shift_by_week.get(current)
            if dates:
                holiday_cutoff = min(dates)

        trash_date = _apply_holiday_shift(
            base_trash_date, holiday_cutoff, holiday_policy.no_collection_dates
        )
        if trash_date and start_date <= trash_date <= end_date:
            events.setdefault(trash_date, set()).add("trash")

        if recycling_color and calendar_policy.recycling_mode == "alternating_week":
            if not anchor_sunday or not anchor_color:
                raise ValueError("Missing recycling anchor data")
            week_color = _week_color(anchor_sunday, anchor_color, current)
            if week_color == recycling_color.upper():
                base_recycling_date = current + timedelta(days=trash_offset)
                recycling_date = _apply_holiday_shift(
                    base_recycling_date, holiday_cutoff, holiday_policy.no_collection_dates
                )
                if recycling_date and start_date <= recycling_date <= end_date:
                    events.setdefault(recycling_date, set()).add("recycling")

        current += timedelta(days=7)

    return [ScheduleEvent(date=d, types=types) for d, types in sorted(events.items())]


def _apply_holiday_shift(
    base_date: date, holiday_cutoff: date | None, no_collection_dates: list[date]
) -> date | None:
    if base_date in no_collection_dates:
        return None
    if not holiday_cutoff:
        return base_date
    if base_date < holiday_cutoff:
        return base_date
    return base_date + timedelta(days=1)
