# A tasteful MCP for Nix*
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Tools

### Enabled by default

* **Nixpkgs** (disable with `--no-packages`)
  * Search Nixpkgs
  * Show Nixpkgs package
* **NixOS** (disable with `--no-options`)
  * Search NixOS options
  * List NixOS channels

### Disabled by default

* **Home Manager** (enabled with `--homemanager`)
  * Search Home Manager options
  * List Home Manager releases



### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
