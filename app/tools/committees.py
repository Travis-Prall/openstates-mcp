"""Committees tools for OpenStates MCP server."""

from typing import Annotated, Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
import httpx
from loguru import logger
from pydantic import Field

from app.config import config

# Load environment variables
load_dotenv()

# Create the committees server
committees_server: FastMCP[Any] = FastMCP(
    name="OpenStates Committees Server",
    instructions="Committees server for OpenStates legislative database providing access to committee information. "
    "This server enables searching for legislative committees by jurisdiction and chamber, as well as getting "
    "detailed information about specific committees. Use this server for researching committee structure, "
    "membership, and legislative oversight responsibilities.",
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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Searching committees for jurisdiction: {jurisdiction}")

    try:
        api_key = _validate_api_key()
    except ValueError as e:
        await _log_error(ctx, str(e))
        raise ValueError(e)

    # Build parameters dict according to OpenAPI spec
    params = {"page": page, "per_page": min(per_page, 100)}

    # Add all parameters as per OpenAPI spec
    param_fields = {
        "jurisdiction": jurisdiction,
        "classification": classification,
        "parent": parent,
        "chamber": chamber,
    }

    # Handle list parameters
    if include:
        for item in include:
            params.setdefault("include", []).append(item)

    # Add non-list parameters
    params.update({key: value for key, value in param_fields.items() if value})
    headers = {"x-api-key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v3.openstates.org/committees",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            await _log_info(ctx, f"Found {len(data.get('results', []))} committees")
            return data

    except Exception as e:
        await _handle_api_error(ctx, e)


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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting committee details for: {committee_id}")

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
                f"https://v3.openstates.org/committees/{committee_id}",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(ctx, f"Successfully retrieved committee {committee_id}")
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)
