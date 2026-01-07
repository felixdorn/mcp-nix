# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP server for Nixpkgs, NixOS and Home Manager."""

import argparse
import os

from fastmcp import FastMCP

mcp = FastMCP("mcp-nix")

# All available tools (flat list, all enabled by default)
ALL_TOOLS = [
    # Nixpkgs
    "search_nixpkgs",
    "read_derivation",
    # Options (unified)
    "search_options",
    "list_versions",
    "show_option_details",
    "read_option_declaration",
    # NixHub
    "find_nixpkgs_commit_with_package_version",
    # Noogle
    "search_nix_stdlib",
    "help_for_stdlib_function",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="MCP server for Nixpkgs, NixOS and Home Manager",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help=f"Comma-separated list of tool names to exclude. Available: {', '.join(ALL_TOOLS)}",
    )

    # Deprecated flags - kept for backwards compatibility, silently ignored
    parser.add_argument("--nixpkgs", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--options", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--nixhub", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--noogle", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--nixos", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--homemanager", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--nixvim", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--nix-darwin", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--impermanence", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--microvm", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--nix-nomad", action=argparse.BooleanOptionalAction, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--include", type=str, default="", help=argparse.SUPPRESS)

    return parser.parse_args()


def parse_tool_list(value: str) -> set[str]:
    """Parse a comma-separated list of tool names."""
    if not value:
        return set()
    return {name.strip() for name in value.split(",") if name.strip()}


def validate_tool_names(names: set[str], arg_name: str) -> None:
    """Validate that all names are valid tools."""
    valid_names = set(ALL_TOOLS)
    for name in names:
        if name not in valid_names:
            print(f"Error: Unknown tool '{name}' in {arg_name}. Available: {', '.join(sorted(valid_names))}")
            raise SystemExit(1)


def main() -> None:
    """Run the MCP server."""
    args = parse_args()

    # Parse and validate exclude list
    exclude = parse_tool_list(args.exclude)
    validate_tool_names(exclude, "--exclude")

    # All tools enabled by default, minus excluded ones
    included_tools = set(ALL_TOOLS) - exclude

    from . import tools as _tools  # noqa: F401

    for tool in ALL_TOOLS:
        if tool not in included_tools:
            mcp.remove_tool(tool)

    try:
        mcp.run()
    except KeyboardInterrupt:
        os._exit(0)


if __name__ == "__main__":
    main()
