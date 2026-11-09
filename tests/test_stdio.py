"""Exercise the actual entry point, stdio framing and tool exclusions."""

import os
import subprocess
import sys
from datetime import timedelta

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_nix import ALL_TOOLS


@pytest.mark.anyio
@pytest.mark.parametrize("excluded", [[], ["read_derivation", "read_option_declaration"]])
async def test_stdio_catalog_ping_and_call(tmp_path, excluded):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from mcp_nix import main; main()", "--exclude=" + ",".join(excluded)],
        env={**os.environ, "XDG_CACHE_HOME": str(tmp_path)},
    )
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as client,
    ):
        await client.initialize()
        await client.send_ping()
        catalog = await client.list_tools()
        assert {t.name for t in catalog.tools} == set(ALL_TOOLS) - set(excluded)
        result = await client.call_tool("list_versions", {"project": "nixvim"})
        assert result.isError is False
        assert result.structuredContent["versions"][0]["id"] == "latest"


def test_invalid_cli_arguments_use_stderr():
    result = subprocess.run(
        [sys.executable, "-c", "from mcp_nix import main; main()", "--exclude=missing"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Unknown tool" in result.stderr
