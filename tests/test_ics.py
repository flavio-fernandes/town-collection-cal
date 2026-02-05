from datetime import date

from town_collection_cal.common.ics import IcsEvent, build_ics


def test_ics_build() -> None:
    events = [
        IcsEvent(date=date(2025, 4, 7), summary="Test Trash", uid_seed="a"),
        IcsEvent(date=date(2025, 4, 8), summary="Test Recycling", uid_seed="b"),
    ]
    text = build_ics("Test Calendar", events, "-//test//EN")
    assert "BEGIN:VCALENDAR" in text
    assert "SUMMARY:Test Trash" in text
    assert "SUMMARY:Test Recycling" in text
