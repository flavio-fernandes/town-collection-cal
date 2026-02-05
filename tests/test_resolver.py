from datetime import UTC, datetime

from town_collection_cal.common.db_model import (
    CalendarPolicy,
    Database,
    HolidayPolicy,
    MetaInfo,
    RouteConstraint,
    RouteEntry,
)
from town_collection_cal.common.normalize import normalize_street_name
from town_collection_cal.service.resolver import resolve_route


def _db() -> Database:
    route = RouteEntry(
        street="Boston Road",
        street_normalized=normalize_street_name("Boston Road"),
        weekday="Thursday",
        recycling_color="BLUE",
        constraints=[RouteConstraint(parity="odd")],
    )
    return Database(
        meta=MetaInfo(
            generated_at=datetime.now(UTC),
            town_id="test",
            sources={},
        ),
        calendar_policy=CalendarPolicy(recycling_mode="alternating_week"),
        holiday_policy=HolidayPolicy(),
        aliases={"boston rd": "boston road"},
        routes=[route],
        street_index={"boston road": [0]},
    )


def test_resolver_alias_and_parity() -> None:
    db = _db()
    result = resolve_route(db, "Boston Rd", 3, suggestion_limit=10, fuzzy_threshold=80)
    assert result.route is not None
    assert result.route.weekday == "Thursday"

    result_fail = resolve_route(db, "Boston Rd", 2, suggestion_limit=10, fuzzy_threshold=80)
    assert result_fail.route is None
    assert result_fail.error is not None
