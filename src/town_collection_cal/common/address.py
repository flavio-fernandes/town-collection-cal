from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

try:
    import usaddress  # type: ignore
except Exception:  # pragma: no cover - fallback when dependency missing
    usaddress = None

logger = logging.getLogger(__name__)
_warned_fallback = False


@dataclass(frozen=True)
class ParsedAddress:
    house_number: str | None
    street_name: str | None
    raw: str
    components: dict[str, Any]


def parse_address(raw: str) -> ParsedAddress:
    raw = raw.strip()
    if not raw:
        return ParsedAddress(None, None, raw, {})
    if usaddress:
        try:
            parsed, _ = usaddress.tag(raw)
        except usaddress.RepeatedLabelError as exc:  # type: ignore[attr-defined]
            parsed = exc.parsed_string or {}
        house_number = parsed.get("AddressNumber")
        street_name = parsed.get("StreetName")
        street_suffix = parsed.get("StreetNamePostType")
        street_dir = parsed.get("StreetNamePreDirectional")

        parts = [p for p in [street_dir, street_name, street_suffix] if p]
        street = " ".join(parts) if parts else None
        return ParsedAddress(house_number, street, raw, parsed)

    # Fallback: naive split (best effort without usaddress)
    global _warned_fallback
    if not _warned_fallback:
        logger.warning("usaddress not installed; using naive address parsing")
        _warned_fallback = True
    primary = raw.split(",")[0]
    parts = primary.split()
    if not parts:
        return ParsedAddress(None, None, raw, {})
    house_number = parts[0] if parts[0].isdigit() else None
    street = " ".join(parts[1:]) if house_number else raw
    return ParsedAddress(house_number, street, raw, {})
