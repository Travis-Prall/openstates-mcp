# OpenStates MCP Server — Source Documentation

A FastMCP server that exposes the OpenStates API v3 (state legislative data) to
LLMs. This document covers the module layout, the runtime surface (transports,
configuration, health) and the tool reference. Project level instructions live in
[../README.md](../README.md).

## Code Architecture Overview

- **`app/server.py`**: Entrypoint. Builds the sub-servers, mounts them on the root
  FastMCP instance, creates the ASGI app (guards, CORS, `/healthz`) and runs
  uvicorn or the stdio transport.
- **`app/config.py`**: `pydantic-settings` configuration. Every field is settable
  through an environment variable or the project `.env` file.
- **`app/middleware.py`**: ASGI middleware — `OriginGuardMiddleware` (opt-in
  `Origin` allow list) and `PathAliasMiddleware` (serves `/mcp` without a
  redirect to the canonical `/mcp/`).
- **`app/tools/`**: One module per data domain, each exposing its own
  `FastMCP` server:
  - `bills.py`: bills and legislation
  - `people.py`: legislators and other people
  - `committees.py`: committees
  - `events.py`: hearings and legislative events
  - `jurisdictions.py`: states, territories and other jurisdictions
  - `common.py`: shared HTTP client, retry/backoff, validation and logging
    helpers used by every tool module
  - `logging.py`: loguru configuration
- **`app/logs/`**: Rotating log files (`LOG_DIR` overrides the location).
- **`tests/`**: Test suite, see [../tests/README.md](../tests/README.md).

Sub-servers are mounted with `mcp.mount(...)`, so **every tool name is prefixed**
with its module name (`bills_search_bills`, `people_search_people`, ...). The
root server additionally exposes `status`.

## Transport and Endpoints

The server defaults to **streamable-http**, served by uvicorn as an ASGI app:

| Endpoint | Purpose |
|--------------------------------|------------------------------------------------------------|
| `http://localhost:8797/mcp/`   | MCP Streamable HTTP endpoint (canonical path) |
| `http://localhost:8797/mcp`    | Same endpoint, alias served without a redirect |
| `http://localhost:8797/healthz` | Unauthenticated liveness/readiness probe |

To connect programmatically:

```python
from fastmcp import Client

async with Client("http://localhost:8797/mcp/") as client:
    result = await client.call_tool("jurisdictions_get_jurisdictions")
    print(result)
```

A **stdio** transport is available for single-client, local integrations (it
opens no HTTP listener):

```bash
uv run python -m app --transport stdio
```



## Configuration

All settings come from environment variables or `.env` (field name in upper
case; case insensitive). The most relevant ones:

| Variable | Default | Description |
|------------------------------|-------------------|-------------------------------------------------------|
| `MCP_HOST` | `0.0.0.0` | HTTP bind address |
| `MCP_PORT` | `8797` | HTTP bind port |
| `MCP_PATH` | `/mcp/` | MCP endpoint path (slash-less form is aliased) |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http`, `http` or `stdio` |
| `MCP_STATELESS_HTTP` | `false` | Fresh session per request, for horizontal scaling |
| `MCP_ALLOWED_HOSTS` | *(empty)* | Comma separated `Host` allow list (empty disables the check) |
| `MCP_ALLOWED_ORIGINS` | *(empty)* | Comma separated `Origin` allow list (empty disables the check) |
| `MCP_CORS_ORIGINS` | *(empty)* | Comma separated CORS origins (empty disables CORS) |
| `LOG_DIR` | `app/logs` | Log directory; point at a writable path for read-only root filesystems |
| `ENVIRONMENT` | `production` | `development` enables development behaviour |
| `OPENSTATES_API_KEY` | *(none)* | Required by every API call |
| `OPENSTATES_BASE_URL` | `https://v3.openstates.org` | API base URL |
| `OPENSTATES_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OPENSTATES_TIMEOUT` | `30` | Total request timeout in seconds |
| `OPENSTATES_CONNECT_TIMEOUT` | `10` | Connection timeout in seconds |
| `OPENSTATES_READ_TIMEOUT` | `30` | Read timeout in seconds |
| `OPENSTATES_MAX_RETRIES` | `3` | Attempts for rate limited/transient failures |
| `OPENSTATES_RETRY_DELAY` | `1.0` | Base delay for exponential backoff |
| `OPENSTATES_RATE_LIMIT` | `50` | Requests per hour as documented by OpenStates |
| `OPENSTATES_CACHE_TTL` | `300` | Cache TTL in seconds |

Command line flags override `MCP_TRANSPORT`, `MCP_HOST` and `MCP_PORT`:

```bash
uv run python -m app --host 127.0.0.1 --port 9000 --transport streamable-http
```

## Health and Observability

- `GET /healthz` returns `{"status": "healthy", "service": ..., "version": ...,`
  `"transport": ..., "stateless_http": ...}` and backs the container
  `HEALTHCHECK`.
- The `status` tool reports process, platform and API-key state to MCP clients.
- Logs go to `LOG_DIR/server.log` (rotating) and to stderr.

## MCP Tools

All parameters are optional unless marked *(required)*.

| Tool Name | Parameters | Description |
|----------------------------------------|----------------------------------------------------------------------|--------------------------------------------|
| `bills_search_bills` | q, jurisdiction, session, chamber, classification, updated_since, subject, sponsor, limit, page | Search bills and legislation |
| `bills_get_bill_details` | jurisdiction *(required)*, session *(required)*, bill_id *(required)*, include | Detailed bill information |
| `bills_get_bill_by_id` | bill_id *(required)*, include | Bill lookup by OpenStates ID |
| `people_search_people` | q, jurisdiction, name, org_classification, district, id, include, limit, page | Search legislators and political figures |
| `people_get_legislators_by_location` | latitude *(required)*, longitude *(required)* | Legislators representing a location |
| `committees_search_committees` | jurisdiction, classification, parent, chamber, include, limit, page | Search legislative committees |
| `committees_get_committee_details` | committee_id *(required)*, include | Detailed committee information |
| `events_search_events` | jurisdiction, deleted, before, after, require_bills, include, limit, page | Search legislative events and hearings |
| `events_get_event_details` | event_id *(required)*, include | Detailed event information |
| `jurisdictions_get_jurisdictions` | classification, include, limit, page | List available jurisdictions |
| `jurisdictions_get_jurisdiction_details` | jurisdiction_id *(required)*, include | Detailed jurisdiction information |
| `status` | (none) | Server and environment health check |

## Usage Examples

```python
# Search legislation in California
await client.call_tool(
    "bills_search_bills",
    {"q": "education funding", "jurisdiction": "ca", "session": "2023"},
)

# Detailed bill lookup
await client.call_tool(
    "bills_get_bill_details",
    {"jurisdiction": "ny", "session": "2023", "bill_id": "A1234"},
)

# Legislators for a location
await client.call_tool(
    "people_get_legislators_by_location",
    {"latitude": 40.7128, "longitude": -74.0060},
)
```

## Common Use Cases

- Legislative research by state, topic, or sponsor
- Tracking bill progress and legislative history
- Finding legislators and their contact information
- Committee research and membership tracking
- Event and hearing schedules
- Multi-state policy comparison

## See Also

- [../README.md](../README.md) — Main project documentation
- [../tests/README.md](../tests/README.md) — Test suite documentation
- [OpenStates API v3 documentation](https://v3.openstates.org/docs/)
