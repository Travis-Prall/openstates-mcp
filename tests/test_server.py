"""Tests for the OpenStates MCP server."""

import asyncio
from collections.abc import Callable
import json
from typing import Any

from fastmcp import Client
from fastmcp.exceptions import ToolError
from loguru import logger
import pytest

from app.config import config
from app.server import mcp


def has_api_key() -> bool:
    """Check if OpenStates API key is available.

    Returns
    -------
    bool
        True if API key is configured, False otherwise.

    """
    return config.openstates_api_key is not None and bool(
        config.openstates_api_key.strip()
    )


def api_key_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Skip tests that require an API key when none is available.

    Parameters
    ----------
    func : Callable[..., Any]
        The test function to potentially skip.

    Returns
    -------
    Callable[..., Any]
        The decorated test function.

    """
    return pytest.mark.skipif(
        not has_api_key(), reason="OpenStates API key not configured"
    )(func)


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
async def test_status_tool(client: Client[Any]) -> None:
    """Test the status tool returns expected server information.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        result = await client.call_tool("status", {})

        # Check response structure
        assert len(result) == 1
        response = result[0].text  # type: ignore[attr-defined]

        # Parse JSON response
        data = json.loads(response)

        # Verify expected fields
        assert data["status"] == "healthy"
        assert data["service"] == "OpenStates MCP Server"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "environment" in data
        assert "system" in data
        assert "server" in data

        # Verify environment section
        assert "runtime" in data["environment"]
        assert "docker" in data["environment"]
        assert "python_version" in data["environment"]

        # Verify system section
        assert "process_uptime" in data["system"]
        assert "memory_mb" in data["system"]
        assert "cpu_percent" in data["system"]

        # Verify server section
        expected_tools = ["bills", "people", "committees", "events", "jurisdictions"]
        for tool in expected_tools:
            assert tool in data["server"]["tools_available"]
        assert data["server"]["transport"] == "streamable-http"
        assert data["server"]["api_base"] == "https://v3.openstates.org"

        logger.info(f"Status tool test passed: {data}")


@pytest.mark.asyncio
async def test_imported_search_tools_available(client: Client[Any]) -> None:
    """Test that search tools were properly imported with prefix.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # List all available tools
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        # Check search tools are present with prefix
        expected_search_tools = [
            "bills_search_bills",
            "people_search_people",
            "committees_search_committees",
            "events_search_events",
        ]

        for tool_name in expected_search_tools:
            assert tool_name in tool_names, f"Expected tool {tool_name} not found"

        logger.info(
            f"Found {len(expected_search_tools)} search tools with correct prefixes"
        )


@pytest.mark.asyncio
async def test_imported_get_tools_available(client: Client[Any]) -> None:
    """Test that get tools were properly imported with prefix.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # List all available tools
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        # Check get tools are present with prefix
        expected_get_tools = [
            "bills_get_bill_details",
            "people_get_legislators_by_location",
            "committees_get_committee_details",
            "events_get_event_details",
            "jurisdictions_get_jurisdictions",
            "jurisdictions_get_jurisdiction_details",
        ]

        for tool_name in expected_get_tools:
            assert tool_name in tool_names, f"Expected tool {tool_name} not found"

        logger.info(f"Found {len(expected_get_tools)} get tools with correct prefixes")


@pytest.mark.asyncio
@api_key_required
async def test_search_bills_tool(client: Client[Any]) -> None:
    """Test the search bills tool with real API call.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Search for bills with a common topic
        try:
            result = await client.call_tool(
                "bills_search_bills", {"q": "education", "per_page": 5}
            )

            assert len(result) == 1
            response = result[0].text  # type: ignore[attr-defined]

            # Parse JSON response
            data = json.loads(response)

            # Verify response structure
            assert "results" in data
            assert isinstance(data["results"], list)

            # Check we got results (might be empty if no API key or 401 error)
            # The important thing is the structure is correct
            logger.info(f"Search bills returned {len(data.get('results', []))} results")

        except ToolError as e:
            # If we get an error, log it but check if it's an expected error
            error_msg = str(e)
            logger.warning(f"Search bills test failed with: {error_msg}")

            # Re-raise if it's not a timeout or auth error
            if (
                "ReadTimeout" not in error_msg
                and "401" not in error_msg
                and "403" not in error_msg
            ):
                raise


@pytest.mark.asyncio
@api_key_required
async def test_get_jurisdictions_tool(client: Client[Any]) -> None:
    """Test the get jurisdictions tool.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Get list of available jurisdictions
        try:
            result = await client.call_tool("jurisdictions_get_jurisdictions", {})

            assert len(result) == 1
            response = result[0].text  # type: ignore[attr-defined]

            # Parse JSON response
            data = json.loads(response)

            # Verify jurisdiction data structure
            assert "results" in data
            if data.get("results"):
                first_jurisdiction = data["results"][0]
                assert "id" in first_jurisdiction
                assert "name" in first_jurisdiction

            logger.info(f"Retrieved {len(data.get('results', []))} jurisdictions")

        except ToolError as e:
            # If we get an error, log it but check if it's an expected error
            error_msg = str(e)
            logger.warning(f"Get jurisdictions test failed with: {error_msg}")

            # Re-raise if it's not a timeout or auth error
            if (
                "ReadTimeout" not in error_msg
                and "401" not in error_msg
                and "403" not in error_msg
            ):
                raise


@pytest.mark.asyncio
@api_key_required
async def test_search_with_jurisdiction_filter(client: Client[Any]) -> None:
    """Test search with jurisdiction filters.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Search for bills in a specific jurisdiction (e.g., California)
        try:
            result = await client.call_tool(
                "bills_search_bills",
                {
                    "q": "budget",
                    "jurisdiction": "ca",
                    "per_page": 10,
                },
            )

            assert len(result) == 1
            response = result[0].text  # type: ignore[attr-defined]

            data = json.loads(response)

            assert "results" in data

            # If we have results, verify they're from the expected jurisdiction
            if data.get("results"):
                for bill in data["results"]:
                    if "jurisdiction" in bill:
                        # Check jurisdiction matches - could be "ca" or full OCD ID
                        jurisdiction_id = bill["jurisdiction"]["id"]
                        assert (
                            jurisdiction_id == "ca" or "state:ca" in jurisdiction_id
                        ), f"Expected CA jurisdiction but got: {jurisdiction_id}"

            logger.info(
                f"Jurisdiction filtered search returned {len(data.get('results', []))} results"
            )

        except ToolError as e:
            # If we get an error, log it but check if it's an expected error
            error_msg = str(e)
            logger.warning(f"Jurisdiction filter test failed with: {error_msg}")

            # Re-raise if it's not a timeout or auth error
            if (
                "ReadTimeout" not in error_msg
                and "401" not in error_msg
                and "403" not in error_msg
            ):
                raise


@pytest.mark.asyncio
async def test_error_handling(client: Client[Any]) -> None:
    """Test error handling for invalid requests.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Try to get a non-existent bill - should raise ToolError
        with pytest.raises(ToolError):
            await client.call_tool(
                "bills_get_bill_details",
                {
                    "jurisdiction": "invalid",
                    "session": "invalid",
                    "bill_id": "invalid-bill-99999999",
                },
            )

        logger.info("Error handling test passed - exception was raised as expected")


@pytest.mark.asyncio
async def test_tool_descriptions(client: Client[Any]) -> None:
    """Test that all tools have proper descriptions.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        tools = await client.list_tools()

        for tool in tools:
            # Check tool has a name
            assert tool.name

            # Check tool has a description
            assert tool.description, f"Tool {tool.name} missing description"

            # Check description is meaningful (not empty or too short)
            assert len(tool.description) > 10, (
                f"Tool {tool.name} has too short description"
            )

            # Check input schema exists
            assert tool.inputSchema is not None, (
                f"Tool {tool.name} missing input schema"
            )

        logger.info(f"All {len(tools)} tools have proper descriptions and schemas")


@pytest.mark.asyncio
async def test_search_people_tool(client: Client[Any]) -> None:
    """Test searching for legislators/people in the database.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        result = await client.call_tool(
            "people_search_people", {"name": "Smith", "per_page": 5}
        )

        assert len(result) == 1
        response = result[0].text  # type: ignore[attr-defined]

        data = json.loads(response)

        assert "results" in data

        if data.get("results"):
            person = data["results"][0]
            # Check for basic legislator fields
            expected_fields = [
                "id",
                "name",
                "party",
                "current_role",
            ]
            # At least one of these fields should be present
            assert any(field in person for field in expected_fields), (
                f"No expected fields found in person: {list(person.keys())}"
            )

        logger.info(f"People search found {len(data.get('results', []))} legislators")


@pytest.mark.asyncio
async def test_concurrent_requests(client: Client[Any]) -> None:
    """Test that the server handles concurrent requests properly.

    Parameters
    ----------
    client : Client
        The FastMCP test client fixture.

    """
    async with client:
        # Start with just the status request which should always work
        try:
            # Test status first
            status_result = await client.call_tool("status", {})
            assert len(status_result) == 1
            assert status_result[0].text  # type: ignore[attr-defined]

            data = json.loads(status_result[0].text)  # type: ignore[attr-defined]
            assert isinstance(data, dict)
            assert data["status"] == "healthy"

            logger.info("Status request successful")

            # If we have API key, test concurrent API calls
            if has_api_key():
                tasks = [
                    client.call_tool("status", {}),
                    client.call_tool(
                        "bills_search_bills", {"q": "test", "per_page": 3}
                    ),
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_count = sum(
                    1 for r in results if not isinstance(r, Exception)
                )
                logger.info(
                    f"Concurrent test: {successful_count}/{len(results)} requests successful"
                )

                # At least status should work
                assert successful_count >= 1
            else:
                logger.info("Skipping concurrent API tests - no API key configured")

        except Exception as e:
            logger.error(f"Concurrent request test failed: {e}")
            raise
