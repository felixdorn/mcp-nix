# A tasteful MCP for Nix*
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Upcoming
* Support for searching version from NixHub
* Read declaration/derivation file.

## Tools

### Enabled by default

* **Nixpkgs** (disable with `--no-packages`)
  * Search Nixpkgs
  * Show Nixpkgs package
* **NixOS** (disable with `--no-options`)
  * Search NixOS options
  * List NixOS channels

### Disabled by default

* **Home Manager** (enable with `--homemanager`)
  * Search Home Manager options
  * List Home Manager releases
* **Nixvim** (enable with `--nixvim`)
  * Search and show Nixvim options
* **nix-darwin** (enable with `--nix-darwin`)
  * Search and show nix-darwin options

### Excluding tools

Exclude specific tools using the `--exclude` flag, for example:
```bash
uvx run mcp-nix --homemanager --exclude=list_homemanager_releases
```

Find the tools names in the [reference](#reference).

### Reference

| Tool | Enabled by default | Description |
|------|:-------:|-------------|
| **packages** | | |
| `search_nixpkgs` | ✓ | Search for Nixpkgs packages by name or description |
| `show_nixpkgs_package` | ✓ | Get details for a Nixpkgs package by exact name |
| **options** | | |
| `search_nixos_options` | ✓ | Search NixOS configuration options |
| `show_nixos_option` | ✓ | Get details for a NixOS option, or list children if given a prefix |
| `list_nixos_channels` | ✓ | List available NixOS release channels |
| **homemanager** | | |
| `search_homemanager_options` | ✗ | Search Home Manager options for user environment configuration |
| `show_homemanager_option` | ✗ | Get details for a Home Manager option, or list children if given a prefix |
| `list_homemanager_releases` | ✗ | List available Home Manager releases |
| **nixvim** | | |
| `search_nixvim_options` | ✗ | Search NixVim configuration options |
| `show_nixvim_option` | ✗ | Get details for a NixVim option, or list children if given a prefix |
| **nix-darwin** | | |
| `search_nix_darwin_options` | ✗ | Search nix-darwin configuration options for macOS |
| `show_nix_darwin_option` | ✗ | Get details for a nix-darwin option, or list children if given a prefix |

### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NuschtOS](https://github.com/NuschtOS/search) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
