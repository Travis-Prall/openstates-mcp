"""Events and hearings tools for OpenStates MCP server."""

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from app.tools.common import log_info, request_json

# Create the events server
events_server: FastMCP[Any] = FastMCP(
    name="OpenStates Events Server",
    instructions="Events and hearings server for OpenStates legislative database providing access to legislative events. "
    "This server enables searching for legislative events, hearings, and meetings by jurisdiction and date range, "
    "as well as retrieving detailed information about specific events. Use this server for tracking legislative "
    "calendars, committee hearings, and public meetings.",
)


@events_server.tool()
async def search_events(
    *,
    jurisdiction: Annotated[
        str | None,
        Field(description="Filter by jurisdiction name or ID"),
    ] = None,
    deleted: Annotated[
        bool, Field(description="Return events marked as deleted?")
    ] = False,
    before: Annotated[
        str | None,
        Field(description="Limit results to those starting before a given datetime"),
    ] = None,
    after: Annotated[
        str | None,
        Field(description="Limit results to those starting after a given datetime"),
    ] = None,
    require_bills: Annotated[
        bool, Field(description="Limit results to events with associated bills")
    ] = False,
    include: Annotated[
        list[str] | None,
        Field(description="Additional includes for the Event response"),
    ] = None,
    page: Annotated[
        int, Field(description="Page number for pagination (default: 1)")
    ] = 1,
    per_page: Annotated[
        int, Field(description="Results per page (1-100, default: 20)")
    ] = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Search for legislative events, hearings, and meetings.

    Args:
        jurisdiction: Filter by jurisdiction name or ID.
        deleted: Return events marked as deleted?
        before: Limit results to those starting before a given datetime.
        after: Limit results to those starting after a given datetime.
        require_bills: Limit results to events with associated bills.
        include: Additional includes for the Event response.
        page: Page number for pagination (default: 1).
        per_page: Results per page (1-100, default: 20).
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Search results containing events and metadata.

    """
    await log_info(ctx, f"Searching events for jurisdiction: {jurisdiction}")

    params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}

    param_fields = {
        "jurisdiction": jurisdiction,
        "deleted": deleted,
        "before": before,
        "after": after,
        "require_bills": require_bills,
    }

    # Handle list parameters
    if include:
        params["include"] = list(include)

    # Add non-list parameters
    params.update({
        key: value for key, value in param_fields.items() if value is not None
    })

    data = await request_json("events", params=params, ctx=ctx)
    await log_info(ctx, f"Found {len(data.get('results', []))} events")
    return data


@events_server.tool()
async def get_event_details(
    event_id: Annotated[str, Field(description="Event internal ID")],
    include: Annotated[
        list[str] | None,
        Field(description="Additional includes for the Event response"),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific legislative event.

    Args:
        event_id: Event internal ID.
        include: Additional includes for the Event response.
        ctx: Optional context for logging and error reporting.

    Returns:
        dict: Detailed event information including agenda and participants.

    """
    await log_info(ctx, f"Getting event details for: {event_id}")

    params: dict[str, Any] = {}
    if include:
        params["include"] = list(include)

    data = await request_json(f"events/{event_id}", params=params, ctx=ctx)
    await log_info(ctx, f"Successfully retrieved event {event_id}")
    return data
