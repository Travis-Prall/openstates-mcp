#!/usr/bin/env python3
"""OpenStates MCP Server - FastMCP Implementation."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys
import tomllib
from typing import Any

from fastmcp import FastMCP
from loguru import logger
import psutil

from app.config import config
from app.tools import (
    bills_server,
    committees_server,
    events_server,
    jurisdictions_server,
    people_server,
)

# Configure logging
log_path = Path(__file__).parent / "logs" / "server.log"
log_path.parent.mkdir(exist_ok=True)
logger.add(log_path, rotation="1 MB", retention="1 week")


def get_version() -> str:
    """Get the version from pyproject.toml.

    Returns:
        The version string from pyproject.toml or 'unknown' if not found.

    """
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


def is_docker() -> bool:
    """Check if running inside a Docker container.

    Returns:
        True if running inside Docker, False otherwise.

    """
    return Path("/.dockerenv").exists() or (
        Path("/proc/1/cgroup").exists()
        and any(
            "docker" in line for line in Path("/proc/1/cgroup").open(encoding="utf-8")
        )
    )


# Create main server instance
mcp: FastMCP[Any] = FastMCP(
    name="OpenStates MCP Server",
    instructions="Model Context Protocol server providing LLMs with access to the OpenStates legislative database. "
    "This server enables searching for bills, legislators, committees, events, and jurisdictions across all US states. "
    "It provides comprehensive access to legislative data including bill text, voting records, committee information, "
    "and legislator details. Available tools include: search operations for bills/people/committees/events, "
    "get operations for specific records by ID, and jurisdiction/location-based lookups.",
)


@mcp.tool()
def status() -> dict[str, Any]:
    """Check the status of the OpenStates MCP server.

    Returns:
        A dictionary containing server status, system metrics, and service information.

    """
    logger.info("Status check requested")

    # Get system info using psutil
    process = psutil.Process()
    process_start = datetime.fromtimestamp(process.create_time(), tz=UTC)
    uptime_seconds = (datetime.now(UTC) - process_start).total_seconds()

    # Format uptime as human readable
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Docker and environment info
    docker_info = is_docker()
    environment = "docker" if docker_info else "native"

    return {
        "status": "healthy",
        "service": "OpenStates MCP Server",
        "version": get_version(),
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": {
            "runtime": environment,
            "docker": docker_info,
            "python_version": sys.version.split()[0],
        },
        "system": {
            "process_uptime": uptime,
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
            "cpu_percent": round(process.cpu_percent(interval=0.1), 1),
        },
        "server": {
            "tools_available": [
                "bills",
                "people",
                "committees",
                "events",
                "jurisdictions",
            ],
            "transport": "streamable-http",
            "api_base": "https://v3.openstates.org",
            "host": config.host,
            "port": config.mcp_port,
            "api_configured": bool(config.openstates_api_key),
        },
    }


async def setup() -> None:
    """Set up the server by importing subservers."""
    logger.info("Setting up OpenStates MCP server")

    # Import bills tools with prefix
    await mcp.import_server("bills", bills_server)
    logger.info("Imported bills server tools")

    # Import people tools with prefix
    await mcp.import_server("people", people_server)
    logger.info("Imported people server tools")

    # Import committees tools with prefix
    await mcp.import_server("committees", committees_server)
    logger.info("Imported committees server tools")

    # Import events tools with prefix
    await mcp.import_server("events", events_server)
    logger.info("Imported events server tools")

    # Import jurisdictions tools with prefix
    await mcp.import_server("jurisdictions", jurisdictions_server)
    logger.info("Imported jurisdictions server tools")

    logger.info("Server setup complete")


# Run setup when module is imported
asyncio.run(setup())


async def main() -> None:
    """Run the OpenStates MCP server with streamable-http transport."""
    logger.info("Starting OpenStates MCP server with streamable-http transport")
    logger.info(
        f"Server configuration: host={config.host}, port={config.mcp_port}, log_level={config.openstates_log_level}"
    )

    if not config.openstates_api_key:
        logger.warning(
            "OPENSTATES_API_KEY not configured - some features may be limited"
        )

    try:
        await mcp.run_async(
            transport="streamable-http",
            host=config.host,
            port=config.mcp_port,
            path="/mcp/",
            log_level=config.openstates_log_level.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise e


if __name__ == "__main__":
    logger.info("Starting OpenStates MCP server")
    asyncio.run(main())
