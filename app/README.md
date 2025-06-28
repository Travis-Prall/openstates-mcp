# Open## Code Architecture Overview

- **`app/server.py`**: Main FastMCP server, imports all tool modules and sets up logging
- **`app/tools/`**: Contains all MCP tool implementations:
  - `bills.py`: Bill and legislation search tools
  - `people.py`: Legislator and people search tools
  - `committees.py`: Committee information tools
  - `events.py`: Legislative events and hearings tools
  - `jurisdictions.py`: State and jurisdiction tools
- **`app/config.py`**: Configuration and environment variable management
- **`app/logs/`**: Server logsServer v2.0

A comprehensive Model Context Protocol (MCP) server for accessing the OpenStates API v3, providing powerful state legislative research capabilities optimized for Large Language Model (LLM) interactions.

> **Latest Update (June 2025):** All MCP tools and modules are documented. Pydantic v2 compatibility, type annotations, and import structure are up-to-date. Server passes all lint checks and includes a comprehensive test suite.

## Code Architecture Overview

- **`app/server.py`**: Main FastMCP server, imports all tool modules and sets up logging
- **`app/tools/`**: Contains all MCP tool implementations:
  - `search.py`: Search tools (opinions, dockets, audio, people, RECAP, regulations)
  - `get.py`: Get tools (opinion, docket, audio, court, person, cluster)
  - `citation.py`: Citation lookup, parsing, batch, and enhanced tools
- **`app/models.py`**: Pydantic models for data validation
- **`app/config.py`**: Configuration and environment variable management
- **`app/utils.py``: Utility functions (XML/JSON conversion, etc.)
- **`app/logs/`**: Server logs

## Server Transport

The server is configured to use **streamable-http** transport by default, making it accessible via HTTP at `http://localhost:8000/mcp/`. This allows:

- **HTTP-based access**: Standard HTTP requests for web-based deployments
- **External connections**: Server binds to `0.0.0.0` for network accessibility
- **RESTful interface**: Modern HTTP transport for better integration
- **Production ready**: Suitable for containerized and cloud deployments

To connect to the server programmatically:

```python
from fastmcp import Client

async with Client("http://localhost:8000/mcp/") as client:
    result = await client.call_tool("status")
```

## Modules and Purposes

- **server.py**: FastMCP entrypoint, imports all tool servers
- **tools/bills.py**: Implements search and retrieval tools for bills and legislation
- **tools/people.py**: Implements search tools for legislators and political figures
- **tools/committees.py**: Implements committee search and information tools
- **tools/events.py**: Implements legislative events and hearings tools
- **tools/jurisdictions.py**: Implements jurisdiction and state information tools
- **config.py**: Loads environment and configures logging

## MCP Tools and Parameters

| Tool Name                    | Parameters (all optional unless noted)                                                                 | Description                                      |
|------------------------------|------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| search_bills                 | q, jurisdiction, session, chamber, classification, updated_since, subject, sponsor, limit, page      | Search bills and legislation                     |
| get_bill_details             | jurisdiction (required), session (required), bill_id (required), include                            | Get detailed bill information                    |
| search_people                | q, jurisdiction, name, org_classification, district, id, include, limit, page                       | Search legislators and political figures         |
| get_legislators_by_location  | latitude (required), longitude (required)                                                           | Find legislators by geographic location          |
| search_committees            | jurisdiction, classification, parent, chamber, include, limit, page                                  | Search legislative committees                    |
| get_committee_details        | committee_id (required), include                                                                      | Get detailed committee information               |
| search_events                | jurisdiction, deleted, before, after, require_bills, include, limit, page                           | Search legislative events and hearings           |
| get_event_details            | event_id (required), include                                                                         | Get detailed event information                   |
| get_jurisdictions            | classification, include, limit, page                                                                  | Get list of available jurisdictions             |
| get_jurisdiction_details     | jurisdiction_id (required), include                                                                   | Get detailed jurisdiction information            |
| status                       | (none)                                                                                                | System health check                              |

## Usage Examples

### Search Bills and Legislation

```python
search_bills(q="education funding", jurisdiction="ca", session="2023")
```

### Get Specific Bill Details

```python
get_bill_details(jurisdiction="ny", session="2023", bill_id="A1234")
```

### Search Legislators

```python
search_people(name="Smith", jurisdiction="tx")
```

### Find Legislators by Location

```python
get_legislators_by_location(latitude=40.7128, longitude=-74.0060)
```

### Search Legislative Committees

```python
search_committees(jurisdiction="fl", chamber="upper")
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
- [tests/README.md](../tests/README.md) — Test suite documentation
- [context.json](../context.json) — Project context metadata
