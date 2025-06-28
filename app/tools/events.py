"""Events and hearings tools for OpenStates MCP server."""

from typing import Annotated, Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
import httpx
from loguru import logger
from pydantic import Field

from app.config import config

# Load environment variables
load_dotenv()

# Create the events server
events_server: FastMCP[Any] = FastMCP(
    name="OpenStates Events Server",
    instructions="Events and hearings server for OpenStates legislative database providing access to legislative events. "
    "This server enables searching for legislative events, hearings, and meetings by jurisdiction and date range, "
    "as well as retrieving detailed information about specific events. Use this server for tracking legislative "
    "calendars, committee hearings, and public meetings.",
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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Searching events for jurisdiction: {jurisdiction}")

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
        "deleted": deleted,
        "before": before,
        "after": after,
        "require_bills": require_bills,
    }

    # Handle list parameters
    if include:
        for item in include:
            params.setdefault("include", []).append(item)

    # Add non-list parameters
    params.update({
        key: value for key, value in param_fields.items() if value is not None
    })
    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.openstates.org/events",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            await _log_info(ctx, f"Found {len(data.get('results', []))} events")
            return data

    except Exception as e:
        await _handle_api_error(ctx, e)


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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting event details for: {event_id}")

    try:
        api_key = _validate_api_key()
    except ValueError as e:
        await _log_error(ctx, str(e))
        raise

    params = {}
    if include:
        params["include"] = include

    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://v3.openstates.org/events/{event_id}",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(ctx, f"Successfully retrieved event {event_id}")
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)
