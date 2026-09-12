"""Bills and legislation tools for OpenStates MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from app.tools.common import log_info, request_json

# Create the bills server
bills_server: FastMCP[Any] = FastMCP(
    name="OpenStates Bills Server",
    instructions="Bills and legislation server for OpenStates legislative database providing comprehensive search capabilities. "
    "This server enables searching for bills and legislation by query, jurisdiction, session, subject, or sponsor. "
    "It also provides detailed information about specific bills including full text, sponsors, votes, and legislative history. "
    "Use this server for tracking legislation, researching policy topics, and monitoring legislative activity across states.",
)


@bills_server.tool()
async def search_bills(
    *,
    jurisdiction: Annotated[
        str | None, Field(description="Filter by jurisdiction name or ID")
    ] = None,
    session: Annotated[
        str | None, Field(description="Filter by session identifier")
    ] = None,
    chamber: Annotated[
        str | None, Field(description="Filter by chamber of origination")
    ] = None,
    identifier: Annotated[
        list[str] | None,
        Field(description="Filter to only include bills with these identifiers"),
    ] = None,
    classification: Annotated[
        str | None,
        Field(description="Filter by classification, e.g. bill or resolution"),
    ] = None,
    subject: Annotated[
        list[str] | None, Field(description="Filter by one or more subjects")
    ] = None,
    updated_since: Annotated[
        str | None,
        Field(
            description="Filter to only include bills with updates since a given date"
        ),
    ] = None,
    created_since: Annotated[
        str | None,
        Field(description="Filter to only include bills created since a given date"),
    ] = None,
    action_since: Annotated[
        str | None,
        Field(
            description="Filter to only include bills with an action since a given date"
        ),
    ] = None,
    sort: Annotated[
        str, Field(description="Desired sort order for bill results")
    ] = "updated_desc",
    sponsor: Annotated[
        str | None,
        Field(
            description="Filter to only include bills sponsored by a given name or person ID"
        ),
    ] = None,
    sponsor_classification: Annotated[
        str | None,
        Field(
            description="Filter matched sponsors to only include particular types of sponsorships"
        ),
    ] = None,
    q: Annotated[
        str | None, Field(description="Filter by full text search term")
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
    """Search for bills matching given criteria.

    Must either specify a jurisdiction or a full text query (q). Additional parameters will
    further restrict bills returned.

    Args:
        jurisdiction: Filter by jurisdiction name or ID.
        session: Filter by session identifier.
        chamber: Filter by chamber of origination.
        identifier: Filter to only include bills with these identifiers.
        classification: Filter by classification, e.g. bill or resolution.
        subject: Filter by one or more subjects.
        updated_since: Filter to only include bills with updates since a given date.
        created_since: Filter to only include bills created since a given date.
        action_since: Filter to only include bills with an action since a given date.
        sort: Desired sort order for bill results.
        sponsor: Filter to only include bills sponsored by a given name or person ID.
        sponsor_classification: Filter matched sponsors to only include particular types of sponsorships.
        q: Filter by full text search term.
        include: Additional information to include in response.
        page: Page number for pagination (default: 1).
        per_page: Results per page (1-100, default: 10).
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Search results containing bills and metadata.

    """
    await log_info(
        ctx, f"Searching bills with jurisdiction: {jurisdiction}, query: {q}"
    )

    params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}

    param_fields = {
        "jurisdiction": jurisdiction,
        "session": session,
        "chamber": chamber,
        "classification": classification,
        "updated_since": updated_since,
        "created_since": created_since,
        "action_since": action_since,
        "sort": sort,
        "sponsor": sponsor,
        "sponsor_classification": sponsor_classification,
        "q": q,
    }

    # Handle list parameters
    if identifier:
        params["identifier"] = list(identifier)
    if subject:
        params["subject"] = list(subject)
    if include:
        params["include"] = list(include)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})

    data = await request_json("bills", params=params, ctx=ctx)
    await log_info(ctx, f"Found {len(data.get('results', []))} bills")
    return data


@bills_server.tool()
async def get_bill_by_id(
    bill_uuid: Annotated[
        str,
        Field(
            description="OpenStates bill UUID (just the UUID part, not the full ocd-bill/{uuid})"
        ),
    ],
    include: Annotated[
        list[str] | None,
        Field(description="Additional information to include in response"),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Obtain bill information by internal OpenStates UUID.

    Args:
        bill_uuid: OpenStates bill UUID (just the UUID part, not the full ocd-bill/{uuid}).
        include: Additional information to include in response.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Detailed bill information including text, sponsors, votes, and history.

    """
    await log_info(ctx, f"Getting bill by UUID: {bill_uuid}")

    params: dict[str, Any] = {}
    if include:
        params["include"] = list(include)

    data = await request_json(f"bills/ocd-bill/{bill_uuid}", params=params, ctx=ctx)
    await log_info(ctx, f"Successfully retrieved bill {bill_uuid}")
    return data


@bills_server.tool()
async def get_bill_details(
    jurisdiction: Annotated[
        str, Field(description="Jurisdiction identifier (e.g., 'ny', 'ca', 'tx')")
    ],
    session: Annotated[str, Field(description="Legislative session identifier")],
    bill_id: Annotated[
        str, Field(description="Bill identifier (e.g., 'HB123', 'SB456')")
    ],
    include: Annotated[
        list[str] | None,
        Field(description="Additional information to include in response"),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Obtain bill information based on (jurisdiction, session, bill_id).

    Args:
        jurisdiction: Jurisdiction identifier (e.g., 'ny', 'ca', 'tx').
        session: Legislative session identifier.
        bill_id: Bill identifier (e.g., 'HB123', 'SB456').
        include: Additional information to include in response.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Detailed bill information including text, sponsors, votes, and history.

    """
    await log_info(ctx, f"Getting bill details: {jurisdiction}/{session}/{bill_id}")

    params: dict[str, Any] = {}
    if include:
        params["include"] = list(include)

    data = await request_json(
        f"bills/{jurisdiction}/{session}/{bill_id}", params=params, ctx=ctx
    )
    await log_info(
        ctx, f"Successfully retrieved bill {jurisdiction}/{session}/{bill_id}"
    )
    return data
