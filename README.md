# OpenStates MCP Server

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

The OpenStates MCP Server provides these production-ready tools (see [app/README.md](app/README.md) for full details and parameters):

- **Bill & Legislation Search:**
  - `search_bills` — Search bills and legislation by query, jurisdiction, session, subject, or sponsor
  - `get_bill_details` — Get detailed information about a specific bill
- **People & Legislators:**
  - `search_people` — Search for legislators, governors, and other political figures
  - `get_legislators_by_location` — Find legislators representing a specific geographic location
- **Jurisdictions & States:**
  - `get_jurisdictions` — Get list of available jurisdictions (states, territories)
  - `get_jurisdiction_details` — Get detailed metadata for a specific jurisdiction
- **Committees:**
  - `search_committees` — Search for legislative committees by jurisdiction and chamber
  - `get_committee_details` — Get detailed information about a specific committee
- **Events & Hearings:**
  - `search_events` — Search for legislative events, hearings, and meetings
  - `get_event_details` — Get detailed information about a specific legislative event
- **System & Health:**
  - `status`, `get_api_status`, `health_check`

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
 uv shell
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
OPENSTATES_BASE_URL=https://v3.openstates.org
OPENSTATES_API_KEY=your-api-key-here
OPENSTATES_TIMEOUT=30
OPENSTATES_LOG_LEVEL=INFO
OPENSTATES_RATE_LIMIT=50
OPENSTATES_CACHE_TTL=300
OPENSTATES_DEBUG=false
MCP_PORT=8785
```

### Running the Server

The server now runs with streamable-http transport by default:

```bash
uv run python -m app.server
```

This will start the server at:

- **Host**: `0.0.0.0` (accessible from external connections)
- **Port**: `8785`
- **Endpoint**: `http://localhost:8785/mcp/`

Or use the VS Code task: **Run MCP Server**

#### Connecting to the Server

When using the streamable-http transport, clients can connect to the server using:

```python
from fastmcp import Client

async with Client("http://localhost:8785/mcp/") as client:
    result = await client.call_tool("status")
    print(result)
```

## 💡 Usage Examples

See [app/README.md](app/README.md) for detailed tool usage and examples, including search, citation, and regulatory queries.

## 🐳 Docker Setup

```bash
# Production
 docker-compose up -d
# Development with hot reload
 docker-compose --profile dev up --build
```

## 🧪 Testing

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

See [tests/README.md](tests/README.md) for test suite details, coverage, and troubleshooting.

## 🔧 Development

```bash
uv run ruff format .
uv run ruff check .
uv run mypy app/
uv run pip-audit
```

## 🚨 Troubleshooting

See [app/README.md](app/README.md) and [tests/README.md](tests/README.md) for troubleshooting and advanced usage.

## 📚 Documentation

- [Source Code Documentation](app/README.md)
- [Test Documentation](tests/README.md)
- [Project Context](context.json)
- [OpenStates API Documentation](https://docs.openstates.org/api-v3/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://spec.modelcontextprotocol.io/)

---

**Ready to use!** The OpenStates MCP Server provides production-ready access to state legislative data through comprehensive MCP tools.
