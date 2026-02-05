from town_collection_cal.common import address as address_mod


def test_parse_address_fallback_strips_city(monkeypatch) -> None:
    monkeypatch.setattr(address_mod, "usaddress", None)
    parsed = address_mod.parse_address("65 Boston Road, Westford, MA 01886")
    assert parsed.house_number == "65"
    assert parsed.street_name == "Boston Road"
