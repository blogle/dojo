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

      dependencyOverlay = final: prev: {
        multitasking = prev.multitasking.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++ [
            final.setuptools
          ];
        });
        peewee = prev.peewee.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++ [
            final.setuptools
          ];
        });
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
              dependencyOverlay
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
              biome
              actionlint
              cypress
              duckdb
              nodejs_20
              mermaid-cli
              python312
              ruff
              sqlfluff
              uv
            ];

            shellHook = with pkgs; ''
              export UV_PYTHON_DOWNLOADS=never
              export UV_CACHE_DIR="$PWD/.uv-cache"
              export LD_LIBRARY_PATH=${lib.makeLibraryPath [ stdenv.cc.cc.lib zlib ]}:$LD_LIBRARY_PATH
               export CYPRESS_INSTALL_BINARY=0
               export CYPRESS_RUN_BINARY=${pkgs.cypress}/bin/Cypress
               export PATH="$PWD/scripts:$PATH"
               export DOJO_RUN_STARTUP_MIGRATIONS=true

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

      packages = forAllSystems (system: 
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system};
          app-env = pythonSet.mkVirtualEnv "dojo-env" workspace.deps.default;
          frontendDist = pkgs.buildNpmPackage {
            pname = "dojo-frontend";
            version = "0.0.0";
            src = ./src/dojo/frontend/vite;
            npmDepsHash = "sha256-+TocTOZG0/j+rZQa4Cx1cGbzjDEztc96V0zP933e9Yo=";
            nodejs = pkgs.nodejs_20;
            npmBuild = "npm run build";
            installPhase = ''
              mkdir -p $out/dist
              cp -r dist/. $out/dist
            '';
          };
        in {
          default = app-env;
          frontend = frontendDist;
          
          docker = pkgs.dockerTools.buildLayeredImage {
          name = "dojo";
          tag = "latest";
          contents = [ 
            app-env 
            pkgs.busybox 
          ];
          config = {
            Cmd = [ "python" "-m" "uvicorn" "dojo.core.app:create_app" "--factory" "--host" "0.0.0.0" "--port" "8000" ];
            Env = [
              "DOJO_DB_PATH=/data/ledger.duckdb"
              "DOJO_ENV=production"
            ];
            ExposedPorts = {
              "8000/tcp" = {};
            };
            User = "1000";
            WorkingDir = "/app";
          };
        };
      });
    };
}
