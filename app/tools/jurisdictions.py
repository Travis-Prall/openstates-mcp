"""Jurisdictions and states tools for OpenStates MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from app.tools.common import log_info, request_json

# Create the jurisdictions server
jurisdictions_server: FastMCP[Any] = FastMCP(
    name="OpenStates Jurisdictions Server",
    instructions="Jurisdictions and states server for OpenStates legislative database providing access to jurisdiction information. "
    "This server enables retrieving information about available jurisdictions (states, territories, municipalities) and "
    "detailed metadata for specific jurisdictions. Use this server for understanding the scope of available data "
    "and getting information about state legislative systems.",
)


@jurisdictions_server.tool()
async def get_jurisdictions(
    *,
    classification: Annotated[
        str | None, Field(description="Filter returned jurisdictions by type")
    ] = None,
    include: Annotated[
        list[str] | None,
        Field(description="Additional information to include in response"),
    ] = None,
    page: Annotated[
        int, Field(description="Page number for pagination (default: 1)")
    ] = 1,
    per_page: Annotated[
        int, Field(description="Results per page (1-100, default: 52)")
    ] = 52,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get list of available jurisdictions (states, territories, municipalities).

    Args:
        classification: Filter returned jurisdictions by type.
        include: Additional information to include in response.
        page: Page number for pagination (default: 1).
        per_page: Results per page (1-100, default: 52).
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: List of available jurisdictions with basic information.

    """
    await log_info(
        ctx, f"Getting list of jurisdictions with classification: {classification}"
    )

    params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}

    if classification:
        params["classification"] = classification
    if include:
        params["include"] = list(include)

    data = await request_json("jurisdictions", params=params, ctx=ctx)
    await log_info(ctx, f"Found {len(data.get('results', []))} jurisdictions")
    return data


@jurisdictions_server.tool()
async def get_jurisdiction_details(
    jurisdiction_id: Annotated[
        str, Field(description="Jurisdiction identifier (e.g., 'ny', 'ca', 'tx')")
    ],
    include: Annotated[
        list[str] | None,
        Field(description="Additional includes for the Jurisdiction response"),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get detailed metadata for a specific jurisdiction.

    Args:
        jurisdiction_id: Jurisdiction identifier (e.g., 'ny', 'ca', 'tx').
        include: Additional includes for the Jurisdiction response.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Detailed jurisdiction information including legislative structure.

    """
    await log_info(ctx, f"Getting jurisdiction details for: {jurisdiction_id}")

    params: dict[str, Any] = {}
    if include:
        params["include"] = list(include)

    data = await request_json(
        f"jurisdictions/{jurisdiction_id}", params=params, ctx=ctx
    )
    await log_info(ctx, f"Successfully retrieved jurisdiction {jurisdiction_id}")
    return data
