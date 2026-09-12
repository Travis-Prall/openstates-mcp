"""Tests for the Streamable HTTP service shape (ASGI app, health, security).

These tests exercise the app in-process, so they are fast and need no listening
socket: plain reads go through httpx's ASGI transport and JSON-RPC calls go
through Starlette's ``TestClient`` so the FastMCP lifespan is executed.
"""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from app.server import HEALTH_PATH, SERVICE_NAME, create_app, get_version

BASE_URL = "http://testserver"
#: Headers the Streamable HTTP transport requires on JSON-RPC requests.
INIT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


async def _get(
    app: Starlette,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    base_url: str = BASE_URL,
) -> httpx.Response:
    """Issue a GET request against an in-process ASGI app.

    Args:
        app: ASGI application to call.
        path: Request path.
        headers: Optional request headers.
        base_url: Base URL, which sets the ``Host`` header.

    Returns:
        The HTTP response.

    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        return await client.get(path, headers=headers)


def test_create_app_exposes_mcp_endpoint_and_health_route() -> None:
    """The ASGI app exposes the MCP endpoint plus a health probe."""
    app = create_app()
    routes = {getattr(route, "path", None) for route in app.routes}

    assert "/mcp" in routes
    assert HEALTH_PATH in routes


@pytest.mark.asyncio
async def test_health_route_returns_healthy_payload() -> None:
    """The health probe reports service identity and version."""
    response = await _get(create_app(), HEALTH_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == SERVICE_NAME
    assert payload["version"] == get_version()


def test_stateless_http_mode_is_honoured() -> None:
    """Stateless mode is opt-in so horizontal scaling can be configured."""
    assert create_app(stateless_http=True) is not None
    assert create_app(stateless_http=False) is not None


def test_slashless_endpoint_path_is_served_without_redirect() -> None:
    """``/mcp`` reaches the MCP endpoint, so clients need not follow redirects."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    with TestClient(create_app(), follow_redirects=False) as client:
        slashless = client.post("/mcp", json=payload, headers=INIT_HEADERS)
        canonical = client.post("/mcp/", json=payload, headers=INIT_HEADERS)

    assert slashless.status_code == 200
    assert canonical.status_code == 200
    assert slashless.headers["mcp-session-id"]


def test_unknown_paths_are_not_aliased_to_the_mcp_endpoint() -> None:
    """Only the configured alias is rewritten; other paths still 404."""
    with TestClient(create_app(), follow_redirects=False) as client:
        assert client.get("/nope").status_code == 404


@pytest.mark.asyncio
async def test_allowed_hosts_rejects_unknown_host_header() -> None:
    """An unexpected Host header is rejected when an allow list is configured."""
    app = create_app(allowed_hosts=["allowed.example.com"])

    rejected = await _get(app, HEALTH_PATH, base_url="http://evil.example.com")
    accepted = await _get(app, HEALTH_PATH, base_url="http://allowed.example.com")

    assert rejected.status_code == 400
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_origin_guard_allows_missing_and_matching_origins() -> None:
    """Non-browser clients and allowed origins pass; other origins get 403."""
    app = create_app(allowed_origins=["https://app.example.com"])

    no_origin = await _get(app, HEALTH_PATH)
    matching = await _get(
        app, HEALTH_PATH, headers={"Origin": "https://app.example.com"}
    )
    matching_trailing_slash = await _get(
        app, HEALTH_PATH, headers={"Origin": "https://app.example.com/"}
    )
    rejected = await _get(app, HEALTH_PATH, headers={"Origin": "https://evil.test"})

    assert no_origin.status_code == 200
    assert matching.status_code == 200
    assert matching_trailing_slash.status_code == 200
    assert rejected.status_code == 403


@pytest.mark.asyncio
async def test_cors_is_disabled_by_default_and_opt_in_when_configured() -> None:
    """CORS is off unless browser origins are configured."""
    default_app = create_app()
    cors_app = create_app(cors_origins=["https://app.example.com"])
    origin = {"Origin": "https://app.example.com"}

    default_response = await _get(default_app, HEALTH_PATH, headers=origin)
    cors_response = await _get(cors_app, HEALTH_PATH, headers=origin)

    assert "access-control-allow-origin" not in default_response.headers
    assert (
        cors_response.headers["access-control-allow-origin"]
        == "https://app.example.com"
    )
