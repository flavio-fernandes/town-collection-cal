from town_collection_cal.common.normalize import normalize_street_name


def test_normalize_street_name() -> None:
    assert normalize_street_name("Boston Rd") == "boston road"
