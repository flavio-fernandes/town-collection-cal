from datetime import date
from pathlib import Path

from town_collection_cal.updater.parsers.westford_guide import parse_schedule


def test_parse_schedule_fixture() -> None:
    fixture = Path("tests/fixtures/westford_guide.txt")
    result = parse_schedule(fixture, "fixture://schedule")
    assert not result.errors
    assert result.calendar_policy.anchor_color == "BLUE"
    assert result.calendar_policy.anchor_week_sunday == date(2025, 4, 6)
