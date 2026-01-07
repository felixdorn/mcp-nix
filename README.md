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
- nix-nomad
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
| **nix-nomad** | `nix-nomad` | `search_nix_nomad_options`, `show_nix_nomad_option` |
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

### Tool Reference

See [docs/REFERENCE.md](docs/REFERENCE.md) for a complete list of tools with descriptions.

### Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md)

### Acknowledgments
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NüschtOS](https://github.com/NuschtOS/search), [nix-nomad](https://github.com/tristanpemble/nix-nomad), [NixHub](https://nixhub.io), [Noogle](https://noogle.dev) for maintaining the backends and pipeline this server uses and for the Nix community for making any of this possible.

### License
GPLv3: [License](LICENSE)

<!-- mcp-name: io.github.felixdorn/mcp-nix -->
