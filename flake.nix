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
        llacPackage = pkgs.python311.pkgs.buildPythonPackage {
          pname = "LLAC";
          version = "0.0.0a";
          format = "pyproject";

          src = ./Src;

          nativeBuildInputs = with pkgs.python311.pkgs; [
            setuptools
            wheel
          ];

          # Add runtime dependencies here if needed
          propagatedBuildInputs = with pkgs.python311.pkgs; [
            # e.g., numpy, pandas, etc.
          ];

          # Disable tests during build
          doCheck = false;

          pythonImportsCheck = [ "LLAC" ];
        };

        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          # Development dependencies
          setuptools
          wheel
          pip
          pytest
          ipython
        ]);

      in
      {
        # The package itself
        packages.default = llacPackage;

        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv

            # Build tools
            stdenv.cc.cc.lib
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

          shellHook = ''
            export PYTHONDONTWRITEBYTECODE=1
            export PYTHONUNBUFFERED=1

            cd "$PWD"
            ${pythonEnv}/bin/pip install -e ./Src 2>/dev/null || true

            echo "LLAC development environment loaded"
            echo "Python: ${pythonEnv}/bin/python"
          '';
        };
      });
}
