import csv
import hashlib
import shutil
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from town_collection_cal.common.db_model import HolidayPolicy
from town_collection_cal.common.http_cache import CacheResult
from town_collection_cal.service.app import create_app
from town_collection_cal.service.schedule import generate_schedule
from town_collection_cal.updater import build_db as builder
from town_collection_cal.updater.overrides import apply_holiday_overrides
from town_collection_cal.updater.parsers.westford_guide import parse_schedule

FIXTURES = Path("tests/fixtures")


def reviewed_policies():
    calendar = parse_schedule(FIXTURES / "westford_guide_2026_2027.txt", "fixture://guide")
    holidays = apply_holiday_overrides(
        HolidayPolicy(), Path("towns/westford_ma/holiday_rules.yaml")
    )
    return calendar.calendar_policy, holidays


@pytest.mark.parametrize("color", ["BLUE", "GREEN"])
def test_every_thursday_against_visually_reviewed_calendar(color):
    # All 52 pickups transcribed from page 5, including the three Thursday delays.
    with (FIXTURES / "westford_thursday_2026_2027.csv").open() as stream:
        expected = {date.fromisoformat(row["date"]): row["color"] for row in csv.DictReader(stream)}
    calendar, holidays = reviewed_policies()
    events = generate_schedule(
        start_date=date(2026, 7, 1),
        days=365,
        trash_weekday="Thursday",
        recycling_color=color,
        calendar_policy=calendar,
        holiday_policy=holidays,
    )
    assert {e.date for e in events} == set(expected)
    assert {e.date for e in events if "recycling" in e.types} == {
        day for day, week_color in expected.items() if week_color == color
    }


@pytest.mark.parametrize(
    "start,weekday,expected",
    [
        ("2026-07-01", "Friday", "2026-07-03"),
        ("2026-09-06", "Monday", "2026-09-08"),
        ("2026-09-06", "Tuesday", "2026-09-09"),
        ("2026-09-06", "Wednesday", "2026-09-10"),
        ("2026-09-06", "Thursday", "2026-09-11"),
        ("2026-09-06", "Friday", "2026-09-12"),
        ("2026-11-22", "Wednesday", "2026-11-25"),
        ("2026-11-22", "Thursday", "2026-11-27"),
        ("2026-11-22", "Friday", "2026-11-28"),
        ("2026-12-20", "Thursday", "2026-12-24"),
        ("2026-12-20", "Friday", "2026-12-26"),
        ("2026-12-27", "Thursday", "2026-12-31"),
        ("2026-12-27", "Friday", "2027-01-02"),
        ("2027-05-30", "Monday", "2027-06-01"),
        ("2027-05-30", "Friday", "2027-06-05"),
    ],
)
def test_holiday_cutoffs_and_saturday_pickups(start, weekday, expected):
    calendar, holidays = reviewed_policies()
    events = generate_schedule(
        start_date=date.fromisoformat(start),
        days=6,
        trash_weekday=weekday,
        recycling_color=None,
        calendar_policy=calendar,
        holiday_policy=holidays,
    )
    assert [e.date.isoformat() for e in events] == [expected]


def test_reviewed_coverage_boundary():
    calendar, holidays = reviewed_policies()
    kwargs = dict(
        trash_weekday="Wednesday",
        recycling_color="BLUE",
        calendar_policy=calendar,
        holiday_policy=holidays,
    )
    events = generate_schedule(start_date=date(2027, 6, 27), days=365, **kwargs)
    assert [e.date for e in events] == [date(2027, 6, 30)]
    with pytest.raises(ValueError, match="No reviewed"):
        generate_schedule(start_date=date(2027, 7, 1), days=365, **kwargs)


@pytest.fixture
def build_inputs(tmp_path, monkeypatch):
    town = tmp_path / "town"
    shutil.copytree("towns/westford_ma", town)
    guide = FIXTURES / "westford_guide_2026_2027.txt"
    overrides = town / "holiday_rules.yaml"
    rules = yaml.safe_load(overrides.read_text())
    rules["reviewed_source_sha256"] = hashlib.sha256(guide.read_bytes()).hexdigest()
    overrides.write_text(yaml.safe_dump(rules))

    def fetch(url, cache_dir, filename, **kwargs):
        path = guide if filename == "schedule.pdf" else FIXTURES / "westford_routes.txt"
        return CacheResult(
            path, hashlib.sha256(path.read_bytes()).hexdigest(), True, 200, str(url), None, None
        )

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 10, 12, tzinfo=tz)

    monkeypatch.setattr(builder, "fetch_with_cache", fetch)
    monkeypatch.setattr(builder, "datetime", FrozenDatetime)
    return town, tmp_path / "db.json", tmp_path / "cache"


@pytest.mark.parametrize("failure", ["changed_pdf", "expired_review"])
def test_review_failure_preserves_previous_db(build_inputs, failure):
    town, output, cache = build_inputs
    output.write_text("previous database")
    path = town / "holiday_rules.yaml"
    rules = yaml.safe_load(path.read_text())
    if failure == "changed_pdf":
        rules["reviewed_source_sha256"] = "0" * 64
        message = "Schedule PDF changed"
    else:
        rules["valid_through"] = "2026-09-09"
        message = "Holiday rules expired"
    path.write_text(yaml.safe_dump(rules))
    with pytest.raises(ValueError, match=message):
        builder.build_db(town / "town.yaml", output, cache)
    assert output.read_text() == "previous database"


def test_built_db_serves_correct_ics_and_reports_expiry(build_inputs, monkeypatch):
    town, output, cache = build_inputs
    builder.build_db(town / "town.yaml", output, cache)
    monkeypatch.setenv("TOWN_CONFIG_PATH", str(town / "town.yaml"))
    monkeypatch.setenv("DB_PATH", str(output))
    monkeypatch.setattr("town_collection_cal.service.app.local_today", lambda _: date(2026, 9, 10))
    client = create_app().test_client()
    result = client.get("/town.ics?weekday=Thursday&color=BLUE&days=7")
    assert result.status_code == 200
    assert "DTSTART;VALUE=DATE:20260911" in result.text
    assert "DTSTART;VALUE=DATE:20260910" not in result.text
    assert client.get("/healthz").status_code == 200
    assert client.get("/version").json["schedule_review"]["valid_through"]
    monkeypatch.setattr("town_collection_cal.service.app.local_today", lambda _: date(2027, 7, 1))
    assert client.get("/healthz").status_code == 503
    result = client.get("/town.ics?weekday=Thursday&color=BLUE")
    assert result.status_code == 400
    assert "No reviewed" in result.json["error"]
