# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP tools for Nixpkgs, NixOS and Home Manager."""

from . import mcp
from .nixhub import NixhubSearch, PackageNotFoundError, VersionNotFoundError
from .noogle import FunctionNotFoundError, NoogleSearch
from .options import InvalidProjectError, get_backend
from .search import APIError, InvalidChannelError, NixOSSearch
from .sources import fetch_source, get_line_count

_SEARCH_LIMIT = 20


def _position_to_github_url(position: str, channel: str) -> str | None:
    """Convert nixpkgs position to GitHub URL."""
    if not position:
        return None
    # Position format: path/to/file.nix:line
    parts = position.split(":")
    if not parts:
        return None
    file_path = parts[0]
    branch = "nixos-unstable" if channel == "unstable" else f"nixos-{channel}"
    return f"https://github.com/NixOS/nixpkgs/blob/{branch}/{file_path}"


def _format_error(e: Exception) -> str:
    """Format an exception for user display."""
    if isinstance(e, InvalidChannelError):
        return f"Error: Invalid channel '{e.channel}'. Available: {', '.join(e.available)}"
    if isinstance(e, InvalidProjectError):
        return f"Error: Invalid project '{e.project}'. Available: {', '.join(e.available)}"
    if isinstance(e, PackageNotFoundError):
        return f"Error: Package '{e.name}' not found on nixhub"
    if isinstance(e, VersionNotFoundError):
        versions_preview = ", ".join(e.available[:5])
        if len(e.available) > 5:
            versions_preview += f", ... ({len(e.available)} total)"
        return f"Error: Version '{e.version}' not found for '{e.name}'. Available: {versions_preview}"
    if isinstance(e, FunctionNotFoundError):
        return f"Error: Function '{e.path}' not found on Noogle"
    return f"Error: {e}"


# =============================================================================
# Nixpkgs package tools
# =============================================================================


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
async def read_derivation(name: str, channel: str = "unstable") -> str:
    """Read the Nix source code for a package derivation.

    Fetches and returns the .nix file that defines a package. Use search_nixpkgs
    first if you don't know the exact package name.

    Args:
        name: Exact package name (e.g., "git", "firefox")
        channel: NixOS channel - "unstable" or version like "24.11", "25.05"
    """
    try:
        pkg = NixOSSearch.get_package(name, channel)
    except APIError as e:
        return _format_error(e)

    if pkg is None:
        return f"Error: Package '{name}' not found"

    if not pkg.position:
        return f"Error: No source position available for '{name}'"

    url = _position_to_github_url(pkg.position, channel)
    if not url:
        return f"Error: Could not determine source URL for '{name}'"

    try:
        source = fetch_source(url)
    except APIError as e:
        return _format_error(e)

    return f"Reference: {url}\nSource: {source.line_count} lines\n\n{source.content}"


# =============================================================================
# Unified options tools
# =============================================================================


@mcp.tool()
async def search_options(project: str, query: str, version: str = "") -> str:
    """Search configuration options for a Nix project.

    Searches NixOS, Home Manager, NixVim, nix-darwin, impermanence, MicroVM, or nix-nomad
    options by name or description.

    Args:
        project: Project to search - one of: nixos, homemanager, nixvim, nix-darwin,
                 impermanence, microvm, nix-nomad
        query: Search term (e.g., "nginx", "programs.git", "colorscheme")
        version: Version/channel to search. For nixos: "unstable", "24.11", "25.05".
                 For homemanager: "unstable", "24.11", "25.05". Other projects only
                 support "latest". If omitted, uses the default version.
    """
    try:
        backend = get_backend(project)
    except InvalidProjectError as e:
        return _format_error(e)

    # Handle version
    effective_version = version or backend.get_default_version()
    effective_version, warning = backend.validate_version(effective_version)

    try:
        result = backend.search_options(query, _SEARCH_LIMIT, effective_version)
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No {project} options found matching '{query}'"

    header = ""
    if warning:
        header = f"Note: {warning}\n\n"

    if result.total > len(result.items):
        header += f"Showing {len(result.items)} of {result.total} options:\n"
    else:
        header += f"Found {len(result.items)} options:\n"

    return header + "\n\n".join(opt.format_short() for opt in result.items)


@mcp.tool()
async def list_versions(project: str) -> str:
    """List available versions for a Nix project.

    Returns available versions/channels that can be used with the version parameter
    in search_options and show_option_details.

    Args:
        project: Project name - one of: nixos, homemanager, nixvim, nix-darwin,
                 impermanence, microvm, nix-nomad
    """
    try:
        backend = get_backend(project)
    except InvalidProjectError as e:
        return _format_error(e)

    try:
        versions = backend.list_versions()
    except APIError as e:
        return _format_error(e)

    header = f"{project} versions:\n"
    return header + "\n\n".join(str(v) for v in versions)


@mcp.tool()
async def show_option_details(project: str, name: str, version: str = "") -> str:
    """Get details for an option, or list all children if given a prefix.

    For leaf options like "services.nginx.enable", returns type, default, and description.
    For prefixes like "services.nginx", lists ALL child options exhaustively.

    Args:
        project: Project name - one of: nixos, homemanager, nixvim, nix-darwin,
                 impermanence, microvm, nix-nomad
        name: Option path or prefix (e.g., "services.nginx.enable" or "programs.git")
        version: Version to use. If omitted, uses the default version.
    """
    try:
        backend = get_backend(project)
    except InvalidProjectError as e:
        return _format_error(e)

    effective_version = version or backend.get_default_version()
    effective_version, warning = backend.validate_version(effective_version)

    header = ""
    if warning:
        header = f"Note: {warning}\n\n"

    try:
        # Try exact match first
        opt = backend.get_option(name, effective_version)
        if opt is not None:
            result = str(opt)
            if opt.declaration_url:
                line_count = get_line_count(opt.declaration_url)
                if line_count and backend.supports_declaration_read():
                    result += (
                        f"\nReference: {opt.declaration_url} ({line_count} lines, use read_option_declaration to read)"
                    )
                elif line_count:
                    result += f"\nReference: {opt.declaration_url} ({line_count} lines)"
                else:
                    result += f"\nReference: {opt.declaration_url}"
            return header + result

        # No exact match - get children
        children = backend.get_option_children(name, effective_version)
        if children:
            child_header = f"'{name}' has {len(children)} child options:\n"
            return header + child_header + "\n\n".join(o.format_short() for o in children)

        return header + f"No option or children found for '{name}'"
    except APIError as e:
        return _format_error(e)


@mcp.tool()
async def read_option_declaration(project: str, name: str, version: str = "") -> str:
    """Read the Nix source code for an option declaration.

    Fetches and returns the module file that declares an option.
    Use search_options or show_option_details first to find the option name.

    Note: nix-nomad options don't have readable declarations as they are
    auto-generated from Nomad HCL specifications.

    Args:
        project: Project name - one of: nixos, homemanager, nixvim, nix-darwin,
                 impermanence, microvm (nix-nomad not supported)
        name: Exact option path (e.g., "services.nginx.enable")
        version: Version to use. If omitted, uses the default version.
    """
    try:
        backend = get_backend(project)
    except InvalidProjectError as e:
        return _format_error(e)

    if not backend.supports_declaration_read():
        return (
            f"Error: {project} options don't have readable declarations. "
            "They are auto-generated from external specifications (Nomad HCL)."
        )

    effective_version = version or backend.get_default_version()
    effective_version, warning = backend.validate_version(effective_version)

    header = ""
    if warning:
        header = f"Note: {warning}\n\n"

    try:
        opt = backend.get_option(name, effective_version)
    except APIError as e:
        return _format_error(e)

    if opt is None:
        return f"Error: Option '{name}' not found"

    url = opt.declaration_url
    if not url:
        return f"Error: No declaration URL available for '{name}'"

    try:
        source = fetch_source(url)
    except APIError as e:
        return _format_error(e)

    return header + f"Reference: {url}\nSource: {source.line_count} lines\n\n{source.content}"


# =============================================================================
# NixHub tools
# =============================================================================


@mcp.tool()
async def find_nixpkgs_commit_with_package_version(name: str, version: str) -> str:
    """Get the nixpkgs commit hash for a specific package version.

    Returns the commit hash that can be used to pin nixpkgs to get
    this exact package version. If the version is not found, returns
    available versions for the package.

    Args:
        name: Package name (e.g., "nodejs", "python")
        version: Exact version string (e.g., "20.11.0", "3.12.1")
    """
    try:
        commit = NixhubSearch.get_commit(name, version)
    except APIError as e:
        return _format_error(e)

    return str(commit)


# =============================================================================
# Noogle tools
# =============================================================================


@mcp.tool()
async def search_nix_stdlib(query: str) -> str:
    """Search Nix standard library functions by name or type signature.

    Searches noogle.dev for Nix builtins and lib functions. Use this to find
    functions for string manipulation, list operations, attribute sets, etc.

    Args:
        query: Function name or keyword (e.g., "map", "filter", "strings", "attrset")
    """
    try:
        result = NoogleSearch.search_functions(query, _SEARCH_LIMIT)
    except APIError as e:
        return _format_error(e)

    if not result.items:
        return f"No Nix stdlib functions found matching '{query}'"

    if result.total > len(result.items):
        header = f"Showing {len(result.items)} of {result.total} functions:\n"
    else:
        header = f"Found {len(result.items)} functions:\n"
    return header + "\n\n".join(fn.format_short() for fn in result.items)


@mcp.tool()
async def help_for_stdlib_function(path: str) -> str:
    """Get detailed help for a Nix standard library function.

    Returns type signature, description, arguments, and examples.
    Use search_nix_stdlib first if you don't know the exact function path.

    Args:
        path: Function path (e.g., "lib.strings.splitString", "builtins.map", "lib.attrsets.mapAttrs")
    """
    try:
        func = NoogleSearch.get_function(path)
    except APIError as e:
        return _format_error(e)

    return str(func)
