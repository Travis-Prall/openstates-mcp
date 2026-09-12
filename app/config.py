#!/usr/bin/env python3
"""Configuration management for OpenStates MCP Server.

Every setting can be supplied as an environment variable or through a ``.env``
file in the project root. Environment variable names are the field names in
upper case (for example ``mcp_port`` -> ``MCP_PORT``).
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

#: Directory containing this file (``app/``).
APP_DIR = Path(__file__).resolve().parent

#: Supported MCP transports for the server entrypoint.
TransportName = Literal["streamable-http", "http", "stdio"]


def parse_csv(raw: str | None) -> list[str]:
    """Split a comma separated string into a list of stripped values.

    Args:
        raw: Raw comma separated value, or ``None``.

    Returns:
        List of non-empty, whitespace-stripped entries. Empty for falsy input.

    """
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config(BaseSettings):
    """Configuration for OpenStates MCP Server."""

    # Server settings
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8797
    mcp_path: str = "/mcp/"
    mcp_transport: TransportName = "streamable-http"
    #: Serve every request in a fresh session so the service can be scaled
    #: horizontally behind a load balancer without sticky sessions.
    mcp_stateless_http: bool = False
    #: Comma separated hostnames allowed in the HTTP ``Host`` header
    #: (DNS-rebinding protection). Empty disables the check for native/dev runs.
    mcp_allowed_hosts: str = ""
    #: Comma separated ``Origin`` header values allowed to call the server.
    #: Empty disables the check (non-browser MCP clients send no ``Origin``).
    mcp_allowed_origins: str = ""
    #: Comma separated browser origins allowed by CORS. Empty means no CORS
    #: headers are emitted at all, which is the safe default for an MCP API.
    mcp_cors_origins: str = ""

    # Logging
    openstates_log_level: str = "INFO"
    openstates_debug: bool = False
    #: Directory for rotating log files. Defaults to ``app/logs``. Set this to
    #: a writable location (for example ``/tmp/logs``) when the root filesystem
    #: is mounted read-only.
    log_dir: str | None = None

    # Environment
    environment: str = "production"

    # OpenStates API
    openstates_base_url: str = "https://v3.openstates.org"
    openstates_api_key: str | None = None
    openstates_timeout: int = 30
    openstates_connect_timeout: int = 10
    openstates_read_timeout: int = 30
    openstates_rate_limit: int = 50
    openstates_cache_ttl: int = 300
    openstates_max_retries: int = 3
    openstates_retry_delay: float = 1.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }

    @property
    def host(self) -> str:
        """Deprecated alias for :attr:`mcp_host`."""
        return self.mcp_host

    @property
    def allowed_hosts(self) -> list[str]:
        """Hostnames accepted in the ``Host`` header (empty = no check)."""
        return parse_csv(self.mcp_allowed_hosts)

    @property
    def allowed_origins(self) -> list[str]:
        """``Origin`` header values accepted (empty = no check)."""
        return parse_csv(self.mcp_allowed_origins)

    @property
    def cors_origins(self) -> list[str]:
        """Browser origins allowed by CORS (empty = CORS disabled)."""
        return parse_csv(self.mcp_cors_origins)

    @property
    def resolved_log_dir(self) -> Path:
        """Filesystem directory used for rotating log files."""
        if self.log_dir:
            return Path(self.log_dir).expanduser()
        return APP_DIR / "logs"

    @property
    def streamable_http_path(self) -> str:
        """Normalised HTTP path for the streamable-http endpoint."""
        path = self.mcp_path.strip() or "/mcp/"
        if not path.startswith("/"):
            path = f"/{path}"
        return path


# Global config instance
config = Config()


def is_development() -> bool:
    """Check if running in development environment.

    Returns:
        True if in development mode, False otherwise.

    """
    return config.environment.lower() == "development"


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if debug is enabled, False otherwise.

    """
    return config.openstates_debug or config.openstates_log_level.upper() == "DEBUG"
