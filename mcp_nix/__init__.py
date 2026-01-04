# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP server for Nixpkgs, NixOS and Home Manager."""

import argparse

from fastmcp import FastMCP

mcp = FastMCP("mcp-nix")

# Tool categories: maps category name to list of tool names
TOOL_CATEGORIES = {
    "packages": ["search_nixpkgs", "show_nixpkgs_package"],
    "options": ["search_nixos_options", "show_nixos_option", "list_nixos_channels"],
    "homemanager": ["search_homemanager_options", "show_homemanager_option", "list_homemanager_releases"],
    "nixvim": ["search_nixvim_options", "show_nixvim_option"],
    "nix-darwin": ["search_nix_darwin_options", "show_nix_darwin_option"],
    "nixhub": ["list_package_versions", "find_nixpkgs_commit_with_package_version"],
}

# All available tool names (flattened from categories)
ALL_TOOLS = [tool for tools in TOOL_CATEGORIES.values() for tool in tools]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="MCP server for Nixpkgs, NixOS and Home Manager",
    )
    parser.add_argument(
        "--packages",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable package search tools (default: enabled)",
    )
    parser.add_argument(
        "--options",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable option search tools (default: enabled)",
    )
    parser.add_argument(
        "--homemanager",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable home-manager tools (default: disabled)",
    )
    parser.add_argument(
        "--nixvim",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable NixVim option search tools (default: disabled)",
    )
    parser.add_argument(
        "--nixhub",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable NixHub version tools (default: disabled)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help=f"Comma-separated list of tool names to exclude. Available: {', '.join(ALL_TOOLS)}",
    )
    return parser.parse_args()


def main() -> None:
    """Run the MCP server."""
    args = parse_args()

    # Parse excluded tools
    excluded_tools: list[str] = []
    if args.exclude:
        for tool_name in args.exclude.split(","):
            tool_name = tool_name.strip()
            if tool_name:
                if tool_name not in ALL_TOOLS:
                    print(f"Error: Unknown tool '{tool_name}'. Available: {', '.join(ALL_TOOLS)}")
                    raise SystemExit(1)
                excluded_tools.append(tool_name)

    # Import tools (registers them all with mcp)
    from . import tools as _tools  # noqa: F401

    # Remove tools based on CLI flags
    for category, enabled in [
        ("packages", args.packages),
        ("options", args.options),
        ("homemanager", args.homemanager),
        ("nixvim", args.nixvim),
        ("nixhub", args.nixhub),
    ]:
        if not enabled:
            for tool_name in TOOL_CATEGORIES[category]:
                mcp.remove_tool(tool_name)

    # Remove explicitly excluded tools
    for tool_name in excluded_tools:
        mcp.remove_tool(tool_name)

    mcp.run()


if __name__ == "__main__":
    main()
