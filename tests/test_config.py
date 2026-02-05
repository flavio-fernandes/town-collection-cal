from pathlib import Path

from town_collection_cal.config.loader import load_town_config


def test_load_westford_config() -> None:
    config, town_dir = load_town_config(Path("towns/westford_ma/town.yaml"))
    assert config.town_id == "westford_ma"
    assert config.ics.default_days_ahead == 365
    assert town_dir.name == "westford_ma"
