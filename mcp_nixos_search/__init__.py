"""MCP server for NixOS package and option search."""

import argparse

from fastmcp import FastMCP

mcp = FastMCP("mcp-nixos-search")

# Tool categories: maps category name to list of tool names
TOOL_CATEGORIES = {
    "packages": ["nixos_search_package", "nixos_get_package_details"],
    "options": ["nixos_search_option", "nixos_get_option_details", "nixos_channels"],
    "homemanager": ["homemanager_search_option", "homemanager_get_option_details", "homemanager_releases"],
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="MCP server for NixOS package and option search",
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

    # Disable tools based on CLI flags
    for category, enabled in [
        ("packages", args.packages),
        ("options", args.options),
        ("homemanager", args.homemanager),
    ]:
        if not enabled:
            for tool_name in TOOL_CATEGORIES[category]:
                tool = mcp.get_tool(tool_name)
                if tool:
                    tool.disable()

    mcp.run()


if __name__ == "__main__":
    main()
