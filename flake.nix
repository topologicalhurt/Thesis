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
            pythonEnv

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
            pre-commit
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
          ];

          shellHook = ''
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath ldLibPath}:$LD_LIBRARY_PATH"

            export PYTHONDONTWRITEBYTECODE=1
            export PYTHONUNBUFFERED=1
            VENV_DIR=".venv"

            # Create a virtual environment if it doesn't exist
            if [ ! -d "$VENV_DIR" ]; then
              echo "Creating Python virtual environment in $VENV_DIR..."
              ${pythonEnv}/bin/python -m venv $VENV_DIR
            fi

            # Activate the virtual environment
            source "$VENV_DIR/bin/activate"

            # Install dependencies from requirements.txt files
            echo "Installing Python dependencies into the virtual environment..."
            pip install -r Src/Allocator/requirements.txt
            pip install -r Src/Scripts/requirements.txt

            # Install the main project package in editable mode
            pip install -e ./Src

            echo "LLAC development environment loaded"
            echo "Python virtual environment activated. Python: $(which python)"
            python3 --version
          '';
        };
      });
}
