# tests/test_e2e.py
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nixos_search import mcp
from mcp_nixos_search import tools as _  # noqa: F401 - registers tools

pytestmark = pytest.mark.anyio

async def test_list_tools():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools.tools]
        assert "nixos_search_package" in tool_names
        assert "nixos_search_option" in tool_names
        assert "nixos_channels" in tool_names

async def test_search_package():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("nixos_search_package", {"query": "git", "limit": 3})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()

async def test_search_option():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("nixos_search_option", {"query": "nginx", "limit": 3})
        assert result.content
        text = result.content[0].text
        assert "nginx" in text.lower()

async def test_channels():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("nixos_channels", {})
        assert result.content
        text = result.content[0].text
        assert "unstable" in text.lower()

async def test_get_package_details():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("nixos_get_package_details", {"name": "git"})
        assert result.content
        text = result.content[0].text
        assert "git" in text.lower()

async def test_get_option_details():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("nixos_get_option_details", {"name": "services.nginx.enable"})
        assert result.content
        text = result.content[0].text
        assert "nginx" in text.lower()
