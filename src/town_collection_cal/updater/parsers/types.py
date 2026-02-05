from __future__ import annotations

from dataclasses import dataclass, field

from town_collection_cal.common.db_model import CalendarPolicy, HolidayPolicy, RouteEntry


@dataclass
class RoutesParseResult:
    routes: list[RouteEntry]
    errors: list[str] = field(default_factory=list)


@dataclass
class ScheduleParseResult:
    calendar_policy: CalendarPolicy
    holiday_policy: HolidayPolicy
    errors: list[str] = field(default_factory=list)
