from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = 1


class SourceMeta(BaseModel):
    url: str
    sha256: str
    etag: str | None = None
    last_modified: str | None = None


class MetaInfo(BaseModel):
    generated_at: datetime
    town_id: str
    sources: dict[str, SourceMeta]
    git_commit: str | None = None


class CalendarPolicy(BaseModel):
    recycling_mode: Literal["alternating_week", "fixed_dates", "none"]
    anchor_week_sunday: date | None = None
    anchor_color: str | None = None


class HolidayPolicy(BaseModel):
    no_collection_dates: list[date] = Field(default_factory=list)
    delay_anchor_week_sundays: list[date] = Field(default_factory=list)
    shift_by_one_day: bool = True


class RouteConstraint(BaseModel):
    parity: Literal["odd", "even"] | None = None
    range_min: int | None = None
    range_max: int | None = None

    @field_validator("range_min", "range_max")
    @classmethod
    def _positive_range(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("range values must be non-negative")
        return v


class RouteEntry(BaseModel):
    street: str
    street_normalized: str
    weekday: str | None = None
    recycling_color: str | None = None
    no_collection: bool = False
    constraints: list[RouteConstraint] = Field(default_factory=list)
    notes: str | None = None


class Database(BaseModel):
    schema_version: int = SCHEMA_VERSION
    meta: MetaInfo
    calendar_policy: CalendarPolicy
    holiday_policy: HolidayPolicy
    aliases: dict[str, str] = Field(default_factory=dict)
    routes: list[RouteEntry]
    street_index: dict[str, list[int]] | None = None
