#!/usr/bin/env python3
"""Entry point for running the OpenStates MCP Server.

This allows the server to be run with:

    python -m app
    uv run python -m app
    uv run python -m app --transport stdio
    uv run python -m app --host 127.0.0.1 --port 9000
"""

import asyncio

from app.server import main, parse_args

if __name__ == "__main__":
    _args = parse_args()
    asyncio.run(main(transport=_args.transport, host=_args.host, port=_args.port))
