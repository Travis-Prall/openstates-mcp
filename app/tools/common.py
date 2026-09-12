"""Shared helpers for OpenStates MCP tool modules.

Every tool module talks to the same upstream API with the same auth header,
timeout policy, retry policy and logging behaviour. Keeping that logic here
means the tool modules stay small and declarative.
"""

import asyncio
from typing import Any

from fastmcp import Context
import httpx
from loguru import logger

from app.config import config

#: Environment variable holding the OpenStates API key.
API_KEY_ENV_VAR = "OPENSTATES_API_KEY"

#: HTTP status codes worth retrying (rate limited / transient server errors).
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def validate_api_key() -> str:
    """Return the configured OpenStates API key.

    Returns:
        The OpenStates API key.

    Raises:
        ValueError: If no API key is configured.

    """
    if not config.openstates_api_key:
        raise ValueError(f"{API_KEY_ENV_VAR} not found in environment variables")
    return config.openstates_api_key


async def log_info(ctx: Context | None, message: str) -> None:
    """Log an informational message to the MCP context or the log file."""
    if ctx:
        await ctx.info(message)
    else:
        logger.info(message)


async def log_error(ctx: Context | None, message: str) -> None:
    """Log an error message to the MCP context or the log file."""
    if ctx:
        await ctx.error(message)
    else:
        logger.error(message)


def build_url(path: str) -> str:
    """Join a relative API path onto the configured base URL.

    Args:
        path: Relative path such as ``bills`` or ``people.geo``.

    Returns:
        Absolute URL on the configured OpenStates API host.

    """
    return f"{config.openstates_base_url.rstrip('/')}/{path.lstrip('/')}"


def _timeout() -> httpx.Timeout:
    """Build the httpx timeout from configuration.

    Returns:
        Configured connect/read timeouts.

    """
    return httpx.Timeout(
        config.openstates_timeout,
        connect=config.openstates_connect_timeout,
        read=config.openstates_read_timeout,
    )


async def request_json(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Perform an authenticated GET request against the OpenStates API.

    Retries rate limited and transient server responses with exponential
    backoff. The API key is read from configuration; a missing key surfaces as a
    ``ValueError`` from :func:`validate_api_key` before any request is made, and
    a non-retryable error status propagates as ``httpx.HTTPStatusError``.

    Args:
        path: Relative API path (for example ``bills`` or ``bills/ocd-bill/<id>``).
        params: Optional query parameters.
        ctx: Optional MCP context used for progress/error reporting.

    Returns:
        The decoded JSON response body.

    Raises:
        httpx.HTTPError: If the request keeps failing after every retry.

    """
    api_key = validate_api_key()
    url = build_url(path)
    headers = {"x-api-key": api_key}
    attempts = max(1, config.openstates_max_retries)

    last_error: httpx.HTTPError | None = None
    async with httpx.AsyncClient() as client:
        for attempt in range(attempts):
            try:
                response = await client.get(
                    url, params=params, headers=headers, timeout=_timeout()
                )
            except httpx.HTTPError as error:
                last_error = error
                await log_error(ctx, f"API request to {url} failed: {error}")
            else:
                if response.status_code in RETRYABLE_STATUS_CODES:
                    last_error = httpx.HTTPStatusError(
                        f"Retryable status {response.status_code} for {url}",
                        request=response.request,
                        response=response,
                    )
                    await log_error(
                        ctx,
                        f"API returned {response.status_code} for {url} "
                        f"(attempt {attempt + 1}/{attempts})",
                    )
                else:
                    response.raise_for_status()
                    return response.json()

            if attempt + 1 < attempts:
                await asyncio.sleep(config.openstates_retry_delay * (2**attempt))

    if last_error is not None:
        raise last_error
    raise httpx.HTTPError(f"Request to {url} failed without a captured error")
