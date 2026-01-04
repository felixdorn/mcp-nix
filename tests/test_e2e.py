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
        assert "search_nixos_options" in tool_names
        assert "list_nixos_channels" in tool_names


async def test_search_package():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nixpkgs", {"query": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_search_option():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nixos_options", {"query": "nginx"})
        assert result.content
        text = result.content[0].text
        assert "nginx" in text.lower()


async def test_channels():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_nixos_channels", {})
        assert result.content
        text = result.content[0].text
        assert "unstable" in text.lower()


async def test_get_package_details():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixpkgs_package", {"name": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_get_option_details():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixos_option", {"name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "nginx" in text.lower()


async def test_homemanager_search_option():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_homemanager_options", {"query": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_homemanager_get_option_details():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_homemanager_option", {"name": "programs.git.enable"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()


async def test_homemanager_releases():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_homemanager_releases", {})
        assert result.content
        text = result.content[0].text
        assert "unstable" in text.lower()


# Tests for prefix/children behavior - prevents regression
async def test_nixos_option_prefix_returns_children():
    """Prefix like 'services.nginx' should return child options, not error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixos_option", {"name": "services.nginx"})
        assert result.content
        text = result.content[0].text
        # Should list children, not return "not found"
        assert "child options" in text.lower()
        assert "services.nginx." in text  # Should have actual child options


async def test_homemanager_option_prefix_returns_children():
    """Prefix like 'programs.git' should return child options, not error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_homemanager_option", {"name": "programs.git"})
        assert result.content
        text = result.content[0].text
        # Should list children, not return "not found"
        assert "child options" in text.lower()
        assert "programs.git." in text  # Should have actual child options


async def test_nixos_option_leaf_returns_details():
    """Leaf option like 'services.nginx.enable' should return full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixos_option", {"name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        # Should have option details, not children list
        assert "type:" in text.lower()
        assert "child options" not in text.lower()


async def test_homemanager_option_leaf_returns_details():
    """Leaf option like 'programs.git.enable' should return full details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_homemanager_option", {"name": "programs.git.enable"})
        assert result.content
        text = result.content[0].text
        # Should have option details, not children list
        assert "type:" in text.lower()
        assert "child options" not in text.lower()


async def test_nixvim_search_option():
    """Search NixVim options."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("search_nixvim_options", {"query": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "colorscheme" in text.lower()


async def test_nixvim_get_option_details():
    """Get NixVim option details."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixvim_option", {"name": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "colorscheme" in text.lower()
        assert "type:" in text.lower()


async def test_nixhub_list_package_versions():
    """List available versions for a package."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_package_versions", {"name": "nodejs"})
        assert result.content
        text = result.content[0].text
        assert "versions" in text.lower()


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


async def test_nixhub_package_not_found():
    """Non-existent package should return error."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("list_package_versions", {"name": "nonexistent-package-xyz123"})
        assert result.content
        text = result.content[0].text
        assert "error" in text.lower() or "not found" in text.lower()


# Declaration tools tests
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


async def test_read_nixos_module():
    """Read NixOS module source for an option."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_nixos_module", {"name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "lines" in text
        assert "nginx" in text.lower()


async def test_read_home_module():
    """Read Home Manager module source for an option."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_home_module", {"name": "programs.git.enable"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "lines" in text
        assert "git" in text.lower()


async def test_read_nixvim_declaration():
    """Read NixVim declaration source for an option."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_nixvim_declaration", {"name": "colorscheme"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "lines" in text


async def test_read_nix_darwin_declaration():
    """Read nix-darwin declaration source for an option."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_nix_darwin_declaration", {"name": "system.defaults.dock.autohide"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "Source:" in text
        assert "lines" in text


async def test_show_nixpkgs_package_has_reference():
    """show_nixpkgs_package should include Reference with line count."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixpkgs_package", {"name": "git"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "lines" in text
        assert "read_derivation" in text


async def test_show_nixos_option_has_reference():
    """show_nixos_option should include Reference with line count."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_nixos_option", {"name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "lines" in text
        assert "read_nixos_module" in text


async def test_show_homemanager_option_has_reference():
    """show_homemanager_option should include Reference with line count."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("show_homemanager_option", {"name": "programs.git.enable"})
        assert result.content
        text = result.content[0].text
        assert "Reference:" in text
        assert "lines" in text
        assert "read_home_module" in text


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
