from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True)
class IcsEvent:
    date: date
    summary: str
    uid_seed: str


def _format_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _format_dtstamp(value: date) -> str:
    dt = datetime(value.year, value.month, value.day, tzinfo=UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _uid_from_seed(seed: str) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def build_ics(
    calendar_name: str,
    events: list[IcsEvent],
    prodid: str,
) -> str:
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"PRODID:{prodid}",
        f"X-WR-CALNAME:{calendar_name}",
    ]

    for event in sorted(events, key=lambda e: (e.date, e.summary)):
        uid = _uid_from_seed(event.uid_seed)
        start = _format_date(event.date)
        end = _format_date(event.date + timedelta(days=1))
        dtstamp = _format_dtstamp(event.date)

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;VALUE=DATE:{start}",
                f"DTEND;VALUE=DATE:{end}",
                f"SUMMARY:{event.summary}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
