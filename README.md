# A tasteful MCP server for the Nix ecosystem
[![Tests](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml/badge.svg)](https://github.com/felixdorn/mcp-nix/actions/workflows/test.yml)

## Installation

Use the following configuration to add the MCP server to your client:

**Using uvx:**

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

**Using nix run:**

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

**Declaratively:**

Add the flake input:

```nix
{
  inputs.mcp-nix.url = "github:felixdorn/mcp-nix";
}
```

Then reference the package:

```nix
{
  command = "${inputs.mcp-nix.packages.${system}.default}/bin/mcp-nix";
}
```



## Tools

| Tool | Description |
|------|-------------|
| `search_nixpkgs` | Search Nixpkgs packages |
| `read_derivation` | Read package source code |
| `search_options` | Search options for many projects |
| `list_versions` | List available versions for a project |
| `show_option_details` | Get option details or list children |
| `read_option_declaration` | Read option source code |
| `find_nixpkgs_commit_with_package_version` | Get nixpkgs commit for a version, shows available versions if not found (NixHub) |
| `search_nix_stdlib` | Search Nix stdlib functions (Noogle) |
| `help_for_stdlib_function` | Get help for a stdlib function (Noogle) |

### Supported Projects for Options

| Project | Versions |
|---------|----------|
| `nixos` | unstable, 24.11, 25.05, etc. |
| `homemanager` | unstable, 24.11, 25.05, etc. |
| `nixvim` | latest only |
| `nix-darwin` | latest only |
| `impermanence` | latest only |
| `microvm` | latest only |
| `nix-nomad` | latest only (no source reading) |
| `simple-nixos-mailserver` | latest only |
| `sops-nix` | latest only |
| `nixos-hardware` | latest only |
| `disko` | latest only |

### Excluding Tools

Use `--exclude` to disable specific tools:

```json
{
  "mcpServers": {
    "nix": {
      "command": "uvx",
      "args": ["mcp-nix", "--exclude=read_derivation,read_option_declaration"]
    }
  }
}
```

### Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md)

### Acknowledgments
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com), [NüschtOS](https://github.com/NuschtOS/search), [nix-nomad](https://github.com/tristanpemble/nix-nomad), [NixHub](https://nixhub.io), [Noogle](https://noogle.dev) for maintaining the backends and pipeline this server uses and for the Nix community for making any of this possible.

### License
GPLv3: [License](LICENSE)

<!-- mcp-name: io.github.felixdorn/mcp-nix -->
