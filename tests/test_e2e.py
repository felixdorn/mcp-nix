# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp
from mcp_nix import tools as _  # noqa: F401 - registers tools

pytestmark = pytest.mark.anyio


async def test_list_tools(snapshot):
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        tool_names = sorted([t.name for t in tools.tools])
        assert tool_names == snapshot


# =============================================================================
# Nixpkgs package tools tests
# =============================================================================


async def test_search_package(snapshot):
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nixpkgs", {"query": "git", "channel": "25.11"})
        assert result.content[0].text == snapshot


async def test_read_derivation(snapshot):
    """Read derivation source for a package."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_derivation", {"name": "git", "channel": "25.11"})
        assert result.content[0].text == snapshot


# =============================================================================
# Unified options tools tests
# =============================================================================


async def test_search_options_nixos(snapshot):
    """Search NixOS options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixos", "query": "time.timeZone", "version": "25.11"})
        assert result.content[0].text == snapshot


async def test_search_options_homemanager(snapshot):
    """Search Home Manager options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "search_options", {"project": "homemanager", "query": "git", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_search_options_nixvim(snapshot):
    """Search NixVim options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixvim", "query": "colorscheme"})
        assert result.content[0].text == snapshot


async def test_search_options_nix_nomad(snapshot):
    """Search nix-nomad options via unified tool."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nix-nomad", "query": "job"})
        assert result.content[0].text == snapshot


async def test_list_versions_nixos(snapshot):
    """List NixOS versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "nixos"})
        assert result.content[0].text == snapshot


async def test_list_versions_homemanager(snapshot):
    """List Home Manager versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "homemanager"})
        assert result.content[0].text == snapshot


async def test_list_versions_latest_only(snapshot):
    """Projects without versions return just 'latest'."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_versions", {"project": "nixvim"})
        assert result.content[0].text == snapshot


async def test_show_option_details_nixos_leaf(snapshot):
    """Leaf option returns full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "nixos", "name": "time.timeZone", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_show_option_details_nixos_prefix(snapshot):
    """Prefix returns child options."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "nixos", "name": "time", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_show_option_details_homemanager_leaf(snapshot):
    """Home Manager leaf option returns full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "homemanager", "name": "programs.git.enable", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_show_option_details_homemanager_prefix(snapshot):
    """Home Manager prefix returns child options."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "homemanager", "name": "programs.git", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_show_option_details_nixvim(snapshot):
    """Get NixVim option details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_option_details", {"project": "nixvim", "name": "colorscheme"})
        assert result.content[0].text == snapshot


async def test_show_option_details_with_reference(snapshot):
    """Leaf option includes reference with line count."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "show_option_details", {"project": "nixos", "name": "time.timeZone", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_read_option_declaration_nixos(snapshot):
    """Read NixOS option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "nixos", "name": "time.timeZone", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_read_option_declaration_homemanager(snapshot):
    """Read Home Manager option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "homemanager", "name": "programs.git.enable", "version": "25.11"}
        )
        assert result.content[0].text == snapshot


async def test_read_option_declaration_nixvim(snapshot):
    """Read NixVim option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_option_declaration", {"project": "nixvim", "name": "colorscheme"})
        assert result.content[0].text == snapshot


async def test_read_option_declaration_nix_darwin(snapshot):
    """Read nix-darwin option source code."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "read_option_declaration", {"project": "nix-darwin", "name": "system.stateVersion"}
        )
        assert result.content[0].text == snapshot


async def test_read_option_declaration_nix_nomad_not_supported(snapshot):
    """nix-nomad doesn't support reading declarations."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_option_declaration", {"project": "nix-nomad", "name": "job"})
        assert result.content[0].text == snapshot


async def test_version_fallback(snapshot):
    """Invalid version falls back with warning."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "nixos", "query": "time.timeZone", "version": "99.99"})
        assert result.content[0].text == snapshot


async def test_invalid_project(snapshot):
    """Invalid project returns error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_options", {"project": "invalid-project", "query": "test"})
        assert result.content[0].text == snapshot


# =============================================================================
# NixHub tools tests
# =============================================================================


async def test_nixhub_get_commit(snapshot):
    """Get nixpkgs commit for a specific version."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "20.11.0"}
        )
        assert result.content[0].text == snapshot


async def test_nixhub_version_not_found_shows_available(snapshot):
    """Non-existent version should return error with available versions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "999.999.999"}
        )
        assert result.content[0].text == snapshot


async def test_nixhub_package_not_found(snapshot):
    """Non-existent package should return error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(
            "find_nixpkgs_commit_with_package_version", {"name": "nonexistent-package-xyz123", "version": "1.0.0"}
        )
        assert result.content[0].text == snapshot


# =============================================================================
# Noogle tools tests
# =============================================================================


async def test_search_nix_stdlib(snapshot):
    """Search for Nix standard library functions."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nix_stdlib", {"query": "map"})
        assert result.content[0].text == snapshot


async def test_help_for_stdlib_function(snapshot):
    """Get details for a Nix stdlib function."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("help_for_stdlib_function", {"path": "lib.strings.splitString"})
        assert result.content[0].text == snapshot


async def test_help_for_stdlib_function_not_found(snapshot):
    """Non-existent function should return error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("help_for_stdlib_function", {"path": "lib.nonexistent.xyz123"})
        assert result.content[0].text == snapshot
