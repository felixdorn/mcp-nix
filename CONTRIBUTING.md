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
- [uv](https://github.com/astral-sh/uv)
- Rust toolchain

### Using Nix

```bash
nix develop
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

import requests
from pathlib import Path
from platformdirs import user_cache_dir

CACHE_DIR = Path(user_cache_dir("mcp-nix")) / "newservice"


class NewServiceError(Exception):
    """Base exception for NewService errors."""
    pass


class NewServiceSearch:
    """Search client for NewService."""

    _instance: "NewServiceSearch | None" = None

    def __init__(self):
        self._cache: dict = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "NewServiceSearch":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def search(self, query: str) -> list[dict]:
        """Search NewService."""
        # Check cache first
        if query in self._cache:
            return self._cache[query]

        # Fetch from API
        response = requests.get(
            f"https://api.newservice.example/search",
            params={"q": query},
        )
        response.raise_for_status()

        results = response.json()["results"]
        self._cache[query] = results
        return results
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

### Running Tests

```bash
# Run all tests
make test

# Or run specific test file
uv run pytest tests/test_e2e.py -v
```

### Writing Tests

```python
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def get_client():
    """Create an MCP client connected to the server."""
    return stdio_client(StdioServerParameters(
        command="uv",
        args=["run", "mcp-nix"],
    ))

@pytest.mark.anyio
async def test_my_new_tool():
    async with get_client() as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            # Call the tool
            result = await client.call_tool("my_new_tool", {
                "query": "test",
            })

            # Assert on the result
            assert len(result) > 0
            assert "expected text" in result[0].text
```

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
