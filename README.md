# A tasteful MCP server for the Nix ecosystem
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Upcoming
* Read declaration/derivation file.

## Tool categories

### Included by default

| Category | ID | Tools |
|----------|-----|-------|
| **Nixpkgs** | `nixpkgs` | `search_nixpkgs`, `show_nixpkgs_package` |
| **NixOS** | `nixos` | `search_nixos_options`, `show_nixos_option`, `list_nixos_channels` |

### Excluded by default

| Category | ID | Tools |
|----------|-----|-------|
| **Home Manager** | `homemanager` | `search_homemanager_options`, `show_homemanager_option`, `list_homemanager_releases` |
| **Nixvim** | `nixvim` | `search_nixvim_options`, `show_nixvim_option` |
| **nix-darwin** | `nix-darwin` | `search_nix_darwin_options`, `show_nix_darwin_option` |
| **NixHub** | `nixhub` | `list_package_versions`, `find_nixpkgs_commit_with_package_version` |

### Including tools

* **By category**
  * Pass the category's ID as an argument: `--homemanager --nixvim`
* **By name**
  * Use --include: `--include=list_package_versions,...`

### Excluding tools

* **By category**
  * Prefix the category's ID by "no-": `--no-nixos`
* **By name**
  * Use --exclude: `--exclude=find_nixpkgs_commit_with_package_version,...`

## List of tools

| Tool | Usage |
|------|-------------|
| **nixpkgs** | |
| `search_nixpkgs` | Search for Nixpkgs packages by name or description |
| `show_nixpkgs_package` | Get details for a Nixpkgs package by exact name |
| **nixos** | |
| `search_nixos_options` | Search NixOS configuration options |
| `show_nixos_option` | Get details for a NixOS option, or list children if given a prefix |
| `list_nixos_channels` | List available NixOS release channels |
| **homemanager** | |
| `search_homemanager_options` | Search Home Manager options for user environment configuration |
| `show_homemanager_option` | Get details for a Home Manager option, or list children if given a prefix |
| `list_homemanager_releases` | List available Home Manager releases |
| **nixvim** | |
| `search_nixvim_options` | Search NixVim configuration options |
| `show_nixvim_option` | Get details for a NixVim option, or list children if given a prefix |
| **nix-darwin** | |
| `search_nix_darwin_options` | Search nix-darwin configuration options for macOS |
| `show_nix_darwin_option` | Get details for a nix-darwin option, or list children if given a prefix |
| **nixhub** | |
| `list_package_versions` | List all available versions for a Nixpkgs package |
| `find_nixpkgs_commit_with_package_version` | Get the nixpkgs commit hash for a specific package version |

### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NüschtOS](https://github.com/NuschtOS/search), [NixHub](https://nixhub.io) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
