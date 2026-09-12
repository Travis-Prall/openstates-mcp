# OpenStates MCP Server

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=flat-square&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/travisprall)

A Model Context Protocol (MCP) server that provides LLM-friendly access to state legislative data through the OpenStates API v3. This server enables searching and retrieving bills, legislators, committees, events, and legislative sessions for comprehensive state-level political and legislative research.

## 🎯 Purpose

The OpenStates MCP Server provides comprehensive access to **state legislative data** through the extensive OpenStates API. OpenStates tracks legislation, legislators, committees, and legislative events across all 50 US states plus DC and Puerto Rico.

## 📋 Key Advantages

- **Comprehensive Legislative Database:**
  - Access to bills and legislation from all 50 states
  - Real-time updates from state legislatures
  - Historical legislative data and tracking
- **Detailed Legislator Information:**
  - Complete legislator profiles and contact information
  - Committee memberships and leadership roles
  - Legislative districts and boundaries
- **Legislative Process Tracking:**
  - Bill status and legislative progress
  - Committee hearings and legislative events
  - Voting records and legislative history
- **Multi-State Research:**
  - Compare legislation across states
  - Track policy trends and patterns
  - Research specific legislative topics nationwide

## 🛠️ Available MCP Tools

The OpenStates MCP Server provides these production-ready tools (see [app/README.md](app/README.md) for full details and parameters). Tool names are namespaced by domain:

- **Bill & Legislation Search:**
  - `bills_search_bills` — Search bills and legislation by query, jurisdiction, session, subject, or sponsor
  - `bills_get_bill_details` — Get detailed information about a specific bill
  - `bills_get_bill_by_id` — Look up a bill by its OpenStates ID
- **People & Legislators:**
  - `people_search_people` — Search for legislators, governors, and other political figures
  - `people_get_legislators_by_location` — Find legislators representing a specific geographic location
- **Jurisdictions & States:**
  - `jurisdictions_get_jurisdictions` — Get list of available jurisdictions (states, territories)
  - `jurisdictions_get_jurisdiction_details` — Get detailed metadata for a specific jurisdiction
- **Committees:**
  - `committees_search_committees` — Search for legislative committees by jurisdiction and chamber
  - `committees_get_committee_details` — Get detailed information about a specific committee
- **Events & Hearings:**
  - `events_search_events` — Search for legislative events, hearings, and meetings
  - `events_get_event_details` — Get detailed information about a specific legislative event
- **System & Health:**
  - `status` — Server, platform and API-key health check

See [app/README.md](app/README.md) for a full reference of all tools, parameters, and usage examples.

## 📦 Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Internet connection for OpenStates API access

### Install with uv

```bash
# Clone the repository
git clone <repository-url>
cd OpenStates

# Install dependencies
uv sync

# Activate the environment (optional)
source .venv/bin/activate
```

### Environment Configuration

Create a `.env` file in the project root (only the API key is required):

```bash
OPENSTATES_API_KEY=your-api-key-here

# Optional overrides
OPENSTATES_LOG_LEVEL=INFO
OPENSTATES_TIMEOUT=30
OPENSTATES_RATE_LIMIT=50
OPENSTATES_CACHE_TTL=300
OPENSTATES_DEBUG=false
MCP_HOST=0.0.0.0
MCP_PORT=8797
MCP_PATH=/mcp/
```

### Running the Server

The server runs with the streamable-http transport by default:

```bash
uv run python -m app
```

This starts the server at:

- **Host**: `0.0.0.0` (accessible from external connections)
- **Port**: `8797`
- **Endpoint**: `http://localhost:8797/mcp/` (the slash-less `/mcp` also works)
- **Health probe**: `http://localhost:8797/healthz`

For a single local client, the stdio transport is also available:

```bash
uv run python -m app --transport stdio
```

Bind address and port can be overridden with `--host` / `--port`:

```bash
uv run python -m app --host 127.0.0.1 --port 9000
```

Or use the VS Code task: **Run MCP Server**

#### Connecting to the Server

When using the streamable-http transport, clients can connect to the server using:

```python
from fastmcp import Client

async with Client("http://localhost:8797/mcp/") as client:
    result = await client.call_tool("status")
    print(result)
```

### Security

- `GET /healthz` is the only unauthenticated route; tool calls are authenticated
  with `OPENSTATES_API_KEY` on the server side.
- `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` enable `Host`/`Origin` allow
  lists (DNS-rebinding and browser-origin protection). Leave them empty for
  local and non-browser clients; set them for internet-facing deployments.
- CORS headers are only emitted when `MCP_CORS_ORIGINS` is set.

## 💡 Usage Examples

See [app/README.md](app/README.md) for detailed tool usage and examples.

## 🐳 Docker Setup

The image is a multi-stage build on a digest-pinned `python:3.12-slim-bookworm`,
runs as a non-root user (`uid 1001`) and ships a `/healthz` based `HEALTHCHECK`
plus `STOPSIGNAL SIGTERM` for graceful shutdown.

```bash
# Build and start the production service (port 8797)
docker compose up -d --build

# Follow logs / check health
docker compose logs -f
docker compose exec open-states-mcp-server \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8797/healthz').read().decode())"

# Stop
docker compose down
```

`docker-compose.yml` applies container hardening: read-only root filesystem, a
`/tmp` tmpfs for logs (`LOG_DIR=/tmp/logs`), `cap_drop: ALL`,
`no-new-privileges`, an init process, CPU/memory limits and a healthcheck. The
`OPENSTATES_API_KEY` is read from the project `.env` when present.

Run any other transport by overriding the command, for example stdio:

```bash
docker compose run --rm open-states-mcp-server python -m app --transport stdio
```

Helper scripts: `scripts/prod.sh {build|start|stop|restart|logs|status|shell}` and
`scripts/dev.sh {rebuild|start|test|lint|format|logs|shell}`.

## 🧪 Testing

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

See [tests/README.md](tests/README.md) for test suite details, coverage, and troubleshooting.

## 🔧 Development

```bash
uv run ruff check app tests
uv run ruff format app tests
uv run mypy app
uvx pip-audit
```

## 🚨 Troubleshooting

See [app/README.md](app/README.md) and [tests/README.md](tests/README.md) for troubleshooting and advanced usage.

## 📚 Documentation

- [Source Code Documentation](app/README.md)
- [Test Documentation](tests/README.md)
- [OpenStates API Documentation](https://docs.openstates.org/api-v3/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://spec.modelcontextprotocol.io/)

## ☕ Support

If this project saves you time, consider [buying me a coffee](https://www.buymeacoffee.com/travisprall) or [sponsoring me on GitHub](https://github.com/sponsors/travisprall). Donations fund maintenance, bug fixes, and new features, and are always optional.

Questions, ideas, or bug reports? [Open an issue](https://github.com/Travis-Prall/openstates-mcp/issues).

## 📄 License

Copyright © 2025 travisprall. Licensed under the [PolyForm Noncommercial 1.0.0 license](LICENSE.md).

---

**Ready to use!** The OpenStates MCP Server provides production-ready access to state legislative data through comprehensive MCP tools.
