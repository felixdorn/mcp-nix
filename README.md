# A tasteful MCP server for the Nix ecosystem
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Ecosystem coverage

- Nixpkgs
- NixOS
- Home Manager
- Nixvim
- nix-darwin
- impermanence
- MicroVM.nix
- NixHub
- Noogle 

> Without additional configuration, only **Nixpkgs** and **NixOS** categories are included.



## Installation

Use the following configuration to add the MCP server to your client:

```json
{
  "mcpServers": {
    "nix": {
      "command": "uvx",
      "args": ["mcp-nix"]
    }
  }
}
```

### Using Nix

```json
{
  "mcpServers": {
    "nix": {
      "command": "nix",
      "args": ["run", "github:felixdorn/mcp-nix"]
    }
  }
}
```

## Tools

* **Categories included by default:**

| Category | ID | Tools |
|----------|-----|-------|
| **Nixpkgs** | `nixpkgs` | `search_nixpkgs`, `show_nixpkgs_package`, `read_derivation`[^a] |
| **NixOS** | `nixos` | `search_nixos_options`, `show_nixos_option`, `list_nixos_channels`, `read_nixos_module`[^a] |

* **Categories excluded by default**

| Category | ID | Tools |
|----------|-----|-------|
| **Home Manager** | `homemanager` | `search_homemanager_options`, `show_homemanager_option`, `list_homemanager_releases`, `read_home_module`[^a] |
| **Nixvim** | `nixvim` | `search_nixvim_options`, `show_nixvim_option`, `read_nixvim_declaration`[^a] |
| **nix-darwin** | `nix-darwin` | `search_nix_darwin_options`, `show_nix_darwin_option`, `read_nix_darwin_declaration`[^a] |
| **impermanence** | `impermanence` | `search_impermanence_options`, `show_impermanence_option`, `read_impermanence_declaration`[^a] |
| **MicroVM.nix** | `microvm` | `search_microvm_options`, `show_microvm_option`, `read_microvm_declaration`[^a] |
| **NixHub** | `nixhub` | `list_package_versions`, `find_nixpkgs_commit_with_package_version` |
| **Noogle** | `noogle` | `search_nix_stdlib`, `help_for_stdlib_function` |

[^a]: Requires explicit `--include` even when the category is enabled.

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

### List of tools

| Tool | Usage |
|------|-------------|
| **nixpkgs** | |
| `search_nixpkgs` | Search for Nixpkgs packages by name or description |
| `show_nixpkgs_package` | Get details for a Nixpkgs package by exact name |
| `read_derivation`[^a] | Read the Nix source code for a package derivation |
| **nixos** | |
| `search_nixos_options` | Search NixOS configuration options |
| `show_nixos_option` | Get details for a NixOS option, or list children if given a prefix |
| `list_nixos_channels` | List available NixOS release channels |
| `read_nixos_module`[^a] | Read the Nix source code for a NixOS option declaration |
| **homemanager** | |
| `search_homemanager_options` | Search Home Manager options for user environment configuration |
| `show_homemanager_option` | Get details for a Home Manager option, or list children if given a prefix |
| `list_homemanager_releases` | List available Home Manager releases |
| `read_home_module`[^a] | Read the Nix source code for a Home Manager option declaration |
| **nixvim** | |
| `search_nixvim_options` | Search NixVim configuration options |
| `show_nixvim_option` | Get details for a NixVim option, or list children if given a prefix |
| `read_nixvim_declaration`[^a] | Get the declaration reference for a NixVim option |
| **nix-darwin** | |
| `search_nix_darwin_options` | Search nix-darwin configuration options for macOS |
| `show_nix_darwin_option` | Get details for a nix-darwin option, or list children if given a prefix |
| `read_nix_darwin_declaration`[^a] | Get the declaration reference for a nix-darwin option |
| **impermanence** | |
| `search_impermanence_options` | Search impermanence configuration options |
| `show_impermanence_option` | Get details for an impermanence option, or list children if given a prefix |
| `read_impermanence_declaration`[^a] | Read the Nix source code for an impermanence option declaration |
| **microvm** | |
| `search_microvm_options` | Search MicroVM.nix configuration options |
| `show_microvm_option` | Get details for a MicroVM.nix option, or list children if given a prefix |
| `read_microvm_declaration`[^a] | Read the Nix source code for a MicroVM.nix option declaration |
| **nixhub** | |
| `list_package_versions` | List all available versions for a Nixpkgs package |
| `find_nixpkgs_commit_with_package_version` | Get the nixpkgs commit hash for a specific package version |
| **noogle** | |
| `search_nix_stdlib` | Search Nix standard library functions by name or type signature |
| `help_for_stdlib_function` | Get detailed help for a Nix standard library function |
[^a]: Requires explicit `--include` even when the category is enabled.

### Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md)

### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NüschtOS](https://github.com/NuschtOS/search), [NixHub](https://nixhub.io), [Noogle](https://noogle.dev) for maintaining the backends and pipeline this server uses and for the Nix community for making any of this possible.

### License
GPLv3: [License](LICENSE)

<!-- mcp-name: io.github.felixdorn/mcp-nix -->
