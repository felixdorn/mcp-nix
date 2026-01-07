# Tool Reference

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
| **nix-nomad** | |
| `search_nix_nomad_options` | Search nix-nomad configuration options for Nomad job specs |
| `show_nix_nomad_option` | Get details for a nix-nomad option, or list children if given a prefix |
| **nixhub** | |
| `list_package_versions` | List all available versions for a Nixpkgs package |
| `find_nixpkgs_commit_with_package_version` | Get the nixpkgs commit hash for a specific package version |
| **noogle** | |
| `search_nix_stdlib` | Search Nix standard library functions by name or type signature |
| `help_for_stdlib_function` | Get detailed help for a Nix standard library function |

[^a]: Requires explicit `--include` even when the category is enabled.
