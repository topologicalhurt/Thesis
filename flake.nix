{
  description = "A development environment for the LLAC project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [
      "aarch64-darwin"
      "aarch64-linux"
      "x86_64-darwin"
      "x86_64-linux"
    ] (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Build Python package from pyproject.toml
        # llacPackage = pkgs.python313.pkgs.buildPythonPackage {
        #   pname = "LLAC";
        #   version = "0.0.0a";
        #   format = "pyproject";
        #
        #   src = ./Src;
        #
        #   nativeBuildInputs = with pkgs.python313.pkgs; [
        #     setuptools
        #     wheel
        #   ];
        #
        #   # Add runtime dependencies here if needed
        #   propagatedBuildInputs = with pkgs.python313.pkgs; [
        #     # e.g., numpy, pandas, etc.
        #   ];
        #
        #   # Disable tests during build
        #   doCheck = false;
        #
        #   pythonImportsCheck = [ "LLAC" ];
        # };

        pythonEnv = pkgs.python313.withPackages (ps: with ps; [
          # Development dependencies
          virtualenv
          setuptools
          wheel
          pip
          pytest
          ipython
          ruff
        ]);

      in
      {
        # The package itself
        # packages.default = llacPackage;

        # Development shell
        devShells.default = pkgs.mkShell rec {
          buildInputs = with pkgs; [
            # Dev
            pythonEnv

            (python313Packages.matplotlib.override {
              enableQt = true;
            })

            # Build tools
            stdenv.cc.cc.lib
            zlib
            zlib-ng
            gcc
            gnumake
            pkg-config
            autoconf
            automake
            libtool
            m4
            bison
            flex

            # Graphics (tested: all of these should be optional)
            glib
            libGL
            fontconfig
            wayland
            libxkbcommon
            freetype
            dbus
            libsForQt5.wrapQtAppsHook

            # System dependencies
            git
            curl
            cacert
            gnupg
            coreutils-full
            ccache
            perl
            act
            docker
            docker-compose

            # Git dependencies
            pre-commit
            codespell

          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            # macOS specific packages
            darwin.apple_sdk.frameworks.CoreServices
            darwin.apple_sdk.frameworks.SystemConfiguration
          ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            # Linux specific packages
            sudo
          ];

          # Specify dependencies that need to be on LD_LIBRARY_PATH
          ldLibPath = with pkgs; [
            zlib
            libGL
            glib.out
          ];

          shellHook = ''
            export PYTHONPATH=${builtins.toString ./.}:$PYTHONPATH
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath ldLibPath}:$LD_LIBRARY_PATH"

            export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.libsForQt5.qt5.qtbase.bin}/lib/qt-${pkgs.libsForQt5.qt5.qtbase.version}/plugins";

            export PYTHONDONTWRITEBYTECODE=1
            export PYTHONUNBUFFERED=1

            export ROOT="$(git rev-parse --show-toplevel)"
            export CUR_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

            case "$CUR_BRANCH" in
              "research") VENV_DIR="$ROOT/docs/Notebook/.venv";;
              *) VENV_DIR="$ROOT/.venv";;
            esac

            export VENV_DIR="$VENV_DIR"

            [ ! -d $VENV_DIR ] && {
              echo "Creating Python virtual environment in $VENV_DIR..."
              python3 -m venv $VENV_DIR
            }

            source "$VENV_DIR/bin/activate"

            # Install the main project package in editable mode for all branches
            pip install -e "$ROOT/Src" --quiet

            case "$CUR_BRANCH" in
              "research")
                  echo "Installing Python dependencies into the research virtual environment..."
                  pip install -r "$ROOT/docs/Notebook/requirements.txt" --quiet
                  python3 -m ipykernel install --user --name=.venv
                  cd "$ROOT/docs/Notebook"
                ;;
              *)
                echo "Installing Python dependencies into the virtual environment..."
                pip install -r "$ROOT/Src/Allocator/requirements.txt" --quiet
                pip install -r "$ROOT/Src/Scripts/requirements.txt" --quiet
              ;;
            esac

            echo "LLAC development environment loaded on $CUR_BRANCH branch"
            echo "Python virtual environment activated. Python: $(which python)"
            python3 --version
          '';
        };
    });
}
