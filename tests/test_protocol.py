"""Deterministic checks of errors as seen by an MCP client."""

from threading import Event
from types import SimpleNamespace

import anyio
import pytest
from jsonschema import validate
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp, tools
from mcp_nix.cache import APIError
from mcp_nix.models import Package, SearchResult
from mcp_nix.options import UnifiedOption
from mcp_nix.sources import CachedSource


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


@pytest.mark.anyio
async def test_catalog_advertises_read_only_tools_and_typed_results():
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        catalog = await client.list_tools()
        assert len(catalog.tools) == 9
        for tool in catalog.tools:
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.openWorldHint is True
            assert tool.outputSchema["properties"]["result"]["type"] == "string"


@pytest.mark.anyio
async def test_slow_backend_does_not_block_other_tools(monkeypatch):
    entered, release = Event(), Event()

    def slow(*args):
        entered.set()
        assert release.wait(3), "Protocol event loop could not release a blocked backend"
        return SearchResult(items=[Package(package_pname="git", package_pversion="1")], total=1)

    monkeypatch.setattr(tools.NixOSSearch, "search_packages", slow)
    async with (
        create_connected_server_and_client_session(mcp._mcp_server) as client,
        anyio.create_task_group() as group,
    ):
        group.start_soon(client.call_tool, "search_nixpkgs", {"query": "git"})
        try:
            assert await anyio.to_thread.run_sync(entered.wait, 1)
            with anyio.fail_after(1):
                result = await client.call_tool("list_versions", {"project": "nixvim"})
                assert result.isError is False
        finally:
            release.set()


@pytest.mark.anyio
async def test_source_lines_are_bounded_and_can_be_continued(monkeypatch):
    monkeypatch.setattr(tools.NixOSSearch, "get_package", lambda *args: SimpleNamespace(position="pkgs/git.nix:1"))
    monkeypatch.setattr(tools, "fetch_source", lambda url: CachedSource("one\ntwo\nthree\nfour\nfive\n", 5, url))
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("read_derivation", {"name": "git", "start_line": 3, "limit": 2})
        assert result.isError is False
        data = result.structuredContent
        assert data["total_lines"] == 5
        assert data["next_start_line"] == 5
        assert "three\nfour" in result.content[0].text
        assert "five" not in result.content[0].text
        catalog = await client.list_tools()
        schema = next(t.outputSchema for t in catalog.tools if t.name == "read_derivation")
        validate(data, schema)


@pytest.mark.anyio
async def test_child_options_are_paginated(monkeypatch):
    children = [UnifiedOption(f"services.test.x{i:02d}", "bool", "", "", "", None, "nixos") for i in range(70)]
    backend = SimpleNamespace(
        get_default_version=lambda: "unstable",
        validate_version=lambda v: (v, None),
        get_option=lambda *args: None,
        get_option_children=lambda *args: children,
    )
    monkeypatch.setattr(tools, "get_backend", lambda project: backend)
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        first = await client.call_tool("show_option_details", {"project": "nixos", "name": "services.test"})
        assert first.isError is False
        assert first.structuredContent["total"] == 70
        assert len(first.structuredContent["children"]) == 50
        second = await client.call_tool(
            "show_option_details",
            {"project": "nixos", "name": "services.test", "offset": first.structuredContent["next_offset"]},
        )
        assert len(second.structuredContent["children"]) == 20
        assert second.structuredContent["next_offset"] is None
