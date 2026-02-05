from __future__ import annotations

import re

DEFAULT_SUFFIX_MAP = {
    "rd": "road",
    "st": "street",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "cir": "circle",
    "hwy": "highway",
    "pkwy": "parkway",
    "pl": "place",
    "ter": "terrace",
    "trl": "trail",
    "wy": "way",
    "way": "way",
}

DEFAULT_DIRECTIONAL_MAP = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}


def normalize_street_name(
    raw: str,
    suffix_map: dict[str, str] | None = None,
    directional_map: dict[str, str] | None = None,
) -> str:
    if not raw:
        return ""
    suffix_map = suffix_map or DEFAULT_SUFFIX_MAP
    directional_map = directional_map or DEFAULT_DIRECTIONAL_MAP

    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw).lower()
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return ""

    normalized: list[str] = []
    for idx, token in enumerate(tokens):
        if token in directional_map:
            normalized.append(directional_map[token])
            continue

        if idx == len(tokens) - 1 and token in suffix_map:
            normalized.append(suffix_map[token])
            continue

        normalized.append(token)

    return " ".join(normalized).strip()
