"""Jurisdictions and states tools for OpenStates MCP server."""

from typing import Annotated, Any

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
import httpx
from loguru import logger
from pydantic import Field

from app.config import config

# Load environment variables
load_dotenv()

# Create the jurisdictions server
jurisdictions_server: FastMCP[Any] = FastMCP(
    name="OpenStates Jurisdictions Server",
    instructions="Jurisdictions and states server for OpenStates legislative database providing access to jurisdiction information. "
    "This server enables retrieving information about available jurisdictions (states, territories, municipalities) and "
    "detailed metadata for specific jurisdictions. Use this server for understanding the scope of available data "
    "and getting information about state legislative systems.",
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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(
        ctx, f"Getting list of jurisdictions with classification: {classification}"
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
        "classification": classification,
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
                "https://v3.openstates.org/jurisdictions",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            await _log_info(ctx, f"Found {len(data.get('results', []))} jurisdictions")
            return data

    except Exception as e:
        await _handle_api_error(ctx, e)


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

    Raises:
        ValueError: If OPEN_STATES_API_KEY is not found in environment variables.

    """
    await _log_info(ctx, f"Getting jurisdiction details for: {jurisdiction_id}")

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
                f"https://v3.openstates.org/jurisdictions/{jurisdiction_id}",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            await _log_info(
                ctx, f"Successfully retrieved jurisdiction {jurisdiction_id}"
            )
            return response.json()

    except Exception as e:
        await _handle_api_error(ctx, e)
