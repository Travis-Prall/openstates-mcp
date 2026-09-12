#!/usr/bin/env python3
"""OpenStates MCP Server - FastMCP Implementation.

The server exposes OpenStates legislative tools over the Model Context
Protocol. In production it runs as an async, standalone Linux service speaking
Streamable HTTP through an ASGI app (served by uvicorn) so that it can sit
behind a reverse proxy or container orchestrator. A stdio transport is also
available for local, single-client MCP integrations.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
import sys
import tomllib
from typing import Any

from fastmcp import FastMCP
from loguru import logger
import psutil
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
import uvicorn

from app import __version__
from app.config import config
from app.middleware import OriginGuardMiddleware, PathAliasMiddleware
from app.tools import (
    bills_server,
    committees_server,
    events_server,
    jurisdictions_server,
    people_server,
)

#: Human readable service name used in status and health payloads.
SERVICE_NAME = "OpenStates MCP Server"

#: Prefixes used to namespace every tool exposed by a sub-server.
SUB_SERVER_PREFIXES = ("bills", "people", "committees", "events", "jurisdictions")

#: HTTP path of the unauthenticated health probe used by orchestrators.
HEALTH_PATH = "/healthz"


def configure_logging(directory: Path | None = None) -> Path | None:
    """Attach a rotating file sink for the server.

    Args:
        directory: Log directory override. Defaults to configuration.

    Returns:
        Path of the log file, or ``None`` when no file sink could be created
        (for example on a read-only container filesystem).

    """
    log_dir = directory or config.resolved_log_dir
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "server.log"
        logger.add(log_path, rotation="1 MB", retention="1 week")
    except OSError as error:
        logger.warning(f"File logging disabled: could not write to {log_dir}: {error}")
        return None
    return log_path


configure_logging()


def get_version() -> str:
    """Return the server version.

    Installed distribution metadata is preferred, then ``pyproject.toml`` for a
    native checkout, and finally the package constant. This keeps the reported
    version correct inside the Docker image where the project itself is not
    installed.

    Returns:
        The version string.

    """
    try:
        return metadata.version("openstates-mcp-server")
    except metadata.PackageNotFoundError:
        pass
    except Exception as error:  # pragma: no cover - defensive
        logger.debug(f"Could not read installed metadata: {error}")

    for candidate in (
        Path(__file__).resolve().parent.parent / "pyproject.toml",
        Path("/app/pyproject.toml"),
    ):
        try:
            with candidate.open("rb") as handle:
                version = tomllib.load(handle).get("project", {}).get("version")
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if version:
            return version
    return __version__


def is_docker() -> bool:
    """Check if running inside a Docker container.

    Returns:
        True if running inside Docker, False otherwise.

    """
    if Path("/.dockerenv").exists():
        return True
    cgroup = Path("/proc/1/cgroup")
    try:
        return cgroup.is_file() and "docker" in cgroup.read_text(encoding="utf-8")
    except OSError:
        return False


# Create the root server instance. Mounted sub-servers are namespaced by prefix.
mcp: FastMCP[Any] = FastMCP(
    name=SERVICE_NAME,
    version=get_version(),
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
        "service": SERVICE_NAME,
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
            "tools_available": list(SUB_SERVER_PREFIXES),
            "transport": config.mcp_transport,
            "endpoint": config.streamable_http_path,
            "stateless_http": config.mcp_stateless_http,
            "api_base": config.openstates_base_url,
            "host": config.mcp_host,
            "port": config.mcp_port,
            "api_configured": bool(config.openstates_api_key),
        },
    }


def setup() -> FastMCP[Any]:
    """Mount every tool sub-server on the root server.

    Mounting is synchronous, so tool registration happens at import time without
    spinning up an event loop. This keeps ``import app.server`` usable from
    ASGI servers, test runners and CLI entrypoints alike.

    Returns:
        The configured root server.

    """
    logger.info("Setting up OpenStates MCP server")
    sub_servers = {
        "bills": bills_server,
        "people": people_server,
        "committees": committees_server,
        "events": events_server,
        "jurisdictions": jurisdictions_server,
    }
    for prefix, sub_server in sub_servers.items():
        mcp.mount(sub_server, prefix=prefix)
        logger.info(f"Mounted '{prefix}' server tools")
    logger.info("Server setup complete")
    return mcp


setup()


def healthz(_request: Request) -> Response:
    """Liveness and readiness probe for orchestrators.

    Registered as a plain Starlette route because a health probe is pure CPU
    work and FastMCP's ``custom_route`` only accepts async handlers.

    Args:
        _request: Incoming HTTP request (unused).

    Returns:
        JSON payload describing the service state.

    """
    return JSONResponse({
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": get_version(),
        "transport": config.mcp_transport,
        "stateless_http": config.mcp_stateless_http,
    })


def create_app(
    *,
    stateless_http: bool | None = None,
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    cors_origins: list[str] | None = None,
) -> Starlette:
    """Build the ASGI application for the Streamable HTTP service.

    Host and Origin protection are opt-in: with no values configured, the checks
    are disabled, which keeps local, container-internal and non-browser MCP
    clients working. CORS stays off unless browser origins are configured.

    Args:
        stateless_http: Override for stateless session handling.
        allowed_hosts: Override for the ``Host`` header allow list.
        allowed_origins: Override for the ``Origin`` header allow list.
        cors_origins: Override for the CORS allow list.

    Returns:
        Starlette application exposing the MCP endpoint and health route.

    """
    hosts = config.allowed_hosts if allowed_hosts is None else allowed_hosts
    origins = config.allowed_origins if allowed_origins is None else allowed_origins
    cors = config.cors_origins if cors_origins is None else cors_origins
    stateless = config.mcp_stateless_http if stateless_http is None else stateless_http

    endpoint_path = config.streamable_http_path
    slashless = endpoint_path.rstrip("/")
    aliases = (
        {slashless: endpoint_path} if slashless and slashless != endpoint_path else {}
    )

    app = mcp.http_app(path=endpoint_path, stateless_http=stateless)
    app.routes.append(Route(HEALTH_PATH, healthz, methods=["GET"]))

    # Innermost so the guards below always inspect the original request.
    if aliases:
        app.add_middleware(PathAliasMiddleware, aliases=aliases)
    if origins:
        app.add_middleware(OriginGuardMiddleware, allowed_origins=origins)
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    if cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        )

    logger.info(
        f"ASGI app ready: path={endpoint_path}{' (alias ' + slashless + ')' if aliases else ''}, "
        f"stateless={stateless}, allowed_hosts={hosts or 'any'}, "
        f"allowed_origins={origins or 'any'}, cors={'enabled' if cors else 'disabled'}"
    )
    return app


#: Module level ASGI app, for example ``uvicorn app.server:app``.
app = create_app()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line overrides for the server entrypoint.

    Args:
        argv: Argument list override, defaulting to ``sys.argv``.

    Returns:
        Parsed arguments namespace.

    """
    parser = argparse.ArgumentParser(
        prog="openstates-mcp",
        description="Run the OpenStates MCP server.",
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "http", "stdio"],
        default=None,
        help="Transport to serve (default: MCP_TRANSPORT or streamable-http).",
    )
    parser.add_argument("--host", default=None, help="HTTP bind address.")
    parser.add_argument("--port", type=int, default=None, help="HTTP bind port.")
    return parser.parse_args(argv)


async def main(
    *,
    transport: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Run the OpenStates MCP server.

    Args:
        transport: Transport override (``streamable-http``, ``http`` or ``stdio``).
        host: HTTP bind address override.
        port: HTTP bind port override.

    """
    selected_transport = transport or config.mcp_transport
    bind_host = host or config.mcp_host
    bind_port = port or config.mcp_port

    logger.info(f"Starting {SERVICE_NAME} with {selected_transport} transport")
    logger.info(
        f"Server configuration: host={bind_host}, port={bind_port}, "
        f"log_level={config.openstates_log_level}"
    )

    if not config.openstates_api_key:
        logger.warning(
            "OPENSTATES_API_KEY not configured - some features may be limited"
        )

    if selected_transport == "stdio":
        await mcp.run_async(transport="stdio")
        return

    server = uvicorn.Server(
        uvicorn.Config(
            app=app,
            host=bind_host,
            port=bind_port,
            log_level=config.openstates_log_level.lower(),
            # Give in-flight MCP requests time to finish on SIGTERM.
            timeout_graceful_shutdown=10,
        )
    )
    logger.info(
        f"Streamable HTTP endpoint available at "
        f"http://{bind_host}:{bind_port}{config.streamable_http_path}"
    )
    await server.serve()


if __name__ == "__main__":
    parsed = parse_args()
    asyncio.run(main(transport=parsed.transport, host=parsed.host, port=parsed.port))
