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
}


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
    return parser.parse_args()


def main() -> None:
    """Run the MCP server."""
    args = parse_args()

    # Import tools (registers them all with mcp)
    from . import tools as _tools  # noqa: F401

    # Remove tools based on CLI flags
    for category, enabled in [
        ("packages", args.packages),
        ("options", args.options),
        ("homemanager", args.homemanager),
    ]:
        if not enabled:
            for tool_name in TOOL_CATEGORIES[category]:
                mcp.remove_tool(tool_name)

    mcp.run()


if __name__ == "__main__":
    main()
