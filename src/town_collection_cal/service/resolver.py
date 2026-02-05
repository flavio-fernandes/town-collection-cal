from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import process

from town_collection_cal.common.db_model import Database, RouteEntry
from town_collection_cal.common.normalize import normalize_street_name


@dataclass
class ResolutionResult:
    route: RouteEntry | None
    suggestions: list[str]
    requires_number: bool
    error: str | None = None


def _matches_constraints(route: RouteEntry, number: int | None) -> bool:
    if not route.constraints:
        return True
    if number is None:
        return False
    for constraint in route.constraints:
        if constraint.parity == "odd" and number % 2 == 0:
            continue
        if constraint.parity == "even" and number % 2 != 0:
            continue
        if constraint.range_min is not None and number < constraint.range_min:
            continue
        if constraint.range_max is not None and number > constraint.range_max:
            continue
        return True
    return False


def _collect_suggestions(
    query: str, streets: list[str], limit: int, score_cutoff: int
) -> list[str]:
    if not query:
        return []
    results = process.extract(
        query,
        streets,
        score_cutoff=score_cutoff,
        limit=limit,
    )
    return [match[0] for match in results]


def resolve_route(
    db: Database,
    street: str,
    number: int | None,
    *,
    suggestion_limit: int,
    fuzzy_threshold: int,
) -> ResolutionResult:
    normalized = normalize_street_name(street)
    if not normalized:
        return ResolutionResult(
            route=None,
            suggestions=[],
            requires_number=False,
            error="Invalid street",
        )

    canonical = db.aliases.get(normalized, normalized)
    indexes = None
    if db.street_index and canonical in db.street_index:
        indexes = db.street_index[canonical]
        candidates = [db.routes[idx] for idx in indexes]
    else:
        candidates = [r for r in db.routes if r.street_normalized == canonical]

    if not candidates:
        streets = sorted({r.street for r in db.routes})
        suggestions = _collect_suggestions(street, streets, suggestion_limit, fuzzy_threshold)
        return ResolutionResult(
            route=None,
            suggestions=suggestions,
            requires_number=False,
            error="Street not found",
        )

    matches = [r for r in candidates if _matches_constraints(r, number)]
    if matches:
        return ResolutionResult(route=matches[0], suggestions=[], requires_number=False)

    if number is None:
        return ResolutionResult(
            route=None,
            suggestions=[],
            requires_number=True,
            error="Street requires a house number for disambiguation",
        )

    return ResolutionResult(
        route=None,
        suggestions=[],
        requires_number=False,
        error="No matching route for house number",
    )
