"""Bills and legislation tools for OpenStates MCP server."""

from typing import Annotated, Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
import httpx
from loguru import logger
from pydantic import Field

from app.config import config

# Load environment variables
load_dotenv()

# Create the bills server
bills_server: FastMCP[Any] = FastMCP(
    name="OpenStates Bills Server",
    instructions="Bills and legislation server for OpenStates legislative database providing comprehensive search capabilities. "
    "This server enables searching for bills and legislation by query, jurisdiction, session, subject, or sponsor. "
    "It also provides detailed information about specific bills including full text, sponsors, votes, and legislative history. "
    "Use this server for tracking legislation, researching policy topics, and monitoring legislative activity across states.",
)


def _validate_api_key() -> str:
    """Validate that API key is available.

    Returns:
        The OpenStates API key.

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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(
        ctx, f"Searching bills with jurisdiction: {jurisdiction}, query: {q}"
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
        for item in identifier:
            params.setdefault("identifier", []).append(item)
    if subject:
        for item in subject:
            params.setdefault("subject", []).append(item)
    if include:
        for item in include:
            params.setdefault("include", []).append(item)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})
    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.openstates.org/bills",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            await _log_info(ctx, f"Found {len(data.get('results', []))} bills")
            return data

    except Exception as e:
        await _handle_api_error(ctx, e)


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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting bill by UUID: {bill_uuid}")

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
                f"https://v3.openstates.org/bills/ocd-bill/{bill_uuid}",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(ctx, f"Successfully retrieved bill {bill_uuid}")
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)


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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting bill details: {jurisdiction}/{session}/{bill_id}")

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
                f"https://v3.openstates.org/bills/{jurisdiction}/{session}/{bill_id}",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(
                ctx, f"Successfully retrieved bill {jurisdiction}/{session}/{bill_id}"
            )
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)
