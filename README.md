# A tasteful MCP server for the Nix ecosystem
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Upcoming
* Read declaration/derivation file.

## Tools

### Included by default

| Category | ID | Usage |
|----------|-----|-------------|
| **Nixpkgs** | `nixpkgs` | Search and show Nixpkgs packages |
| **NixOS** | `nixos` | Search NixOS options and list channels |

### Excluded by default

| Category | ID | Usage |
|----------|-----|-------------|
| **Home Manager** | `homemanager` | Search Home Manager options and list releases |
| **Nixvim** | `nixvim` | Search and show Nixvim options |
| **nix-darwin** | `nix-darwin` | Search and show nix-darwin options |
| **NixHub** | `nixhub` | Find the nixpkgs commit where a version of a package exists |

### Including tools

* **By category**
  * Pass the category's ID as an argument: `--homemanager --nixvim`
* **By name**
  * Use --include: `--include=list_package_versions`

### Excluding tools

* **By category**
  * Prefix the category's ID by "no-": `--no-nixos`
* **By name**
  * Use --exclude: `--exclude=find_nixpkgs_commit_with_package_version`

### List of tools

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
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NuschtOS](https://github.com/NuschtOS/search), [NixHub](https://nixhub.io) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
