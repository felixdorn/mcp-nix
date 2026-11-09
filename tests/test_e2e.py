# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in live contracts: upstream data may change without a repository commit."""

import re

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_nix import mcp
from mcp_nix import tools as _  # noqa: F401
from mcp_nix.options import SUPPORTED_PROJECTS

pytestmark = [pytest.mark.anyio, pytest.mark.live]


async def call(name, arguments):
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(name, arguments)
        assert result.isError is False, result.content[0].text
        assert result.structuredContent is not None
        return result.structuredContent


async def test_package_search():
    result = await call("search_nixpkgs", {"query": "ripgrep", "limit": 5})
    assert any(item["attribute"] == "ripgrep" for item in result["items"])
    assert result["total"] >= len(result["items"]) > 0


@pytest.mark.parametrize("project", SUPPORTED_PROJECTS)
async def test_search_options(project):
    query = {
        "nixos": "nginx",
        "homemanager": "git",
        "nixvim": "colorscheme",
        "nix-darwin": "zsh",
        "impermanence": "persistence",
        "microvm": "microvm",
        "simple-nixos-mailserver": "mailserver",
        "sops-nix": "sops",
        "nixos-hardware": "hardware",
        "disko": "disko",
        "nix-nomad": "job",
    }[project]
    result = await call("search_options", {"project": project, "query": query, "limit": 3})
    assert result["items"]
    assert all(item["project"] == project for item in result["items"])


@pytest.mark.parametrize(
    ("project", "name", "version"),
    [
        ("nixos", "time.timeZone", "unstable"),
        ("homemanager", "programs.git.enable", "25.11"),
        ("nixvim", "colorscheme", "latest"),
        ("nix-darwin", "programs.zsh.enable", "latest"),
        ("nix-nomad", "job", "latest"),
    ],
)
async def test_option_lookup(project, name, version):
    result = await call("show_option_details", {"project": project, "name": name, "version": version})
    assert result["option"]["name"] == name
    assert result["option"]["type"]


@pytest.mark.parametrize("project", ["nixos", "homemanager", "nixvim"])
async def test_versions(project):
    result = await call("list_versions", {"project": project})
    assert result["versions"]
    assert any(v["is_default"] for v in result["versions"])


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("read_derivation", {"name": "ripgrep", "limit": 10}),
        ("read_option_declaration", {"project": "nixos", "name": "time.timeZone", "limit": 10}),
        ("read_option_declaration", {"project": "homemanager", "name": "programs.git.enable", "limit": 10}),
        ("read_option_declaration", {"project": "nixvim", "name": "colorscheme", "limit": 10}),
        ("read_option_declaration", {"project": "nix-darwin", "name": "programs.zsh.enable", "limit": 10}),
    ],
)
async def test_source_reading(tool, arguments):
    result = await call(tool, arguments)
    assert result["total_lines"] > 0
    assert result["end_line"] <= 10
    assert result["url"].startswith("https://")


async def test_historical_package_commit():
    result = await call("find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "20.11.0"})
    assert result["commit"]["version"] == "20.11.0"
    assert re.fullmatch(r"[0-9a-f]{40}", result["commit"]["commit_hash"])


async def test_noogle_search_and_help():
    search = await call("search_nix_stdlib", {"query": "map", "limit": 10})
    assert any(item["path"] == "builtins.map" for item in search["items"])
    function = (await call("help_for_stdlib_function", {"path": "lib.strings.splitString"}))["function"]
    assert function["path"] == "lib.strings.splitString"
    assert function["inputs"] and function["examples"]


@pytest.mark.parametrize(
    ("tool", "arguments", "hint"),
    [
        ("search_nixpkgs", {"query": "git", "channel": "not-a-channel"}, "Available:"),
        ("find_nixpkgs_commit_with_package_version", {"name": "nodejs", "version": "999.999.999"}, "Available:"),
        (
            "find_nixpkgs_commit_with_package_version",
            {"name": "nonexistent-package-xyz123", "version": "1"},
            "not found",
        ),
        ("help_for_stdlib_function", {"path": "lib.nonexistent.xyz123"}, "not found"),
    ],
)
async def test_live_errors(tool, arguments, hint):
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool(tool, arguments)
        assert result.isError is True
        assert hint in result.content[0].text
