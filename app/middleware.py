"""ASGI middleware for the OpenStates MCP server.

FastMCP 2.9 ships no built-in Host/Origin guard, so DNS-rebinding style browser
attacks are rejected here with a small, dependency-free ASGI middleware. A second
middleware removes the redirect FastMCP's trailing-slash mount would otherwise
emit for the slash-less endpoint URL.
"""

from collections.abc import Iterable, Mapping

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class PathAliasMiddleware:
    """Serve canonical request paths under additional aliases.

    FastMCP mounts the Streamable HTTP endpoint with a trailing slash, so a
    request to the slash-less URL (``/mcp``) would be answered with a permanent
    redirect. Rewriting the path in-process keeps MCP clients that do not follow
    redirects working, and saves a round trip for those that do.
    """

    def __init__(self, app: ASGIApp, aliases: Mapping[str, str]) -> None:
        """Store the wrapped app and the alias map.

        Args:
            app: The downstream ASGI application.
            aliases: Mapping of requested path to canonical path.

        """
        self.app = app
        self.aliases = {
            source: target for source, target in aliases.items() if source != target
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Rewrite aliased paths and delegate to the wrapped application.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive channel.
            send: ASGI send channel.

        """
        if scope["type"] in {"http", "websocket"}:
            target = self.aliases.get(scope["path"])
            if target is not None:
                scope = dict(scope)
                scope["path"] = target
                scope["raw_path"] = target.encode("utf-8")
        await self.app(scope, receive, send)


class OriginGuardMiddleware:
    """Reject HTTP requests whose ``Origin`` header is not explicitly allowed.

    Non-browser MCP clients do not send an ``Origin`` header, so they are always
    allowed. When the allow list is empty the middleware is a pass-through.
    """

    def __init__(self, app: ASGIApp, allowed_origins: Iterable[str]) -> None:
        """Store the wrapped app and the allow list.

        Args:
            app: The downstream ASGI application.
            allowed_origins: Origins permitted to call the service.

        """
        self.app = app
        self.allowed_origins = {origin.rstrip("/") for origin in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Validate the ``Origin`` header and delegate to the app.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive channel.
            send: ASGI send channel.

        """
        if scope["type"] == "http" and self.allowed_origins:
            origin = Headers(scope=scope).get("origin")
            if origin and origin.rstrip("/") not in self.allowed_origins:
                response = PlainTextResponse("Origin not allowed", status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
