"""Simple validation tests to check basic server functionality."""

import asyncio
import importlib
import json
from typing import Any

from fastmcp import Client, FastMCP
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
async def test_mounted_tool_names_are_namespaced(client: Client[Any]) -> None:
    """Sub-servers expose stable, prefixed tool names.

    Guards the synchronous ``mount()`` registration: every tool must stay
    namespaced by its sub-server prefix exactly as before.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        names = {tool.name for tool in await client.list_tools()}

    expected = {
        "status",
        "bills_search_bills",
        "bills_get_bill_by_id",
        "bills_get_bill_details",
        "people_search_people",
        "people_get_legislators_by_location",
        "committees_search_committees",
        "committees_get_committee_details",
        "events_search_events",
        "events_get_event_details",
        "jurisdictions_get_jurisdictions",
        "jurisdictions_get_jurisdiction_details",
    }

    assert expected <= names, f"Missing tools: {sorted(expected - names)}"


@pytest.mark.asyncio
async def test_importing_server_inside_running_loop_is_safe() -> None:
    """``app.server`` imports without needing or forbidding an event loop.

    The module used to call ``asyncio.run(setup())`` at import time, which blew
    up with ``RuntimeError`` whenever it was imported from running async code
    (ASGI servers, test runners). Registration is synchronous now.

    """
    module = importlib.reload(importlib.import_module("app.server"))

    assert isinstance(module.mcp, FastMCP)
    assert callable(module.create_app)

    # Prove we really are inside a running event loop.
    await asyncio.sleep(0)


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
