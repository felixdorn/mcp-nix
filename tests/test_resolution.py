# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for tool resolution logic."""

from mcp_nix import DEFAULT_EXCLUDED_TOOLS, TOOL_CATEGORIES, resolve_included_tools


class TestResolveIncludedTools:
    """Tests for resolve_included_tools function."""

    def test_defaults_only(self):
        """With no overrides, uses category defaults (nixpkgs+nixos included)."""
        result = resolve_included_tools({}, set(), set())

        # nixpkgs and nixos are included by default
        assert "search_nixpkgs" in result
        assert "show_nixpkgs_package" in result
        assert "search_nixos_options" in result

        # homemanager, nixvim, nix-darwin, nixhub excluded by default
        assert "search_homemanager_options" not in result
        assert "search_nixvim_options" not in result
        assert "search_nix_darwin_options" not in result
        assert "list_package_versions" not in result

        # default-excluded tools not included even when their category is enabled
        assert "read_derivation" not in result
        assert "read_nixos_module" not in result

    def test_include_excluded_category(self):
        """Including an excluded-by-default category includes its tools."""
        result = resolve_included_tools({"homemanager": True}, set(), set())

        assert "search_homemanager_options" in result
        assert "show_homemanager_option" in result
        assert "list_homemanager_releases" in result

    def test_exclude_included_category(self):
        """Excluding an included-by-default category excludes its tools."""
        result = resolve_included_tools({"nixpkgs": False}, set(), set())

        assert "search_nixpkgs" not in result
        assert "show_nixpkgs_package" not in result
        # nixos still included
        assert "search_nixos_options" in result

    def test_include_tool_from_excluded_category(self):
        """Including a tool from an excluded-by-default category includes just that tool."""
        result = resolve_included_tools({}, {"search_homemanager_options"}, set())

        # Only the included tool, not the whole category
        assert "search_homemanager_options" in result
        assert "show_homemanager_option" not in result
        assert "list_homemanager_releases" not in result

    def test_exclude_tool_from_included_category(self):
        """Excluding a tool from an included category excludes just that tool."""
        result = resolve_included_tools({}, set(), {"search_nixpkgs"})

        assert "search_nixpkgs" not in result
        # Other tools in category still included
        assert "show_nixpkgs_package" in result

    def test_exclude_beats_include_same_tool(self):
        """When same tool is in both include and exclude, exclude wins."""
        result = resolve_included_tools({}, {"search_homemanager_options"}, {"search_homemanager_options"})

        assert "search_homemanager_options" not in result

    def test_exclude_category_beats_include_tool(self):
        """Excluding a category beats including a tool from that category."""
        result = resolve_included_tools({}, {"search_homemanager_options"}, {"homemanager"})

        assert "search_homemanager_options" not in result
        assert "show_homemanager_option" not in result

    def test_explicit_category_exclude_beats_include(self):
        """Category explicitly excluded (--no-category) beats include."""
        result = resolve_included_tools({"homemanager": False}, {"search_homemanager_options"}, set())

        assert "search_homemanager_options" not in result

    def test_include_with_category_not_explicitly_excluded(self):
        """Include works when category is excluded by default but not explicitly."""
        # homemanager is excluded by default, but not explicitly set to False
        result = resolve_included_tools({}, {"search_homemanager_options"}, set())

        assert "search_homemanager_options" in result

    def test_exclude_entire_category(self):
        """Excluding by category name excludes all tools in that category."""
        result = resolve_included_tools({}, set(), {"nixpkgs"})

        assert "search_nixpkgs" not in result
        assert "show_nixpkgs_package" not in result
        # Other categories unaffected
        assert "search_nixos_options" in result

    def test_multiple_includes(self):
        """Multiple tools can be included."""
        result = resolve_included_tools({}, {"search_homemanager_options", "search_nixvim_options"}, set())

        assert "search_homemanager_options" in result
        assert "search_nixvim_options" in result
        # But not other tools from those categories
        assert "show_homemanager_option" not in result
        assert "show_nixvim_option" not in result

    def test_multiple_excludes(self):
        """Multiple tools can be excluded."""
        result = resolve_included_tools({}, set(), {"search_nixpkgs", "search_nixos_options"})

        assert "search_nixpkgs" not in result
        assert "search_nixos_options" not in result
        # But other tools in those categories still work
        assert "show_nixpkgs_package" in result
        assert "show_nixos_option" in result

    def test_complex_scenario(self):
        """Complex scenario with multiple overrides, includes, and excludes."""
        result = resolve_included_tools(
            category_overrides={
                "nixpkgs": None,  # use default (included)
                "nixos": False,  # explicitly excluded
                "homemanager": True,  # explicitly included
            },
            include={"search_nixvim_options", "search_nixos_options"},
            exclude={"show_homemanager_option"},
        )

        # nixpkgs: included by default
        assert "search_nixpkgs" in result
        assert "show_nixpkgs_package" in result

        # nixos: explicitly excluded, include doesn't help
        assert "search_nixos_options" not in result
        assert "show_nixos_option" not in result

        # homemanager: explicitly included, but one tool excluded
        assert "search_homemanager_options" in result
        assert "show_homemanager_option" not in result
        assert "list_homemanager_releases" in result

        # nixvim: excluded by default, but one tool included
        assert "search_nixvim_options" in result
        assert "show_nixvim_option" not in result

    def test_default_excluded_tools_need_explicit_include(self):
        """Default-excluded tools are not included even when their category is enabled."""
        # Enable all categories
        result = resolve_included_tools(dict.fromkeys(TOOL_CATEGORIES, True), set(), set())

        # Default-excluded tools should NOT be included
        for tool in DEFAULT_EXCLUDED_TOOLS:
            assert tool not in result, f"{tool} should be excluded by default"

    def test_default_excluded_tools_can_be_included(self):
        """Default-excluded tools can be included via --include."""
        result = resolve_included_tools({}, {"read_derivation", "read_nixos_module"}, set())

        assert "read_derivation" in result
        assert "read_nixos_module" in result
        # But not other default-excluded tools
        assert "read_home_module" not in result

    def test_all_tools_accounted_for(self):
        """Sanity check: all tools in TOOL_CATEGORIES are considered."""
        all_tools = set()
        for tools in TOOL_CATEGORIES.values():
            all_tools.update(tools)

        # Include everything (categories + explicitly include default-excluded tools)
        result = resolve_included_tools(
            dict.fromkeys(TOOL_CATEGORIES, True),
            DEFAULT_EXCLUDED_TOOLS,  # explicitly include default-excluded tools
            set(),
        )

        assert result == all_tools
