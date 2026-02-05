from datetime import date

from town_collection_cal.common.db_model import CalendarPolicy, HolidayPolicy
from town_collection_cal.service.schedule import generate_schedule


def test_schedule_alternating_week() -> None:
    calendar_policy = CalendarPolicy(
        recycling_mode="alternating_week",
        anchor_week_sunday=date(2025, 4, 6),
        anchor_color="BLUE",
    )
    holiday_policy = HolidayPolicy()
    events = generate_schedule(
        start_date=date(2025, 4, 6),
        days=7,
        trash_weekday="Monday",
        recycling_color="BLUE",
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
    )
    dates = [e.date for e in events]
    assert date(2025, 4, 7) in dates


def test_schedule_holiday_shift_and_skip() -> None:
    calendar_policy = CalendarPolicy(
        recycling_mode="alternating_week",
        anchor_week_sunday=date(2025, 4, 6),
        anchor_color="BLUE",
    )
    holiday_policy = HolidayPolicy(
        no_collection_dates=[date(2025, 4, 7)],
        delay_anchor_week_sundays=[date(2025, 4, 6)],
        shift_by_one_day=True,
    )
    events = generate_schedule(
        start_date=date(2025, 4, 6),
        days=7,
        trash_weekday="Monday",
        recycling_color=None,
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
    )
    assert date(2025, 4, 7) not in [e.date for e in events]
