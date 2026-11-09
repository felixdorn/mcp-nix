"""Deterministic checks of errors as seen by an MCP client."""

from types import SimpleNamespace

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp, tools
from mcp_nix.cache import APIError


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool", "arguments", "package", "option", "supported", "message"),
    [
        ("read_derivation", {"name": "missing"}, None, None, True, "not found"),
        ("read_derivation", {"name": "missing"}, SimpleNamespace(position=""), None, True, "No source position"),
        ("read_option_declaration", {"project": "nixvim", "name": "missing"}, None, None, True, "not found"),
        (
            "read_option_declaration",
            {"project": "nixvim", "name": "missing"},
            None,
            SimpleNamespace(declaration_url=None),
            True,
            "No declaration URL",
        ),
        (
            "read_option_declaration",
            {"project": "nix-nomad", "name": "job"},
            None,
            None,
            False,
            "readable declarations",
        ),
    ],
)
async def test_explicit_failures_set_is_error(monkeypatch, tool, arguments, package, option, supported, message):
    monkeypatch.setattr(tools.NixOSSearch, "get_package", lambda *args: package)
    backend = SimpleNamespace(
        supports_declaration_read=lambda: supported,
        get_default_version=lambda: "latest",
        validate_version=lambda version: (version, None),
        get_option=lambda *args: option,
    )
    monkeypatch.setattr(tools, "get_backend", lambda project: backend)
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(tool, arguments)
        assert result.isError is True
        assert message in result.content[0].text


@pytest.mark.anyio
@pytest.mark.parametrize("name", ["search_options", "show_option_details", "read_option_declaration"])
async def test_version_discovery_failures_are_actionable(monkeypatch, name):
    def fail(version):
        raise APIError("Upstream unavailable; retry later")

    backend = SimpleNamespace(
        supports_declaration_read=lambda: True,
        get_default_version=lambda: "unstable",
        validate_version=fail,
    )
    monkeypatch.setattr(tools, "get_backend", lambda project: backend)
    arguments = {"project": "nixos", "query" if name == "search_options" else "name": "test"}
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(name, arguments)
        assert result.isError is True
        assert result.content[0].text == "Error: Upstream unavailable; retry later"
