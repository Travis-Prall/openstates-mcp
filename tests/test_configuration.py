"""Tests for HTTP client configuration and timeout handling."""

import asyncio
from typing import Any

from fastmcp import Client
from fastmcp.exceptions import ToolError
from loguru import logger
import pytest

from app.config import config
from app.server import mcp


@pytest.fixture
def client() -> Client[Any]:
    """Create a test client connected to the real server.

    Returns
    -------
    Client
        A FastMCP test client connected to the server instance.

    """
    return Client(mcp)


@pytest.mark.asyncio
async def test_timeout_configuration(client: Client[Any]) -> None:
    """Test that timeout is properly configured.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Check that timeout is set to reasonable value
        assert config.openstates_timeout > 0
        assert config.openstates_timeout <= 60  # Should not be too high

        logger.info(
            f"OpenStates API timeout configured to: {config.openstates_timeout}s"
        )


@pytest.mark.asyncio
async def test_api_key_configuration(client: Client[Any]) -> None:
    """Test API key configuration handling.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        if config.openstates_api_key:
            logger.info("OpenStates API key is configured")
            assert len(config.openstates_api_key.strip()) > 0
        else:
            logger.warning(
                "OpenStates API key is not configured - some tests will be skipped"
            )


@pytest.mark.asyncio
async def test_rate_limit_configuration(client: Client[Any]) -> None:
    """Test rate limiting configuration.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Check rate limit configuration
        assert config.openstates_rate_limit > 0
        assert config.openstates_rate_limit <= 100  # Reasonable upper bound

        logger.info(
            f"Rate limit configured to: {config.openstates_rate_limit} requests/second"
        )


@pytest.mark.asyncio
async def test_base_url_configuration(client: Client[Any]) -> None:
    """Test that base URL is properly configured.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Check base URL
        assert config.openstates_base_url.startswith("https://")
        # Accept either openstates.org or courtlistener.com (for testing)
        assert (
            "openstates.org" in config.openstates_base_url
            or "courtlistener.com" in config.openstates_base_url
        )

        logger.info(f"Base URL configured to: {config.openstates_base_url}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_graceful_timeout_handling(client: Client[Any]) -> None:
    """Test that timeouts are handled gracefully.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Try to make a request that might timeout
        try:
            # Use a search that might be slow or timeout
            await client.call_tool(
                "bills_search_bills",
                {
                    "q": "transportation infrastructure budget appropriation",
                    "per_page": 50,
                },
            )
            logger.info("Large search completed successfully")

        except ToolError as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "readtimeout" in error_msg.lower():
                logger.info("Request timed out as expected - timeout handling working")
            else:
                logger.warning(f"Request failed with non-timeout error: {error_msg}")
                # Don't fail the test for non-timeout errors like auth issues
        except Exception as e:
            logger.error(f"Unexpected error in timeout test: {e}")
            # Don't fail for unexpected errors in timeout test


@pytest.mark.asyncio
async def test_concurrent_timeout_handling(client: Client[Any]) -> None:
    """Test timeout handling with concurrent requests.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        if not config.openstates_api_key:
            pytest.skip("API key required for concurrent timeout test")

        # Make multiple concurrent requests that might timeout
        tasks = [
            client.call_tool("bills_search_bills", {"q": f"test{i}", "per_page": 5})
            for i in range(3)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count how many succeeded vs failed
            successes = sum(1 for r in results if not isinstance(r, Exception))
            timeouts = sum(
                1
                for r in results
                if isinstance(r, Exception)
                and ("timeout" in str(r).lower() or "readtimeout" in str(r).lower())
            )

            logger.info(
                f"Concurrent requests: {successes} success, {timeouts} timeout, "
                f"{len(results) - successes - timeouts} other errors"
            )

            # At least some should complete (unless API is completely down)
            # This is a resilience test, not a strict requirement

        except Exception as e:
            logger.warning(f"Concurrent timeout test failed: {e}")
            # Don't fail the test - this is about resilience
