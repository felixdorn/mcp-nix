"""MCP tools for NixOS search."""

from . import mcp
from .homemanager import HomeManagerSearch, InvalidReleaseError
from .search import APIError, InvalidChannelError, InvalidLimitError, NixOSSearch


def _format_error(e: Exception) -> str:
    """Format an exception for user display."""
    if isinstance(e, InvalidChannelError):
        return f"Error: Invalid channel '{e.channel}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidReleaseError):
        return f"Error: Invalid release '{e.release}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidLimitError):
        return "Error: Limit must be 1-100"
    return f"Error: {e}"


@mcp.tool()
async def nixos_search_package(query: str, limit: int = 20, channel: str = "unstable") -> str:
    """Search for NixOS packages by name or description.

    Returns package names, versions, and descriptions. For full details (homepage, license), use
    nixos_get_package_details with the exact package name.

    Args:
        query: Package name or keyword (e.g., "git", "video editor")
        limit: Max results 1-100 (default 20). Use lower values for common terms.
        channel: NixOS release channel - "unstable" (latest) or version like "24.11", "25.05"
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
    """Search NixOS system configuration options (for configuration.nix).

    NixOS options configure system-level services and settings: systemd services,
    networking, users, boot, filesystems, etc. These go in /etc/nixos/configuration.nix.
    NOT for user dotfiles - use homemanager_search_option for those.

    Args:
        query: Option name fragment or keyword (e.g., "nginx", "services.postgresql", "boot.loader")
        limit: Max results 1-100 (default 20)
        channel: NixOS release - "unstable" or version like "24.11", "25.05"
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
    """Get full details for a specific NixOS package by exact name.

    Returns version, description, homepage URL, and license. Use nixos_search_package
    first if you don't know the exact package name.

    Args:
        name: Exact package name from search results (e.g., "git", "firefox", "python312")
        channel: NixOS release - "unstable" or version like "24.11", "25.05"
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
    """Get details for a NixOS option, or list all children if given a prefix.

    For leaf options like "services.nginx.enable", returns type, default, and description.
    For prefixes like "services.nginx", lists ALL child options exhaustively.

    Args:
        name: Option path or prefix (e.g., "services.nginx.enable" or "services.nginx")
        channel: NixOS release - "unstable" or version like "24.11", "25.05"
    """
    try:
        # Try exact match first
        opt = NixOSSearch.get_option(name, channel)
        if opt is not None:
            return str(opt)

        # No exact match - get all children with this prefix
        children = NixOSSearch.get_option_children(name, channel)
        if children:
            header = f"'{name}' has {len(children)} child options:\n"
            return header + "\n\n".join(o.format_short() for o in children)

        return f"No option or children found for '{name}'"
    except APIError as e:
        return _format_error(e)


@mcp.tool()
async def nixos_channels() -> str:
    """List available NixOS release channels.

    Shows all channels (unstable, stable releases like 24.11, 25.05) that can be
    used with the 'channel' parameter in other NixOS tools.
    """
    try:
        channels = NixOSSearch.list_channels()
    except APIError as e:
        return _format_error(e)

    header = "NixOS Channels:\n"
    return header + "\n\n".join(str(ch) for ch in channels)


@mcp.tool()
async def homemanager_search_option(query: str, limit: int = 20, release: str = "unstable") -> str:
    """Search Home Manager options for user environment configuration.

    Home Manager manages user dotfiles and programs: shells, editors, git, tmux, etc.
    Use this for per-user config (home.nix). For system-level NixOS options, use
    nixos_search_option instead.

    Args:
        query: Option name or keyword (e.g., "git", "programs.zsh", "neovim plugin")
        limit: Max results 1-100 (default 20)
        release: Home Manager release - "unstable" or version like "24.11", "25.05"
    """
    try:
        options = HomeManagerSearch.search_options(query, limit, release)
    except APIError as e:
        return _format_error(e)

    if not options:
        return f"No Home Manager options found matching '{query}'"

    header = f"Found {len(options)} Home Manager options matching '{query}':\n"
    return header + "\n\n".join(opt.format_short() for opt in options)


@mcp.tool()
async def homemanager_get_option_details(name: str, release: str = "unstable") -> str:
    """Get details for a Home Manager option, or list all children if given a prefix.

    For leaf options like "programs.git.enable", returns type, default, and description.
    For prefixes like "programs.git", lists ALL child options exhaustively.

    Args:
        name: Option path or prefix (e.g., "programs.git.enable" or "programs.git")
        release: Home Manager release - "unstable" or version like "24.11", "25.05"
    """
    try:
        # Try exact match first
        opt = HomeManagerSearch.get_option(name, release)
        if opt is not None:
            return str(opt)

        # No exact match - get all children with this prefix
        children = HomeManagerSearch.get_option_children(name, release)
        if children:
            header = f"'{name}' has {len(children)} child options:\n"
            return header + "\n\n".join(o.format_short() for o in children)

        return f"No option or children found for '{name}'"
    except APIError as e:
        return _format_error(e)


@mcp.tool()
async def homemanager_releases() -> str:
    """List available Home Manager releases.

    Shows all releases (unstable, stable like 25.11, older versions) that can be
    used with the 'release' parameter in other Home Manager tools.
    """
    try:
        releases = HomeManagerSearch.list_releases()
    except APIError as e:
        return _format_error(e)

    header = "Home Manager Releases:\n"
    return header + "\n\n".join(str(r) for r in releases)
