{
  description = "Net worth focused personal finance";

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

  outputs = { self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
        
      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;
        in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [ 
              pyproject-build-systems.overlays.wheel
              overlay
            ]
          )
      );

    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system}.overrideScope editableOverlay;
          virtualenv = pythonSet.mkVirtualEnv "dojo-dev-env" workspace.deps.all;
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              cypress
              duckdb
              nodejs
              mermaid-cli
              python312
              ruff
              uv
            ];

            shellHook = with pkgs; ''
              export UV_PYTHON_DOWNLOADS=never
              export UV_CACHE_DIR="$PWD/.uv-cache"
              export LD_LIBRARY_PATH=${lib.makeLibraryPath [ stdenv.cc.cc.lib zlib ]}:$LD_LIBRARY_PATH
              export CYPRESS_INSTALL_BINARY=0
              export CYPRESS_RUN_BINARY=${pkgs.cypress}/bin/Cypress

              if [ ! -f .venv/bin/activate ] || [ ''${DOJO_FORCE_UV_SYNC:-0} = 1 ]; then
                mkdir -p .uv-cache
                uv sync --extra dev
              fi
              . .venv/bin/activate
            '';
          };

          builder = pkgs.mkShell {
            packages = with pkgs; [
              duckdb
              ruff
              uv
              virtualenv
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              export PYTHONPATH="$REPO_ROOT/src:$PYTHONPATH"
            '';
          };
        }
      );

      packages = forAllSystems (system: {
        default = pythonSets.${system}.mkVirtualEnv "dojo-env" workspace.deps.default;
      });
    };
}
