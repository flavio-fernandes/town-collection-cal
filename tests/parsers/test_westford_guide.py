from datetime import date
from pathlib import Path

import pytest

from town_collection_cal.updater.parsers.westford_guide import parse_schedule


def test_parse_schedule_fixture() -> None:
    fixture = Path("tests/fixtures/westford_guide.txt")
    result = parse_schedule(fixture, "fixture://schedule")
    assert not result.errors
    assert result.calendar_policy.anchor_color == "BLUE"
    assert result.calendar_policy.anchor_week_sunday == date(2025, 4, 6)


def test_guide_year_ignores_unrelated_years() -> None:
    result = parse_schedule(Path("tests/fixtures/westford_guide_2026_2027.txt"), "fixture://new")
    assert not result.errors
    assert result.calendar_policy.anchor_week_sunday == date(2026, 6, 28)
    assert result.calendar_policy.anchor_color == "BLUE"


def test_missing_title_does_not_guess_current_year(tmp_path: Path) -> None:
    guide = tmp_path / "guide.txt"
    guide.write_text("The week of July 1-3 is BLUE.")
    with pytest.raises(ValueError, match="guide year"):
        parse_schedule(guide, "fixture://missing-title")
