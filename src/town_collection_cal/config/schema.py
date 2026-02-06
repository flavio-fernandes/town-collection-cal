from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator, model_validator


class RecyclingMode(StrEnum):
    ALTERNATING_WEEK = "alternating_week"
    FIXED_DATES = "fixed_dates"
    NONE = "none"


class HolidayPolicyMode(StrEnum):
    YAML_OVERRIDES = "yaml_overrides"
    PARSER_EXTRACTED = "parser_extracted"


class SourcesConfig(BaseModel):
    routes_pdf_url: HttpUrl
    schedule_pdf_url: HttpUrl


class ParsersConfig(BaseModel):
    routes_parser: str
    schedule_parser: str


class IcsConfig(BaseModel):
    calendar_name_template: str = "{town_name} Collection"
    default_days_ahead: int = 365
    max_days_ahead: int = 365

    @field_validator("default_days_ahead", "max_days_ahead")
    @classmethod
    def _positive_days(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be > 0")
        return v

    @model_validator(mode="after")
    def _days_order(self) -> IcsConfig:
        if self.default_days_ahead > self.max_days_ahead:
            raise ValueError("default_days_ahead cannot exceed max_days_ahead")
        return self


class RecyclingRulesConfig(BaseModel):
    mode: RecyclingMode
    anchor_week_sunday: date | None = None
    anchor_color: str | None = None

    @model_validator(mode="after")
    def _validate_anchor(self) -> RecyclingRulesConfig:
        if self.mode == RecyclingMode.ALTERNATING_WEEK:
            if (self.anchor_week_sunday and not self.anchor_color) or (
                self.anchor_color and not self.anchor_week_sunday
            ):
                raise ValueError(
                    "anchor_week_sunday and anchor_color must both be provided if one is set"
                )
        return self


class HolidayRulesConfig(BaseModel):
    policy_mode: HolidayPolicyMode
    no_collection_dates: list[date] = Field(default_factory=list)
    shift_holidays: list[date] = Field(default_factory=list)
    shift_by_one_day: bool = True


class RulesConfig(BaseModel):
    recycling: RecyclingRulesConfig
    holidays: HolidayRulesConfig


class OverridesPathsConfig(BaseModel):
    holiday_rules_yaml: str | None = None
    holiday_overrides_yaml: str | None = None
    street_aliases_yaml: str | None = None
    route_overrides_yaml: str | None = None

    @model_validator(mode="after")
    def _coerce_holiday_rules(self) -> OverridesPathsConfig:
        if not self.holiday_rules_yaml and self.holiday_overrides_yaml:
            self.holiday_rules_yaml = self.holiday_overrides_yaml
        return self


class ResolverConfig(BaseModel):
    suggestion_limit: int = 10
    fuzzy_threshold: int = 85

    @field_validator("suggestion_limit")
    @classmethod
    def _suggestion_limit_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("suggestion_limit must be > 0")
        return v

    @field_validator("fuzzy_threshold")
    @classmethod
    def _fuzzy_threshold_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("fuzzy_threshold must be between 0 and 100")
        return v


class ServiceConfig(BaseModel):
    auto_update_on_missing_db: bool = False
    reload_interval_seconds: int = 10

    @field_validator("reload_interval_seconds")
    @classmethod
    def _reload_interval_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("reload_interval_seconds must be >= 1")
        return v


class TownConfig(BaseModel):
    town_id: str
    town_name: str
    timezone: str
    sources: SourcesConfig
    parsers: ParsersConfig
    ics: IcsConfig = Field(default_factory=IcsConfig)
    rules: RulesConfig
    overrides_paths: OverridesPathsConfig = Field(default_factory=OverridesPathsConfig)
    resolver: ResolverConfig = Field(default_factory=ResolverConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)

    @field_validator("town_id", "town_name", "timezone")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("value must be non-empty")
        return v


def validate_config(data: dict[str, Any]) -> TownConfig:
    try:
        return TownConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid town config: {exc}") from exc
