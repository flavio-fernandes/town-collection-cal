from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from town_collection_cal.config.schema import TownConfig, validate_config


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a mapping: {path}")
    return data


def resolve_config_path(town_id: str | None = None, config_path: str | None = None) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    if not town_id:
        raise ValueError("Either TOWN_ID or TOWN_CONFIG_PATH must be provided")
    return (Path.cwd() / "towns" / town_id / "town.yaml").resolve()


def load_town_config(config_path: Path) -> tuple[TownConfig, Path]:
    data = _load_yaml(config_path)
    config = validate_config(data)
    return config, config_path.parent.resolve()


def load_from_env() -> tuple[TownConfig, Path]:
    town_id = os.getenv("TOWN_ID")
    config_path = os.getenv("TOWN_CONFIG_PATH")
    path = resolve_config_path(town_id=town_id, config_path=config_path)
    return load_town_config(path)
