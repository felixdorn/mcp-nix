# A tasteful MCP server for the Nix ecosystem
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Upcoming
* Read declaration/derivation file.

## Tools

### Included by default

* **Nixpkgs** `nixpkgs`
  * Search Nixpkgs
  * Show Nixpkgs package
* **NixOS** `nixos`
  * Search NixOS options
  * List NixOS channels

### Excluded by default

* **Home Manager** `homemanager`
  * Search Home Manager options
  * List Home Manager releases
* **Nixvim** `nixvim`
  * Search and show Nixvim options
* **nix-darwin** `nix-darwin`
  * Search and show nix-darwin options
* **NixHub** `nixhub`
  * List package versions
  * Find the nixpkgs commit where a version of a package exists

### Including tools

* **Categories**
  * You can include groups of tools such as `uvx mcp-nix --homemanager --nixvim`
* **Individual tools**
  * `uvx mcp-nix --include=list_package_versions`

You can find the group names and the tool names in the [reference](#reference).

### Excluding tools

Excluding tools you don't use reduces context usage and reduces the chance that the model picks the wrong tool.

* **Categories**
  * You can include groups of tools such as `uvx mcp-nix --no-nixos --nix-darwin`
* **Individual tools**
  * `uvx mcp-nix --exclude=find_nixpkgs_commit_with_package_version`

You can find the group names and the tool names in the [reference](#reference).

### Reference

#### Categories

| Category | Included by default | Flag |
|----------|:--------:|------|
| `nixpkgs` | Yes | `--nixpkgs` / `--no-nixpkgs` |
| `nixos` | Yes | `--nixos` / `--no-nixos` |
| `homemanager` | | `--homemanager` / `--no-homemanager` |
| `nixvim` | | `--nixvim` / `--no-nixvim` |
| `nix-darwin` | | `--nix-darwin` / `--no-nix-darwin` |
| `nixhub` | | `--nixhub` / `--no-nixhub` |

#### Individual tools
| Tool | Included by default | Description |
|------|:-------:|-------------|
| **nixpkgs** | | |
| `search_nixpkgs` | Yes | Search for Nixpkgs packages by name or description |
| `show_nixpkgs_package` | Yes | Get details for a Nixpkgs package by exact name |
| **nixos** | | |
| `search_nixos_options` | Yes | Search NixOS configuration options |
| `show_nixos_option` | Yes | Get details for a NixOS option, or list children if given a prefix |
| `list_nixos_channels` | Yes | List available NixOS release channels |
| **homemanager** | | |
| `search_homemanager_options` |  | Search Home Manager options for user environment configuration |
| `show_homemanager_option` |  | Get details for a Home Manager option, or list children if given a prefix |
| `list_homemanager_releases` |  | List available Home Manager releases |
| **nixvim** | | |
| `search_nixvim_options` |  | Search NixVim configuration options |
| `show_nixvim_option` |  | Get details for a NixVim option, or list children if given a prefix |
| **nix-darwin** | | |
| `search_nix_darwin_options` |  | Search nix-darwin configuration options for macOS |
| `show_nix_darwin_option` |  | Get details for a nix-darwin option, or list children if given a prefix |
| **nixhub** | | |
| `list_package_versions` |  | List all available versions for a Nixpkgs package |
| `find_nixpkgs_commit_with_package_version` |  | Get the nixpkgs commit hash for a specific package version |

### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NuschtOS](https://github.com/NuschtOS/search), [NixHub](https://nixhub.io) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
