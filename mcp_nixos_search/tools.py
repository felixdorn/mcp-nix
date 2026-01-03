"""MCP tools for NixOS search."""

from . import mcp
from .search import APIError, InvalidChannelError, InvalidLimitError, NixOSSearch


def _format_error(e: Exception) -> str:
    """Format an exception for user display."""
    if isinstance(e, InvalidChannelError):
        return f"Error: Invalid channel '{e.channel}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidLimitError):
        return "Error: Limit must be 1-100"
    return f"Error: {e}"


@mcp.tool()
async def nixos_search_package(query: str, limit: int = 20, channel: str = "unstable") -> str:
    """Search NixOS packages.

    Args:
        query: Search term to look for
        limit: Maximum number of results to return (1-100)
        channel: NixOS channel to search in (e.g., "unstable", "25.11")
    """
    try:
        packages = NixOSSearch.search_packages(query, limit, channel)
    except APIError as e:
        return _format_error(e)

    if not packages:
        return f"No packages found matching '{query}'"

    header = f"Found {len(packages)} packages matching '{query}':\n"
    return header + "\n\n".join(pkg.format_short() for pkg in packages)


@mcp.tool()
async def nixos_search_option(query: str, limit: int = 20, channel: str = "unstable") -> str:
    """Search NixOS options.

    Args:
        query: Search term to look for
        limit: Maximum number of results to return (1-100)
        channel: NixOS channel to search in (e.g., "unstable", "25.11")
    """
    try:
        options = NixOSSearch.search_options(query, limit, channel)
    except APIError as e:
        return _format_error(e)

    if not options:
        return f"No options found matching '{query}'"

    header = f"Found {len(options)} options matching '{query}':\n"
    return header + "\n\n".join(opt.format_short() for opt in options)


@mcp.tool()
async def nixos_get_package_details(name: str, channel: str = "unstable") -> str:
    """Get detailed info about a NixOS package.

    Args:
        name: Name of the package to look up
        channel: NixOS channel to search in (e.g., "unstable", "25.11")
    """
    try:
        pkg = NixOSSearch.get_package(name, channel)
    except APIError as e:
        return _format_error(e)

    if pkg is None:
        return f"Error: Package '{name}' not found"

    return str(pkg)


@mcp.tool()
async def nixos_get_option_details(name: str, channel: str = "unstable") -> str:
    """Get detailed info about a NixOS option.

    Args:
        name: Name of the option to look up
        channel: NixOS channel to search in (e.g., "unstable", "25.11")
    """
    try:
        opt = NixOSSearch.get_option(name, channel)
    except APIError as e:
        return _format_error(e)

    if opt is None:
        return f"Error: Option '{name}' not found"

    return str(opt)


@mcp.tool()
async def nixos_channels() -> str:
    """List available NixOS channels."""
    try:
        channels = NixOSSearch.list_channels()
    except APIError as e:
        return _format_error(e)

    header = "NixOS Channels:\n"
    return header + "\n\n".join(str(ch) for ch in channels)
