from pathlib import Path

import pytest

from town_collection_cal.updater.parsers.westford_routes import parse_routes


def test_parse_routes_fixture() -> None:
    fixture = Path("tests/fixtures/westford_routes.txt")
    result = parse_routes(fixture, "fixture://routes")
    assert not result.errors
    assert len(result.routes) >= 2
    streets = {r.street for r in result.routes}
    assert "Boston Road" in streets
    assert "Main St" in streets
    assert "Littleton Rd" in streets

    main_entries = [r for r in result.routes if r.street == "Main St"]
    assert len(main_entries) == 2
    ranges = {(c.range_min, c.range_max) for r in main_entries for c in r.constraints}
    assert (1, 110) in ranges
    assert (112, 204) in ranges

    littleton = [r for r in result.routes if r.street == "Littleton Rd"]
    assert len(littleton) == 1
    assert littleton[0].weekday == "Tuesday"
    assert littleton[0].recycling_color == "BLUE"


def test_parse_routes_pdf_if_available() -> None:
    pdf_path = Path("data/cache/routes.pdf")
    if not pdf_path.exists():
        pytest.skip("routes.pdf not cached")
    result = parse_routes(pdf_path, "local://routes.pdf")
    assert result.routes
