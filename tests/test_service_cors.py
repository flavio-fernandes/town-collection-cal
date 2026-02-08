from flask import Response

from town_collection_cal.service.app import (
    _append_vary_header,
    _cors_allowed_origins_from_env,
)


def test_cors_allowed_origins_from_env_parses_csv(monkeypatch: object) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://flavio-fernandes.github.io, https://trash.flaviof.com/ ,",
    )
    monkeypatch.delenv("TCC_CORS_ALLOWED_ORIGINS", raising=False)

    assert _cors_allowed_origins_from_env() == {
        "https://flavio-fernandes.github.io",
        "https://trash.flaviof.com",
    }


def test_cors_allowed_origins_from_env_uses_legacy_fallback(monkeypatch: object) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("TCC_CORS_ALLOWED_ORIGINS", "https://example.org")

    assert _cors_allowed_origins_from_env() == {"https://example.org"}


def test_append_vary_header_merges_without_duplicates() -> None:
    response = Response("ok")
    response.headers["Vary"] = "Accept-Encoding"

    _append_vary_header(response, "Origin")
    _append_vary_header(response, "Origin")

    assert set(value.strip() for value in response.headers["Vary"].split(",")) == {
        "Accept-Encoding",
        "Origin",
    }
