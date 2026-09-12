"""People and legislators tools for OpenStates MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from app.tools.common import log_info, request_json

# Create the people server
people_server: FastMCP[Any] = FastMCP(
    name="OpenStates People Server",
    instructions="People and legislators server for OpenStates legislative database providing access to legislator information. "
    "This server enables searching for legislators, governors, and other political figures, as well as finding legislators "
    "by geographic location. Use this server for researching elected officials, their roles, districts, and contact information.",
)


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

    """
    await log_info(
        ctx, f"Searching people with jurisdiction: {jurisdiction}, name: {name}"
    )

    params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}

    param_fields = {
        "jurisdiction": jurisdiction,
        "name": name,
        "org_classification": org_classification,
        "district": district,
    }

    # Handle list parameters
    if id:
        params["id"] = list(id)
    if include:
        params["include"] = list(include)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})

    data = await request_json("people", params=params, ctx=ctx)
    await log_info(ctx, f"Found {len(data.get('results', []))} people")
    return data


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

    """
    await log_info(ctx, f"Getting legislators for location: {latitude}, {longitude}")

    params = {"lat": latitude, "lng": longitude}

    data = await request_json("people.geo", params=params, ctx=ctx)
    await log_info(ctx, "Successfully retrieved legislators for location")
    return data
