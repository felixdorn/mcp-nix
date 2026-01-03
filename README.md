# MCP for Nix*

## Tools

### Nixpkgs

* `nixos_search_package`
* `nixos_get_package_details`

Disable with `--no-packages`

### Nixos

Disable with `--no-options`.

* `nixos_search_option`
* `nixos_get_option_detail`

### Homemanager (off by default)

Enable with `--homemanager`

* `homemanager_search_option`
* `homemanager_get_option_details`
* `homemanager_releases`


### Credits
Thanks to the [NixOS Search Team](https://search.nixos.org), [ExtraNix](https://extranix.com) for maintaining the backends and pipeline the tool uses and for the Nix community for making all of this possible.


### License
MIT.
