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


def test_schedule_holiday_skip() -> None:
    calendar_policy = CalendarPolicy(
        recycling_mode="alternating_week",
        anchor_week_sunday=date(2025, 4, 6),
        anchor_color="BLUE",
    )
    holiday_policy = HolidayPolicy(
        no_collection_dates=[date(2025, 4, 7)],
        shift_holidays=[date(2025, 4, 7)],
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


def test_schedule_holiday_shift_after_date() -> None:
    calendar_policy = CalendarPolicy(
        recycling_mode="alternating_week",
        anchor_week_sunday=date(2025, 4, 6),
        anchor_color="BLUE",
    )
    holiday_policy = HolidayPolicy(
        shift_holidays=[date(2025, 4, 9)],
        shift_by_one_day=True,
    )

    # Monday before holiday stays Monday.
    events = generate_schedule(
        start_date=date(2025, 4, 6),
        days=7,
        trash_weekday="Monday",
        recycling_color=None,
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
    )
    assert date(2025, 4, 7) in [e.date for e in events]

    # Wednesday holiday shifts to Thursday.
    events = generate_schedule(
        start_date=date(2025, 4, 6),
        days=7,
        trash_weekday="Wednesday",
        recycling_color=None,
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
    )
    dates = [e.date for e in events]
    assert date(2025, 4, 9) not in dates
    assert date(2025, 4, 10) in dates

    # Thursday after holiday shifts to Friday.
    events = generate_schedule(
        start_date=date(2025, 4, 6),
        days=7,
        trash_weekday="Thursday",
        recycling_color=None,
        calendar_policy=calendar_policy,
        holiday_policy=holiday_policy,
    )
    dates = [e.date for e in events]
    assert date(2025, 4, 10) not in dates
    assert date(2025, 4, 11) in dates
