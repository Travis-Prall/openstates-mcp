#!/usr/bin/env python3
"""Configuration management for OpenStates MCP Server."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration for OpenStates MCP Server."""

    # Server settings
    host: str = "0.0.0.0"
    mcp_port: int = 8795

    # Logging
    openstates_log_level: str = "INFO"
    openstates_debug: bool = False

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
