from pathlib import Path

from town_collection_cal.updater.parsers.westford_routes import parse_routes


def test_parse_routes_fixture() -> None:
    fixture = Path("tests/fixtures/westford_routes.txt")
    result = parse_routes(fixture, "fixture://routes")
    assert not result.errors
    assert len(result.routes) >= 2
    streets = {r.street for r in result.routes}
    assert "Boston Road" in streets
