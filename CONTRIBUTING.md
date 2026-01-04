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
│                     Tool Layer (tools.py)                    │
│            17 async tools with @mcp.tool() decorators        │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   search.py     │ │ homemanager.py  │ │   nuschtos.py   │
│  (Elasticsearch)│ │ (lunr + JSON)   │ │ (pyixx binary)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ search.nixos.org│ │extranix.com API │ │ NüschtOS .ixx   │
└─────────────────┘ └─────────────────┘ └─────────────────┘

Additional modules:
├── nixhub.py    → nixhub.io API (package versions)
├── sources.py   → GitHub/GitLab raw file fetching
├── models.py    → Pydantic data models
└── utils.py     → HTML parsing utilities
```

### Key Design Principles

1. **Modularity**: Each data source has its own module handling fetching, caching, and searching
2. **Caching**: Multi-level caching (in-memory + disk) with appropriate TTLs
3. **Async**: All tools are async for non-blocking operation
4. **Type Safety**: Pydantic models validate all external data
5. **Configurability**: Fine-grained control over which tools are enabled

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Rust toolchain (for building pyixx)

### Using Nix

```bash
# Enter the development shell
nix develop

# All dependencies are now available
```

## Project Structure

```
mcp-nix/
├── mcp_nix/                 # Main Python package
│   ├── __init__.py          # Entry point, CLI args, tool registration
│   ├── tools.py             # All 17 MCP tool implementations
│   ├── models.py            # Pydantic data models
│   ├── search.py            # NixOS/Nixpkgs Elasticsearch client
│   ├── homemanager.py       # Home Manager search (lunr-based)
│   ├── nuschtos.py          # NixVim/nix-darwin search (binary index)
│   ├── nixhub.py            # Package version lookup
│   ├── sources.py           # Source code fetching
│   └── utils.py             # Shared utilities
│
├── pyixx/                   # Rust PyO3 bindings for libixx
│   ├── src/lib.rs           # Rust implementation
│   ├── Cargo.toml           # Rust dependencies
│   └── pyproject.toml       # Python package config
│
├── tests/                   # Test suite
│   ├── test_e2e.py          # End-to-end MCP tests
│   └── test_resolution.py   # Tool resolution logic tests
│
├── pyproject.toml           # Project configuration
├── flake.nix                # Nix development environment
└── Makefile                 # Development commands
```

### Module Responsibilities

| Module | Purpose | External Dependency |
|--------|---------|---------------------|
| `search.py` | NixOS/Nixpkgs package and option search | search.nixos.org Elasticsearch |
| `homemanager.py` | Home Manager option search | home-manager-options.extranix.com |
| `nuschtos.py` | NixVim and nix-darwin option search | NüschtOS .ixx binary indices |
| `nixhub.py` | Package version history | nixhub.io API |
| `sources.py` | Fetch Nix source files | GitHub/GitLab raw content |
| `models.py` | Data validation and formatting | None |

## How Tools Work

### Tool Categories

Tools are organized into categories with default inclusion states:

| Category | Default | Tools |
|----------|---------|-------|
| `nixpkgs` | Enabled | `search_nixpkgs`, `show_nixpkgs_package`, `read_derivation`* |
| `nixos` | Enabled | `search_nixos_options`, `show_nixos_option`, `list_nixos_channels`, `read_nixos_module`* |
| `homemanager` | Disabled | `search_homemanager_options`, `show_homemanager_option`, `list_homemanager_releases`, `read_home_module`* |
| `nixvim` | Disabled | `search_nixvim_options`, `show_nixvim_option`, `read_nixvim_declaration`* |
| `nix-darwin` | Disabled | `search_nix_darwin_options`, `show_nix_darwin_option`, `read_nix_darwin_declaration`* |
| `nixhub` | Disabled | `list_package_versions`, `find_nixpkgs_commit_with_package_version` |

*Tools marked with * are in `DEFAULT_EXCLUDED_TOOLS` and require explicit `--include` even when their category is enabled.

### Tool Resolution Logic

The resolution system in `__init__.py` works as follows:

1. Start with category defaults (`TOOL_CATEGORIES`)
2. Apply CLI category flags (`--homemanager`, `--no-nixos`, etc.)
3. Apply `--include` list (adds specific tools)
4. Apply `--exclude` list (removes specific tools)
5. Filter out `DEFAULT_EXCLUDED_TOOLS` unless explicitly included

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

# Run specific test file
uv run pytest tests/test_e2e.py -v

# Run specific test
uv run pytest tests/test_e2e.py::test_search_package -v
```

### Test Structure

**End-to-end tests** (`test_e2e.py`):
- Test the full MCP client-server flow
- Verify tools return expected results
- Use real API calls (not mocked)

**Unit tests** (`test_resolution.py`):
- Test the tool resolution logic
- Verify category and tool inclusion/exclusion rules

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

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
make check

# Auto-fix issues and format
make lint

# Format only
make fmt
```

### Type Checking

We use [ty](https://github.com/astral-sh/ty) for type checking:

```bash
# Run type checker (included in make check)
uv run ty check mcp_nix
```

### Rust Code (pyixx)

```bash
# Check Rust code
make pyixx-check

# This runs:
# - cargo clippy (linting)
# - cargo fmt --check (formatting)
```

### Style Guidelines

1. **Docstrings**: All public functions need docstrings with Args and Examples sections
2. **Type hints**: Use type hints for all function parameters and return types
3. **Error handling**: Use custom exception classes, never bare `except:`
4. **Async**: All tool functions must be async
5. **Caching**: Implement caching for any network requests
6. **Models**: Use Pydantic models for external data validation

### Example Docstring

```python
async def search_packages(
    self,
    query: str,
    channel: str = "unstable",
    limit: int = 10,
) -> list[Package]:
    """
    Search for packages matching the query.

    Args:
        query: Search terms (name, description, or attribute)
        channel: NixOS channel to search (default: unstable)
        limit: Maximum results to return (default: 10)

    Returns:
        List of matching Package objects

    Raises:
        InvalidChannelError: If the channel doesn't exist
        APIError: If the search backend is unavailable

    Examples:
        >>> await search.search_packages("firefox")
        [Package(name="firefox", ...), ...]
    """
```

## Pull Request Process

### Before Submitting

1. **Run the full check suite**:
   ```bash
   make check
   make test
   ```

2. **Ensure all tests pass** (CI runs these automatically)

3. **Update documentation** if adding new features:
   - Add tool to `README.md` tool table
   - Update this file if changing development processes

4. **Write meaningful commit messages**:
   - Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
   - Keep the first line under 72 characters

### PR Guidelines

1. **One feature per PR**: Keep PRs focused and reviewable
2. **Include tests**: New features need corresponding tests
3. **Describe your changes**: Explain what and why in the PR description
4. **Link issues**: Reference any related issues

## Questions?

- Open an issue on [GitHub](https://github.com/felixdorn/mcp-nix/issues)
- Check existing issues for similar questions

Thank you for contributing!
