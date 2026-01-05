# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP server for Nixpkgs, NixOS and Home Manager."""

import argparse
import os

from fastmcp import FastMCP

mcp = FastMCP("mcp-nix")

# maps category ID to list of tool names
TOOL_CATEGORIES: dict[str, list[str]] = {
    "nixpkgs": ["search_nixpkgs", "show_nixpkgs_package", "read_derivation"],
    "nixos": ["search_nixos_options", "show_nixos_option", "list_nixos_channels", "read_nixos_module"],
    "homemanager": [
        "search_homemanager_options",
        "show_homemanager_option",
        "list_homemanager_releases",
        "read_home_module",
    ],
    "nixvim": ["search_nixvim_options", "show_nixvim_option", "read_nixvim_declaration"],
    "nix-darwin": ["search_nix_darwin_options", "show_nix_darwin_option", "read_nix_darwin_declaration"],
    "impermanence": ["search_impermanence_options", "show_impermanence_option", "read_impermanence_declaration"],
    "microvm": ["search_microvm_options", "show_microvm_option", "read_microvm_declaration"],
    "nixhub": ["list_package_versions", "find_nixpkgs_commit_with_package_version"],
    "noogle": ["search_nix_stdlib", "help_for_stdlib_function"],
}

# Tools excluded by default even when their category is enabled (use --include to enable)
DEFAULT_EXCLUDED_TOOLS: set[str] = {
    "read_derivation",
    "read_nixos_module",
    "read_home_module",
    "read_nixvim_declaration",
    "read_nix_darwin_declaration",
    "read_impermanence_declaration",
    "read_microvm_declaration",
}

CATEGORY_DEFAULT_INCLUSION_STATE: dict[str, bool] = {
    "nixpkgs": True,
    "nixos": True,
    "homemanager": False,
    "nixvim": False,
    "nix-darwin": False,
    "impermanence": False,
    "microvm": False,
    "nixhub": False,
    "noogle": False,
}

# All available tool names (flattened from categories)
ALL_TOOLS = [tool for tools in TOOL_CATEGORIES.values() for tool in tools]


def get_tool_category(tool: str) -> str | None:
    """Return the category a tool belongs to, or None if not found."""
    for category, tools in TOOL_CATEGORIES.items():
        if tool in tools:
            return category
    return None


def resolve_included_tools(
    category_overrides: dict[str, bool | None],
    include: set[str],
    exclude: set[str],
) -> set[str]:
    """
    Resolve which tools should be included based on category states and include/exclude lists.

    Resolution rules (in priority order):
    1. If tool is in exclude, or tool's category is in exclude: EXCLUDED
    2. If category is explicitly excluded (override=False): EXCLUDED
    3. If tool is in include (and not excluded by above): INCLUDED
    4. If tool is in DEFAULT_EXCLUDED_TOOLS: EXCLUDED
    5. Otherwise: use category's effective state (override or default)

    Args:
        category_overrides: Category ID -> True/False/None (None = use default)
        include: Set of tool names to explicitly include
        exclude: Set of tool names or category IDs to explicitly exclude

    Returns:
        Set of tool names that should be included
    """
    included_tools: set[str] = set()

    # Expand category IDs in exclude to their tools
    excluded_categories: set[str] = set()
    excluded_tools: set[str] = set()
    for item in exclude:
        if item in TOOL_CATEGORIES:
            excluded_categories.add(item)
        else:
            excluded_tools.add(item)

    for category, tools in TOOL_CATEGORIES.items():
        # Get effective category state
        override = category_overrides.get(category)
        category_included = override if override is not None else CATEGORY_DEFAULT_INCLUSION_STATE.get(category, False)
        category_explicitly_excluded = override is False

        for tool in tools:
            # Rule 1: exclude always wins
            if tool in excluded_tools or category in excluded_categories:
                continue

            # Rule 2: category explicitly excluded
            if category_explicitly_excluded:
                continue

            # Rule 3: include wins (if not excluded above)
            if tool in include:
                included_tools.add(tool)
                continue

            # Rule 4: default-excluded tools are excluded unless explicitly included
            if tool in DEFAULT_EXCLUDED_TOOLS:
                continue

            # Rule 5: use category state
            if category_included:
                included_tools.add(tool)

    return included_tools


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="MCP server for Nixpkgs, NixOS and Home Manager",
    )
    parser.add_argument(
        "--nixpkgs",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include Nixpkgs package tools (default: included)",
    )
    parser.add_argument(
        "--nixos",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include NixOS option tools (default: included)",
    )
    parser.add_argument(
        "--homemanager",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include home-manager tools (default: excluded)",
    )
    parser.add_argument(
        "--nixvim",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include NixVim option search tools (default: excluded)",
    )
    parser.add_argument(
        "--nix-darwin",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include nix-darwin option search tools (default: excluded)",
    )
    parser.add_argument(
        "--impermanence",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include impermanence option search tools (default: excluded)",
    )
    parser.add_argument(
        "--microvm",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include MicroVM.nix option search tools (default: excluded)",
    )
    parser.add_argument(
        "--nixhub",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include NixHub version tools (default: excluded)",
    )
    parser.add_argument(
        "--noogle",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include Noogle stdlib function tools (default: excluded)",
    )
    parser.add_argument(
        "--include",
        type=str,
        default="",
        help=f"Comma-separated list of tool names to include. Available: {', '.join(ALL_TOOLS)}",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help=f"Comma-separated list of tool/category names to exclude. Available: {', '.join(ALL_TOOLS)}",
    )
    return parser.parse_args()


def parse_tool_list(value: str) -> set[str]:
    """Parse a comma-separated list of tool names."""
    if not value:
        return set()
    return {name.strip() for name in value.split(",") if name.strip()}


def validate_tool_names(names: set[str], arg_name: str) -> None:
    """Validate that all names are valid tools or categories."""
    valid_names = set(ALL_TOOLS) | set(TOOL_CATEGORIES.keys())
    for name in names:
        if name not in valid_names:
            print(f"Error: Unknown tool/category '{name}' in {arg_name}. Available: {', '.join(sorted(valid_names))}")
            raise SystemExit(1)


def main() -> None:
    """Run the MCP server."""
    args = parse_args()

    # Parse and validate include/exclude lists
    include = parse_tool_list(args.include)
    exclude = parse_tool_list(args.exclude)
    validate_tool_names(include, "--include")
    validate_tool_names(exclude, "--exclude")

    # Build category overrides from CLI flags
    category_overrides: dict[str, bool | None] = {
        "nixpkgs": args.nixpkgs,
        "nixos": args.nixos,
        "homemanager": args.homemanager,
        "nixvim": args.nixvim,
        "nix-darwin": args.nix_darwin,
        "impermanence": args.impermanence,
        "microvm": args.microvm,
        "nixhub": args.nixhub,
        "noogle": args.noogle,
    }

    included_tools = resolve_included_tools(category_overrides, include, exclude)

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
