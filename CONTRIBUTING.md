# Contributing to mcp-nix

Thank you for your interest in contributing to mcp-nix! This guide will help you understand the architecture and get you started with development.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [How Tools Work](#how-tools-work)
- [Adding a New Tool](#adding-a-new-tool)
- [Adding a New Data Source](#adding-a-new-data-source)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)

## Architecture Overview

mcp-nix is an MCP (Model Context Protocol) server that provides AI assistants with access to Nix ecosystem documentation and package information. It follows a modular, plugin-based architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server (FastMCP)                     │
│                      mcp_nix/__init__.py                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Tool Layer (tools.py)                   │
│              Async tools with @mcp.tool() decorators        │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     search.py    │ │  homemanager.py │ │       ...       │
│  (Elastisearch)  │ │  (lunr + JSON)  │ │(nixhub, ixx,...)│
└──────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│ search.nixos.org│ │extranix.com API │
└─────────────────┘ └─────────────────┘
```

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - **we use uv exclusively for Python package management**
- Rust toolchain

### Using Nix

```bash
nix develop
```

### Running Commands

All Python commands should be run through `uv`:

```bash
uv run pytest tests/           # Run tests
uv run mcp-nix                  # Run the server
uv run ruff check .             # Lint
```

## How Tools Work

### Tool Categories

Tools are organized into categories with inclusion states at the category and tool level. Tool resolution logic is in `__init__.py`

### Tool Implementation Pattern

Every tool follows this pattern:

```python
@mcp.tool()
async def my_tool(
    query: str,
    channel: str = "unstable",
) -> str:
    """
    Short description of what the tool does.

    Args:
        query: What the query parameter represents
        channel: Optional channel selection (default: unstable)

    Examples:
        my_tool("firefox")
        my_tool("python", channel="24.05")
    """
    try:
        # 1. Get the appropriate search client (singleton)
        search = NixOSSearch.get_instance()

        # 2. Call the backend method
        results = await search.my_method(query, channel)

        # 3. Format and return results
        if not results:
            return "No results found."
        return "\n\n".join(str(r) for r in results)

    except SomeError as e:
        return _format_error(e)
```

## Adding a New Tool

### Step 1: Identify the Data Source

Determine which module should handle the data:
- Existing module (e.g., `search.py` for NixOS Search-related tools)
- New module (if it's a completely new data source)

### Step 2: Add Backend Method

Add the data fetching logic to the appropriate module. Example in `search.py`:

```python
async def get_package_maintainers(self, package_name: str, channel: str) -> list[str]:
    """Fetch maintainers for a package."""
    await self._ensure_config()

    # Use the Elasticsearch client
    response = requests.get(
        f"{self.config['url']}/latest-*-{channel}/_doc/package_{package_name}",
        auth=self.auth,
    )

    if response.status_code == 404:
        raise PackageNotFoundError(package_name)

    data = response.json()
    return data["_source"].get("maintainers", [])
```

### Step 3: Add the Tool Function

Add the tool to `tools.py`:

```python
@mcp.tool()
async def get_package_maintainers(
    package_name: str,
    channel: str = "unstable",
) -> str:
    """
    Get maintainers for a Nixpkgs package.

    Args:
        package_name: Exact package attribute name
        channel: NixOS channel (default: unstable)

    Examples:
        get_package_maintainers("firefox")
        get_package_maintainers("python3", channel="24.05")
    """
    try:
        search = NixOSSearch.get_instance()
        maintainers = await search.get_package_maintainers(package_name, channel)

        if not maintainers:
            return f"No maintainers listed for {package_name}"

        return f"Maintainers for {package_name}:\n" + "\n".join(f"- {m}" for m in maintainers)

    except PackageNotFoundError:
        return f"Package '{package_name}' not found in channel '{channel}'"
```

### Step 4: Register the Tool

Add the tool to `TOOL_CATEGORIES` in `__init__.py`:

```python
TOOL_CATEGORIES: dict[str, tuple[bool, list[str]]] = {
    "nixpkgs": (True, [
        "search_nixpkgs",
        "show_nixpkgs_package",
        "read_derivation",
        "get_package_maintainers",  # Add here
    ]),
    # ...
}
```

If the tool should be excluded by default (like source-reading tools), add it to `DEFAULT_EXCLUDED_TOOLS`:

```python
DEFAULT_EXCLUDED_TOOLS = {
    "read_derivation",
    "read_nixos_module",
    # ...
    "get_package_maintainers",  # If it should be opt-in
}
```

### Step 5: Add Tests

Add tests to `tests/test_e2e.py`:

```python
async def test_get_package_maintainers():
    async with get_client() as client:
        result = await client.call_tool("get_package_maintainers", {"package_name": "firefox"})
        assert "Maintainers" in result[0].text
```

### Step 6: Update Documentation

Add the tool to the table in `README.md`:

```markdown
| `get_package_maintainers` | Get maintainers for a Nixpkgs package |
```

## Adding a New Data Source

For entirely new data sources (e.g., a new Nix-related service):

### Step 1: Create the Module

Create a new file `mcp_nix/newservice.py`:

```python
"""Client for NewService API."""

from .cache import get_cache, APIError

_cache = get_cache("newservice")


class NewServiceError(APIError):
    """Base exception for NewService errors."""
    pass


def get_data(query: str) -> list[dict]:
    """Get data from NewService, using cache if available."""
    url = f"https://api.newservice.example/search?q={query}"
    try:
        return _cache.request(url, lambda r: r.json()["results"])
    except APIError as exc:
        raise NewServiceError(f"Failed to fetch: {exc}") from exc


class NewServiceSearch:
    """Search client for NewService."""

    @staticmethod
    def search(query: str) -> list[dict]:
        """Search NewService."""
        return get_data(query)
```

### Caching

We use [diskcache](https://grantjenks.com/docs/diskcache/) for persistent caching. The `cache.py` module provides a `Cache` class with helper methods:

```python
from .cache import get_cache, DEFAULT_EXPIRE

_cache = get_cache("mymodule")  # Namespaced cache instance
```

#### HTTP Requests with Caching

Use `_cache.request()` for HTTP requests. The `callback` is required - it transforms the response and serves as validation. If it fails on a cached value, the cache is automatically invalidated and a fresh request is made:

```python
# Fetch JSON - callback validates by accessing .json()
data = _cache.request(url, lambda r: r.json())

# Fetch and parse YAML
config = _cache.request(url, lambda r: r.yaml())

# Fetch HTML and parse with BeautifulSoup
soup = _cache.request(url, lambda r: r.soup())

# Get raw text
text = _cache.request(url, lambda r: r.text)

# Custom TTL
data = _cache.request(url, lambda r: r.json(), expire=None)      # Forever
data = _cache.request(url, lambda r: r.json(), expire=3600)      # 1 hour
```

#### Non-HTTP Caching

Use `_cache.get_or_set()` for caching arbitrary values. The `callback` is required:

```python
# Cache result of expensive computation
value = _cache.get_or_set("key", factory_fn, lambda v: v["data"])

# Return value as-is (callback still required)
value = _cache.get_or_set("key", factory_fn, lambda v: v)

# Custom TTL
value = _cache.get_or_set("key", factory_fn, lambda v: v, expire=None)  # Forever
```

#### Automatic Cache Recovery

The callback pattern provides automatic recovery from corrupted or outdated cache entries. If the callback fails (e.g., accessing an attribute that doesn't exist), the cached value is deleted and a fresh value is fetched:

```python
# If cache contains old format without "data" key, callback fails,
# cache is invalidated, factory is called, and callback succeeds on fresh value
result = _cache.get_or_set(
    "key",
    factory=fetch_new_format,
    callback=lambda v: v["data"]  # Validates structure by using it
)
```

#### Non-Serializable Objects

For data that can't be serialized (e.g., search indices), use in-memory caching alongside disk caching for the raw data:

```python
_cache = get_cache("mymodule")
_index_cache: dict[str, SearchIndex] = {}  # In-memory for non-serializable objects

def get_index(name: str) -> SearchIndex:
    if name in _index_cache:
        return _index_cache[name]

    # Cache raw bytes, build index in-memory
    raw_data = _cache.request(url, lambda r: r.content)
    index = SearchIndex.from_bytes(raw_data)
    _index_cache[name] = index
    return index
```

### Step 2: Add Models

Add Pydantic models to `models.py`:

```python
class NewServiceResult(BaseModel):
    """A result from NewService."""

    name: str
    description: str | None = None
    url: str

    def format_short(self) -> str:
        """Short format for search results."""
        desc = f" - {self.description}" if self.description else ""
        return f"• {self.name}{desc}"

    def __str__(self) -> str:
        """Full format for detailed view."""
        lines = [f"# {self.name}"]
        if self.description:
            lines.append(f"\n{self.description}")
        lines.append(f"\nURL: {self.url}")
        return "\n".join(lines)
```

### Step 3: Add Tools

Add tools to `tools.py` following the pattern above.

### Step 4: Register Category

Add a new category to `TOOL_CATEGORIES` in `__init__.py`:

```python
TOOL_CATEGORIES: dict[str, tuple[bool, list[str]]] = {
    # ...existing categories...
    "newservice": (False, [  # False = disabled by default
        "search_newservice",
        "show_newservice_item",
    ]),
}
```

### Step 5: Add CLI Flag

The CLI flag is automatically generated from the category name. Users can enable it with `--newservice` or disable it with `--no-newservice`.

## Testing

We use [syrupy](https://github.com/tophat/syrupy) for snapshot testing. Snapshots capture the full output of each tool call.

### Running Tests

```bash
# Run all tests
make test

# Update snapshots after intentional changes
make test-update
```

### Writing Tests

```python
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp
from mcp_nix import tools as _  # noqa: F401 - registers tools

pytestmark = pytest.mark.anyio

async def test_my_new_tool(snapshot):
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("my_new_tool", {"query": "test"})
        assert result.content[0].text == snapshot
```

Use stable versions (e.g., `25.11`) instead of `unstable` to reduce snapshot churn.

## Code Style

### Linting and Formatting

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting  and [ty](https://github.com/astral-sh/ty) for type checking:

```bash
# Check for issues
make check

# Auto-fix issues and format
make lint

# Format only
make fmt
```

### Rust Code (pyixx)

```bash
# Run clippy and fmt
make pyixx-check

```

## PR Guidelines

1. **One feature per PR**: Keep PRs focused and reviewable
2. **Include tests**: New features need corresponding tests
3. **Describe your changes**: Explain what and why in the PR description
4. **Link issues**: Reference any related issues

## Questions?

- Open an issue on [GitHub](https://github.com/felixdorn/mcp-nix/issues)
- Check existing issues for similar questions

Thank you for contributing!
