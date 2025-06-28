"""People and legislators tools for OpenStates MCP server."""

from typing import Annotated, Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
import httpx
from loguru import logger
from pydantic import Field

from app.config import config

# Load environment variables
load_dotenv()

# Create the people server
people_server: FastMCP[Any] = FastMCP(
    name="OpenStates People Server",
    instructions="People and legislators server for OpenStates legislative database providing access to legislator information. "
    "This server enables searching for legislators, governors, and other political figures, as well as finding legislators "
    "by geographic location. Use this server for researching elected officials, their roles, districts, and contact information.",
)


def _validate_api_key() -> str:
    """Validate that API key is available.

    Returns:
        str: The API key.

    Raises:
        ValueError: If openstates_api_key is not found.

    """
    if not config.openstates_api_key:
        raise ValueError("OPENSTATES_API_KEY not found in environment variables")
    return config.openstates_api_key


async def _log_info(ctx: Context | None, message: str) -> None:
    """Log info message to context or logger."""
    if ctx:
        await ctx.info(message)
    else:
        logger.info(message)


async def _log_error(ctx: Context | None, message: str) -> None:
    """Log error message to context or logger."""
    if ctx:
        await ctx.error(message)
    else:
        logger.error(message)


async def _handle_api_error(ctx: Context | None, error: Exception) -> None:
    """Handle API errors with appropriate logging."""
    if isinstance(error, httpx.HTTPStatusError):
        error_msg = f"HTTP error: {error}"
    else:
        error_msg = f"API error: {error}"

    await _log_error(ctx, error_msg)
    raise error


@people_server.tool()
async def search_people(
    *,
    jurisdiction: Annotated[
        str | None, Field(description="Filter by jurisdiction name or id")
    ] = None,
    name: Annotated[
        str | None, Field(description="Filter by name, case-insensitive match")
    ] = None,
    id: Annotated[
        list[str] | None,
        Field(
            description="Filter by id, can be specified multiple times for multiple people"
        ),
    ] = None,
    org_classification: Annotated[
        str | None, Field(description="Filter by current role")
    ] = None,
    district: Annotated[
        str | None, Field(description="Filter by district name")
    ] = None,
    include: Annotated[
        list[str] | None,
        Field(description="Additional information to include in response"),
    ] = None,
    page: Annotated[
        int, Field(description="Page number for pagination (default: 1)")
    ] = 1,
    per_page: Annotated[
        int, Field(description="Results per page (1-100, default: 10)")
    ] = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get list of people matching selected criteria.

    Must provide either jurisdiction, name, or one or more id parameters.

    Args:
        jurisdiction: Filter by jurisdiction name or id.
        name: Filter by name, case-insensitive match.
        id: Filter by id, can be specified multiple times for multiple people.
        org_classification: Filter by current role.
        district: Filter by district name.
        include: Additional information to include in response.
        page: Page number for pagination (default: 1).
        per_page: Results per page (1-100, default: 10).
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Search results containing people and metadata.

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(
        ctx, f"Searching people with jurisdiction: {jurisdiction}, name: {name}"
    )

    try:
        api_key = _validate_api_key()
    except ValueError as e:
        await _log_error(ctx, str(e))
        raise

    # Build parameters dict according to OpenAPI spec
    params = {"page": page, "per_page": min(per_page, 100)}

    # Add all parameters as per OpenAPI spec
    param_fields = {
        "jurisdiction": jurisdiction,
        "name": name,
        "org_classification": org_classification,
        "district": district,
    }

    # Handle list parameters
    if id:
        for item in id:
            params.setdefault("id", []).append(item)
    if include:
        for item in include:
            params.setdefault("include", []).append(item)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})
    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.openstates.org/people",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            await _log_info(ctx, f"Found {len(data.get('results', []))} people")
            return data

    except Exception as e:
        await _handle_api_error(ctx, e)


@people_server.tool()
async def get_legislators_by_location(
    latitude: Annotated[float, Field(description="Latitude coordinate")],
    longitude: Annotated[float, Field(description="Longitude coordinate")],
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Find legislators representing a specific geographic location.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Legislators representing the given location.

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting legislators for location: {latitude}, {longitude}")

    try:
        api_key = _validate_api_key()
    except ValueError as e:
        await _log_error(ctx, str(e))
        raise

    params = {"lat": latitude, "lng": longitude}
    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.openstates.org/people.geo",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(ctx, "Successfully retrieved legislators for location")
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)
