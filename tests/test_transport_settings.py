"""Tests for configuration parsing of the server/transport settings."""

from pydantic import ValidationError
import pytest

from app.config import APP_DIR, Config, config, parse_csv


def test_config_defaults_match_documented_values() -> None:
    """Server and transport defaults are stable and documented."""
    assert config.mcp_host == "0.0.0.0"
    assert config.mcp_port == 8797
    assert config.mcp_path == "/mcp/"
    assert config.mcp_transport == "streamable-http"
    assert config.mcp_stateless_http is False
    assert config.resolved_log_dir == APP_DIR / "logs"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ("", []),
        ("   ", []),
        ("a", ["a"]),
        ("a,b,c", ["a", "b", "c"]),
        (" a , b ", ["a", "b"]),
        ("a,,b", ["a", "b"]),
    ],
)
def test_parse_csv_handles_edge_cases(raw: str | None, expected: list[str]) -> None:
    """CSV parsing ignores blanks and surrounding whitespace."""
    assert parse_csv(raw) == expected


@pytest.mark.parametrize(
    ("attribute", "value", "expected"),
    [
        (
            "allowed_hosts",
            "a.example.com, b.example.com",
            ["a.example.com", "b.example.com"],
        ),
        ("allowed_origins", "https://a.test", ["https://a.test"]),
        ("cors_origins", "", []),
    ],
)
def test_security_settings_parse_from_csv(
    attribute: str, value: str, expected: list[str]
) -> None:
    """Security allow lists are exposed as lists from CSV settings."""
    field = {
        "allowed_hosts": "mcp_allowed_hosts",
        "allowed_origins": "mcp_allowed_origins",
        "cors_origins": "mcp_cors_origins",
    }[attribute]
    settings = Config(_env_file=None, **{field: value})

    assert getattr(settings, attribute) == expected


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [("/mcp/", "/mcp/"), ("mcp", "/mcp"), ("  /custom  ", "/custom"), ("", "/mcp/")],
)
def test_streamable_http_path_is_normalised(raw_path: str, expected: str) -> None:
    """The HTTP path always starts with a slash and falls back to /mcp/."""
    settings = Config(_env_file=None, mcp_path=raw_path)

    assert settings.streamable_http_path == expected


def test_log_dir_override_is_resolved() -> None:
    """An explicit log directory overrides the packaged default."""
    settings = Config(_env_file=None, log_dir="/tmp/openstates-logs")

    assert settings.resolved_log_dir.as_posix() == "/tmp/openstates-logs"


def test_invalid_transport_is_rejected() -> None:
    """Only the supported transports can be configured."""
    with pytest.raises(ValidationError):
        Config(_env_file=None, mcp_transport="carrier-pigeon")


def test_host_property_keeps_backwards_compatibility() -> None:
    """``host`` remains available as an alias for ``mcp_host``."""
    settings = Config(_env_file=None, mcp_host="127.0.0.1")

    assert settings.host == "127.0.0.1"
