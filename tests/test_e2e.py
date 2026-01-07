# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp
from mcp_nix import tools as _  # noqa: F401 - registers tools

pytestmark = pytest.mark.anyio


async def test_list_tools():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools.tools]
        assert "search_nixpkgs" in tool_names
        assert "search_options" in tool_names
        assert "list_versions" in tool_names
        assert "show_option_details" in tool_names
        assert "read_option_declaration" in tool_names


# =============================================================================
# Nixpkgs package tools tests
# =============================================================================


async def test_search_package():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nixpkgs", {"query": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_read_derivation():
    """Read derivation source for a package."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_derivation", {"name": "git"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "lines" in text
        assert "stdenv" in text or "mkDerivation" in text


# =============================================================================
# Unified options tools tests
# =============================================================================


async def test_search_options_nixos():
    """Search NixOS options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixos", "query": "nginx"})
        assert result.content
        text = result.content[0].text
        assert "nginx" in text.lower()


async def test_search_options_homemanager():
    """Search Home Manager options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "homemanager", "query": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_search_options_nixvim():
    """Search NixVim options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixvim", "query": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "colorscheme" in text.lower()


async def test_search_options_nix_nomad():
    """Search nix-nomad options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nix-nomad", "query": "job"})
        assert result.content
        text = result.content[0].text
        assert "job" in text.lower()


async def test_list_versions_nixos():
    """List NixOS versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "nixos"})
        assert result.content
        text = result.content[0].text
        assert "unstable" in text.lower()


async def test_list_versions_homemanager():
    """List Home Manager versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "homemanager"})
        assert result.content
        text = result.content[0].text
        assert "unstable" in text.lower()


async def test_list_versions_latest_only():
    """Projects without versions return just 'latest'."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "nixvim"})
        assert result.content
        text = result.content[0].text
        assert "latest" in text.lower()


async def test_show_option_details_nixos_leaf():
    """Leaf option returns full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "nixos", "name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "type:" in text.lower()
        assert "child options" not in text.lower()


async def test_show_option_details_nixos_prefix():
    """Prefix returns child options."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "nixos", "name": "services.nginx"})
        assert result.content
        text = result.content[0].text
        assert "child options" in text.lower()


async def test_show_option_details_homemanager_leaf():
    """Home Manager leaf option returns full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "homemanager", "name": "programs.git.enable"}
        )
        assert result.content
        text = result.content[0].text
        assert "type:" in text.lower()
        assert "child options" not in text.lower()


async def test_show_option_details_homemanager_prefix():
    """Home Manager prefix returns child options."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "homemanager", "name": "programs.git"})
        assert result.content
        text = result.content[0].text
        assert "child options" in text.lower()


async def test_show_option_details_nixvim():
    """Get NixVim option details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "nixvim", "name": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "colorscheme" in text.lower()
        assert "type:" in text.lower()


async def test_show_option_details_with_reference():
    """Leaf option includes reference with line count."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "nixos", "name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "lines" in text
        assert "read_option_declaration" in text


async def test_read_option_declaration_nixos():
    """Read NixOS option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "nixos", "name": "services.nginx.enable"}
        )
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "nginx" in text.lower()


async def test_read_option_declaration_homemanager():
    """Read Home Manager option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "homemanager", "name": "programs.git.enable"}
        )
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "git" in text.lower()


async def test_read_option_declaration_nixvim():
    """Read NixVim option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_option_declaration", {"project": "nixvim", "name": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text


async def test_read_option_declaration_nix_darwin():
    """Read nix-darwin option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "nix-darwin", "name": "system.defaults.dock.autohide"}
        )
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text


async def test_read_option_declaration_nix_nomad_not_supported():
    """nix-nomad doesn't support reading declarations."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_option_declaration", {"project": "nix-nomad", "name": "job"})
        assert result.content
        text = result.content[0].text
        assert "don't have readable declarations" in text.lower()


async def test_version_fallback():
    """Invalid version falls back with warning."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixos", "query": "nginx", "version": "99.99"})
        assert result.content
        text = result.content[0].text
        assert "not found" in text.lower() and "using" in text.lower()


async def test_invalid_project():
    """Invalid project returns error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "invalid-project", "query": "test"})
        assert result.content
        text = result.content[0].text
        assert "error" in text.lower()
        assert "invalid project" in text.lower()


# =============================================================================
# NixHub tools tests
# =============================================================================


async def test_nixhub_get_commit():
    """Get nixpkgs commit for a specific version."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "20.11.0"}
        )
        assert result.content
        text = result.content[0].text
        # It's unlikely nodejs 20.11.0 would change, and if it does, its trivially updatable.
        assert "10b813040df67c4039086db0f6eaf65c536886c6" in text


async def test_nixhub_version_not_found_shows_available():
    """Non-existent version should return error with available versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "999.999.999"}
        )
        assert result.content
        text = result.content[0].text
        assert "error" in text.lower()
        assert "not found" in text.lower()
        assert "available" in text.lower()


async def test_nixhub_package_not_found():
    """Non-existent package should return error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nonexistent-package-xyz123", "version": "1.0.0"}
        )
        assert result.content
        text = result.content[0].text
        assert "error" in text.lower() or "not found" in text.lower()


# =============================================================================
# Noogle tools tests
# =============================================================================


async def test_search_nix_stdlib():
    """Search for Nix standard library functions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nix_stdlib", {"query": "map"})
        assert result.content
        text = result.content[0].text
        assert "map" in text.lower()


async def test_help_for_stdlib_function():
    """Get details for a Nix stdlib function."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("help_for_stdlib_function", {"path": "lib.strings.splitString"})
        assert result.content
        text = result.content[0].text
        assert "splitstring" in text.lower()


async def test_help_for_stdlib_function_not_found():
    """Non-existent function should return error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("help_for_stdlib_function", {"path": "lib.nonexistent.xyz123"})
        assert result.content
        text = result.content[0].text
        assert "error" in text.lower() or "not found" in text.lower()
