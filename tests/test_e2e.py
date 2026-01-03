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
        assert "show_nixos_channels" in tool_names

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
        result = await client.call_tool("show_nixos_channels", {})
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
        result = await client.call_tool("show_homemanager_releases", {})
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
