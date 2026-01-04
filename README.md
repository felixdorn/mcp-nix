# A tasteful MCP for Nix*
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)


## Upcoming
* Support for searching nixvim options
* Support for searching nix-darwin options
* Support for searching version from NixHub
* Read declaration/derivation file.
* Add granular filtering --exclude=[tool_name,..]

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
  * Search Nixvim options
  * Show Nixvim option



### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NuschtOS](https://github.com/NuschtOS/search) for maintaining the backends and pipeline the tool uses and for the Nix community for making any of this possible.
