# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP tools for Nixpkgs, NixOS and Home Manager."""

from . import mcp
from .homemanager import HomeManagerSearch, InvalidReleaseError
from .nixhub import NixhubSearch, PackageNotFoundError, VersionNotFoundError
from .nuschtos import InvalidProjectError, NuschtosSearch
from .search import APIError, InvalidChannelError, NixOSSearch

_SEARCH_LIMIT = 20


def _format_error(e: Exception) -> str:
    """Format an exception for user display."""
    if isinstance(e, InvalidChannelError):
        return f"Error: Invalid channel '{e.channel}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidReleaseError):
        return f"Error: Invalid release '{e.release}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidProjectError):
        return f"Error: Invalid project '{e.project}'. Available: {', '.join(e.available)}"
    if isinstance(e, PackageNotFoundError):
        return f"Error: Package '{e.name}' not found on nixhub"
    if isinstance(e, VersionNotFoundError):
        versions_preview = ", ".join(e.available[:5])
        if len(e.available) > 5:
            versions_preview += f", ... ({len(e.available)} total)"
        return f"Error: Version '{e.version}' not found for '{e.name}'. Available: {versions_preview}"
    return f"Error: {e}"


@mcp.tool()
async def search_nixpkgs(query: str, channel: str = "unstable") -> str:
    """Search for Nixpkgs packages by name or description.

    Returns package names, versions, and descriptions. For full details (homepage, license), use
    show_nixpkgs_package with the exact package name.

    Args:
        query: Package name or keyword (e.g., "git", "video editor")
        channel: NixOS channel - "unstable" (latest) or version like "24.11", "25.05"
    """
    try:
        result = NixOSSearch.search_packages(query, _SEARCH_LIMIT, channel)
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No packages found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} packages:\n"
    else:
        header = f"Found {len(result.items)} packages:\n"
    return header + "\n\n".join(pkg.format_short() for pkg in result.items)


@mcp.tool()
async def search_nixos_options(query: str, channel: str = "unstable") -> str:
    """Search NixOS configuration options.

    NixOS options configure system-level services and settings. These are NOT options from Home Manager.

    Args:
        query: Option name fragment or keyword (e.g., "nginx", "services.postgresql", "boot.loader")
        channel: NixOS release - "unstable" or version like "24.11", "25.05"
    """
    try:
        result = NixOSSearch.search_options(query, _SEARCH_LIMIT, channel)
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No options found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} options:\n"
    else:
        header = f"Found {len(result.items)} options:\n"
    return header + "\n\n".join(opt.format_short() for opt in result.items)


@mcp.tool()
async def show_nixpkgs_package(name: str, channel: str = "unstable") -> str:
    """Get details for a Nixpkgs package by exact name.

    Returns version, description, homepage URL, and license. Use search_nixpkgs
    first if you don't know the exact package name.

    Args:
        name: Exact package name from search results (e.g., "git", "firefox")
        channel: NixOS channel - "unstable" or version like "24.11", "25.05"
    """
    try:
        pkg = NixOSSearch.get_package(name, channel)
    except APIError as e:
        return _format_error(e)

    if pkg is None:
        return f"Error: Package '{name}' not found"

    return str(pkg)


@mcp.tool()
async def show_nixos_option(name: str, channel: str = "unstable") -> str:
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
async def list_nixos_channels() -> str:
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
async def search_homemanager_options(query: str, release: str = "unstable") -> str:
    """Search Home Manager options for user environment configuration.

    Home Manager manages user dotfiles and programs: shells, editors, git, tmux, etc.
    Use this for per-user config (home.nix).

    Args:
        query: Option name or keyword (e.g., "git", "programs.zsh", "neovim plugin")
        release: Home Manager release - "unstable" or version like "24.11", "25.05"
    """
    try:
        result = HomeManagerSearch.search_options(query, _SEARCH_LIMIT, release)
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No Home Manager options found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} Home Manager options:\n"
    else:
        header = f"Found {len(result.items)} Home Manager options:\n"
    return header + "\n\n".join(opt.format_short() for opt in result.items)


@mcp.tool()
async def show_homemanager_option(name: str, release: str = "unstable") -> str:
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
async def list_homemanager_releases() -> str:
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


@mcp.tool()
async def search_nixvim_options(query: str) -> str:
    """Search NixVim configuration options.

    NixVim is a Neovim configuration framework for Nix. Search for plugins,
    colorschemes, keymaps, and other Neovim configuration options.

    Args:
        query: Option name or keyword (e.g., "colorscheme", "plugins.telescope", "keymaps")
    """
    try:
        result = NuschtosSearch.search_options(query, _SEARCH_LIMIT, "nixvim")
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No NixVim options found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} NixVim options:\n"
    else:
        header = f"Found {len(result.items)} NixVim options:\n"
    return header + "\n\n".join(opt.format_short() for opt in result.items)


@mcp.tool()
async def show_nixvim_option(name: str) -> str:
    """Get details for a NixVim option, or list all children if given a prefix.

    For leaf options like "colorschemes.catppuccin.enable", returns type, default, and description.
    For prefixes like "colorschemes.catppuccin", lists ALL child options exhaustively.

    Args:
        name: Option path or prefix (e.g., "colorschemes.catppuccin.enable" or "plugins.telescope")
    """
    try:
        # Try exact match first
        opt = NuschtosSearch.get_option(name, "nixvim")
        if opt is not None:
            return str(opt)

        # No exact match - get all children with this prefix
        children = NuschtosSearch.get_option_children(name, "nixvim")
        if children:
            header = f"'{name}' has {len(children)} child options:\n"
            return header + "\n\n".join(o.format_short() for o in children)

        return f"No option or children found for '{name}'"
    except APIError as e:
        return _format_error(e)


@mcp.tool()
async def search_nix_darwin_options(query: str) -> str:
    """Search nix-darwin configuration options for macOS.

    nix-darwin provides Nix modules for managing macOS system configuration,
    similar to NixOS but for Darwin/macOS systems.

    Args:
        query: Option name or keyword (e.g., "homebrew", "system.defaults", "launchd")
    """
    try:
        result = NuschtosSearch.search_options(query, _SEARCH_LIMIT, "nix-darwin")
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No nix-darwin options found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} nix-darwin options:\n"
    else:
        header = f"Found {len(result.items)} nix-darwin options:\n"
    return header + "\n\n".join(opt.format_short() for opt in result.items)


@mcp.tool()
async def show_nix_darwin_option(name: str) -> str:
    """Get details for a nix-darwin option, or list all children if given a prefix.

    For leaf options like "system.defaults.dock.autohide", returns type, default, and description.
    For prefixes like "system.defaults.dock", lists ALL child options exhaustively.

    Args:
        name: Option path or prefix (e.g., "system.defaults.dock.autohide" or "homebrew")
    """
    try:
        # Try exact match first
        opt = NuschtosSearch.get_option(name, "nix-darwin")
        if opt is not None:
            return str(opt)

        # No exact match - get all children with this prefix
        children = NuschtosSearch.get_option_children(name, "nix-darwin")
        if children:
            header = f"'{name}' has {len(children)} child options:\n"
            return header + "\n\n".join(o.format_short() for o in children)

        return f"No option or children found for '{name}'"
    except APIError as e:
        return _format_error(e)


@mcp.tool()
async def list_package_versions(name: str) -> str:
    """List all available versions for a Nixpkgs package.

    Returns version history with platform support and update dates.
    Use find_nixpkgs_commit_with_package_version with a specific version to get the nixpkgs
    commit hash for pinning.

    Args:
        name: Package name (e.g., "nodejs", "python", "git")
    """
    try:
        releases = NixhubSearch.get_versions(name)
    except APIError as e:
        return _format_error(e)

    if not releases:
        return f"No versions found for '{name}'"

    header = f"Found {len(releases)} versions for '{name}':\n"
    return header + "\n\n".join(r.format_short() for r in releases[:20])


@mcp.tool()
async def find_nixpkgs_commit_with_package_version(name: str, version: str) -> str:
    """Get the nixpkgs commit hash for a specific package version.

    Returns the commit hash that can be used to pin nixpkgs to get
    this exact package version. Use list_package_versions first to
    see available versions.

    Args:
        name: Package name (e.g., "nodejs", "python")
        version: Exact version string (e.g., "20.11.0", "3.12.1")
    """
    try:
        commit = NixhubSearch.get_commit(name, version)
    except APIError as e:
        return _format_error(e)

    return str(commit)
