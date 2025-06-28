"""Simple validation tests to check basic server functionality."""

import json
from typing import Any

from fastmcp import Client
from loguru import logger
import pytest

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
async def test_server_status_basic(client: Client[Any]) -> None:
    """Test basic server status functionality.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        result = await client.call_tool("status", {})

        # Check basic response structure
        assert len(result) == 1
        response = result[0].text  # type: ignore[attr-defined]
        assert response is not None

        # Parse JSON
        data = json.loads(response)

        # Check essential fields
        assert data["status"] == "healthy"
        assert data["service"] == "OpenStates MCP Server"
        assert "version" in data

        logger.info("Basic status test passed")


@pytest.mark.asyncio
async def test_tools_list_basic(client: Client[Any]) -> None:
    """Test that we can list available tools.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        tools = await client.list_tools()

        # Should have some tools
        assert len(tools) > 0

        # Check for essential tools
        tool_names = [tool.name for tool in tools]
        assert "status" in tool_names

        # Check for some API tools (even if they might not work without API key)
        api_tools = [
            name
            for name in tool_names
            if name.startswith(("bills_", "people_", "jurisdictions_"))
        ]
        assert len(api_tools) > 0

        logger.info(f"Found {len(tools)} tools, including {len(api_tools)} API tools")


@pytest.mark.asyncio
async def test_tool_schemas_basic(client: Client[Any]) -> None:
    """Test that tools have proper schemas.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        tools = await client.list_tools()

        for tool in tools:
            # Each tool should have basic properties
            assert tool.name
            assert tool.description
            assert tool.inputSchema is not None

            # Input schema should be a dict
            assert isinstance(tool.inputSchema, dict)

        logger.info("All tools have proper schemas")
