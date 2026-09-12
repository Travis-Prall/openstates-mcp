"""Committees tools for OpenStates MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from app.tools.common import log_info, request_json

# Create the committees server
committees_server: FastMCP[Any] = FastMCP(
    name="OpenStates Committees Server",
    instructions="Committees server for OpenStates legislative database providing access to committee information. "
    "This server enables searching for legislative committees by jurisdiction and chamber, as well as getting "
    "detailed information about specific committees. Use this server for researching committee structure, "
    "membership, and legislative oversight responsibilities.",
)


@committees_server.tool()
async def search_committees(
    *,
    jurisdiction: Annotated[
        str | None,
        Field(description="Filter by jurisdiction name or ID"),
    ] = None,
    classification: Annotated[
        str | None,
        Field(
            description="Committee classification (e.g., 'committee', 'subcommittee')"
        ),
    ] = None,
    parent: Annotated[
        str | None, Field(description="ocd-organization ID of parent committee")
    ] = None,
    chamber: Annotated[
        str | None, Field(description="Chamber of committee, generally upper or lower")
    ] = None,
    include: Annotated[
        list[str] | None,
        Field(description="Additional includes for the Committee response"),
    ] = None,
    page: Annotated[
        int, Field(description="Page number for pagination (default: 1)")
    ] = 1,
    per_page: Annotated[
        int, Field(description="Results per page (1-100, default: 20)")
    ] = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Search for legislative committees by jurisdiction and chamber.

    Args:
        jurisdiction: Filter by jurisdiction name or ID.
        classification: Committee classification (e.g., 'committee', 'subcommittee').
        parent: ocd-organization ID of parent committee.
        chamber: Chamber of committee, generally upper or lower.
        include: Additional includes for the Committee response.
        page: Page number for pagination (default: 1).
        per_page: Results per page (1-100, default: 20).
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Search results containing committees and metadata.

    """
    await log_info(ctx, f"Searching committees for jurisdiction: {jurisdiction}")

    params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}

    param_fields = {
        "jurisdiction": jurisdiction,
        "classification": classification,
        "parent": parent,
        "chamber": chamber,
    }

    # Handle list parameters
    if include:
        params["include"] = list(include)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})

    data = await request_json("committees", params=params, ctx=ctx)
    await log_info(ctx, f"Found {len(data.get('results', []))} committees")
    return data


@committees_server.tool()
async def get_committee_details(
    committee_id: Annotated[str, Field(description="Committee internal ID")],
    include: Annotated[
        list[str] | None,
        Field(description="Additional includes for the Committee response"),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific committee.

    Args:
        committee_id: Committee internal ID.
        include: Additional includes for the Committee response.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Detailed committee information including membership.

    """
    await log_info(ctx, f"Getting committee details for: {committee_id}")

    params: dict[str, Any] = {}
    if include:
        params["include"] = list(include)

    data = await request_json(f"committees/{committee_id}", params=params, ctx=ctx)
    await log_info(ctx, f"Successfully retrieved committee {committee_id}")
    return data
