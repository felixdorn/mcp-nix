{
  description = "MCP server for Nixpkgs, NixOS and Home Manager";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;

      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems = lib.genAttrs systems;

      # Load uv workspace
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      # Create overlay from workspace
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      pkgsFor = forAllSystems (system: nixpkgs.legacyPackages.${system});

      # Build python package sets for each system
      pythonSetFor = forAllSystems (
        system:
        let
          pkgs = pkgsFor.${system};
          python = pkgs.python313;

          # Base python set with pyproject.nix builders
          pythonBase = pkgs.callPackage pyproject-nix.build.packages { inherit python; };

          # Custom overlay for pyixx (maturin/Rust build)
          pyixxOverlay = final: prev: {
            pyixx = prev.pyixx.overrideAttrs (old: {
              nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
                pkgs.rustPlatform.cargoSetupHook
                pkgs.rustPlatform.maturinBuildHook
                pkgs.cargo
                pkgs.rustc
              ];

              cargoDeps = pkgs.rustPlatform.importCargoLock {
                lockFile = ./pyixx/Cargo.lock;
                outputHashes = {
                  "libixx-0.0.0-git" = "sha256-NNf3vnTI9j+Zjliy/oQrrhQ1meyXt2I05aXjDE3VfJ0=";
                };
              };
            });
          };
        in
        pythonBase.overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyixxOverlay
          ]
        )
      );
    in
    {
      packages = forAllSystems (
        system:
        let
          pythonSet = pythonSetFor.${system};
        in
        {
          default = pythonSet.mkVirtualEnv "mcp-nix" workspace.deps.default;
        }
      );

      checks = forAllSystems (system: {
        startup = pkgsFor.${system}.runCommand "mcp-nix-startup" { } ''
          export XDG_CACHE_HOME="$TMPDIR/cache"
          ${self.packages.${system}.default}/bin/python -c 'from mcp_nix import tools'
          touch "$out"
        '';
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor.${system};
          pythonSet = pythonSetFor.${system};

          # Editable overlay for development
          editableOverlay = workspace.mkEditablePyprojectOverlay {
            root = "$REPO_ROOT";
          };

          editablePythonSet = pythonSet.overrideScope editableOverlay;
          virtualenv = editablePythonSet.mkVirtualEnv "mcp-nix-dev" workspace.deps.default;
        in
        {
          default = pkgs.mkShell {
            packages = [
              virtualenv
              pkgs.uv
            ];

            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = editablePythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };

            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };
        }
      );
    };
}
