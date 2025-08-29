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

        # Build Python package from pyproject.toml (example)
        # llacPackage = pkgs.python3Packages.buildPythonPackage {
        #   pname = "LLAC";
        #   version = "0.0.0a";
        #   format = "pyproject";
        #   src = ./Src;
        #   nativeBuildInputs = with pkgs.python3Packages; [ wheel ];
        #   propagatedBuildInputs = with pkgs.python3Packages; [ numpy ];
        #   doCheck = false;
        #   pythonImportsCheck = [ "LLAC" ];
        # };

        # Mainline build selections
        pythonStable = pkgs.python3;
        python314 = pkgs.python314;

        # Opt-in build selections (build w/ max optimizations)
        # allow profile-guided non-repro builds & PGO for CPython
        pythonStableOpt = pythonStable.override {
          enableOptimizations = true;
          enableGIL = false;
          reproducibleBuild = false;
        };

        python314Opt = python314.override {
          enableOptimizations = true;
          # enableGIL = false;
          reproducibleBuild = false;
        };

        # Build a Python env with common dev packages
        # For Python >= 3.14, exclude ipython (traitlets) and matplotlib until
        # upstream gains support in nixpkgs; keep core tooling.
        mkPythonEnv = python: 
              let
                ver = if python ? pythonVersion then python.pythonVersion else "";
                is314plus = pkgs.lib.versionAtLeast ver "3.14";
              in
                python.withPackages (ps:
                  let
                    baseMinimal = with ps; [ virtualenv wheel pip ];
                    baseFull = (with ps; [ virtualenv wheel pip pytest ruff packaging build ]) ++ [ ps."setuptools-scm" ];
                  in
                    if is314plus then baseMinimal
                    else baseFull ++ (with ps; [ ipython (matplotlib.override { enableQt = true; }) ])
                );

        # Libraries we want in LD_LIBRARY_PATH
        ldLibPath = with pkgs; [ zlib libGL glib.out ];

  baseShellHook = ''
          # Determine Python version (major.minor) inside the shell
          PY_MM=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' || echo)

          # Compute project root and current branch if not already exported
          if [ -z "''${ROOT:-}" ]; then
            ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
            export ROOT
          fi

          if [ -z "''${CUR_BRANCH:-}" ]; then
            CUR_BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
            export CUR_BRANCH
          fi

          # Optionally source shared env exports so they're always
          # available inside nix shells without relying on direnv hooks.
          # Create this file with lines like: export FOO=bar
          if [ -f "$ROOT/.env.shared" ]; then
            # shellcheck disable=SC1090
            . "$ROOT/.env.shared"
          fi

          # Helper to install requirements with optional blocklist for latest python builds
          install_requirements() {
            local req_file="$1"
            local blocklist="$ROOT/.nix/python-314-blocklist.txt"
            if [ -f "$req_file" ]; then
              if printf '%s\n%s\n' "$PY_MM" "3.14" | sort -C -V; then
                # PY_MM < 3.14 -> no blocklist
                pip install -r "$req_file" --quiet
              else
                # PY_MM >= 3.14 -> apply blocklist if available
                if [ -f "$blocklist" ]; then
                  tmp_req="$(mktemp)"
                  # Filter out lines that match any blocked package (regex, anchor-friendly)
                  grep -Ev -f "$blocklist" "$req_file" > "$tmp_req" || cp "$req_file" "$tmp_req"
                  echo "Applying Python 3.14+ blocklist from $blocklist for $req_file"
                  echo "Skipped packages (if present):"
                  grep -E -f "$blocklist" "$req_file" || true
                  pip install -r "$tmp_req" --quiet
                  rm -f "$tmp_req"
                else
                  pip install -r "$req_file" --quiet
                fi
              fi
            fi
          }

          export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/
          export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath ldLibPath}:$LD_LIBRARY_PATH"
          export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.libsForQt5.qt5.qtbase.bin}/lib/qt-${pkgs.libsForQt5.qt5.qtbase.version}/plugins";

          # Decide on venv suffix based on optimization flag
          OPT_SUFFIX=""
          if [ "''${PY_IS_OPT:-0}" = "1" ]; then
            OPT_SUFFIX="_opt"
          fi

          case "$CUR_BRANCH" in
            "research") VENV_DIR="$ROOT/docs/Notebook/.venv_''${PY_MM}''${OPT_SUFFIX}";;
            *) VENV_DIR="$ROOT/.venv_''${PY_MM}''${OPT_SUFFIX}";;
          esac

          export VENV_DIR="$VENV_DIR"

          [ ! -d $VENV_DIR ] && {
            echo "Creating Python virtual environment in $VENV_DIR..."
            python3 -m venv $VENV_DIR
          }

          source "$VENV_DIR/bin/activate"

          # ! Anything below this line is run inside the .venv !

          # Install the main project package in editable mode for all branches
          # pip install -e "$ROOT/Src" --quiet

          case "$CUR_BRANCH" in
            "research")
                echo "Installing Python dependencies into the research virtual environment..."
                install_requirements "$ROOT/docs/Notebook/requirements.txt"
                python3 -m ipykernel install --user --name=.venv
                cd "$ROOT/docs/Notebook"
              ;;
            *)
              echo "Installing Python dependencies into the virtual environment..."
              install_requirements "$ROOT/Src/Allocator/requirements.txt"
              install_requirements "$ROOT/Src/Scripts/requirements.txt"
            ;;
          esac

          GIL_ENABLED=$(python3 -c 'import sys; print(sys._is_gil_enabled())')
          echo "LLAC development environment loaded on $CUR_BRANCH branch"
          echo "Python virtual environment activated. Python: $(which python)"
          echo "GIL status: ''${GIL_ENABLED}"
          python3 --version
        '';

  mkLlacShell = python: optimized: pkgs.mkShell {
          buildInputs = with pkgs; [
            (mkPythonEnv python)
            direnv nix-direnv

            # Build tools
            stdenv.cc.cc.lib zlib zlib-ng gcc gnumake pkg-config autoconf automake libtool m4 bison flex

            # Graphics (tested: all of these should be optional)
            glib libGL fontconfig wayland libxkbcommon freetype dbus libsForQt5.wrapQtAppsHook

            # System dependencies
            git curl cacert gnupg coreutils-full ccache perl act docker docker-compose

            # Git dependencies
            pre-commit codespell
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            # macOS specific packages
            pkgs.darwin.apple_sdk.frameworks.CoreServices
            pkgs.darwin.apple_sdk.frameworks.SystemConfiguration
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isLinux [ sudo ];

          # Expose for the shellHook to consume
          inherit ldLibPath;
          shellHook = ''
            export PY_IS_OPT=${if optimized then "1" else "0"}
          '' + baseShellHook;
        };

        # Choose default Python based on env var PYTHON_ENV, falling back to optimized stable
        pyEnv = builtins.getEnv "PYTHON_ENV";
        defaultPython =
          if pyEnv == "python-stable" || pyEnv == "python3-stable" || pyEnv == "stable" then pythonStable
          else if pyEnv == "python-stable-opt" || pyEnv == "python3-stable-opt" || pyEnv == "stable-opt" then pythonStableOpt
          else if pyEnv == "python-314" || pyEnv == "3.14" then python314
          else if pyEnv == "python-314-opt" || pyEnv == "314-opt" then python314Opt
          else pythonStableOpt;

        defaultIsOpt =
          if pyEnv == "python-stable" || pyEnv == "python3-stable" || pyEnv == "stable" then false
          else if pyEnv == "python-stable-opt" || pyEnv == "python3-stable-opt" || pyEnv == "stable-opt" then true
          else if pyEnv == "python-314" || pyEnv == "3.14" then false
          else if pyEnv == "python-314-opt" || pyEnv == "314-opt" then true
          else true;
      in
      {
        # Dev shells: default is stable; expose both cached 3.14 and an "opt" alias
        devShells = {
          # If PYTHON_ENV is set (e.g., by setup.sh), use that to pick default
          default = mkLlacShell defaultPython defaultIsOpt;
          python-stable = mkLlacShell pythonStable false;
          python3-stable = mkLlacShell pythonStable false;
          python-stable-opt = mkLlacShell pythonStableOpt true;
          python3-stable-opt = mkLlacShell pythonStableOpt true;
          python-314 = mkLlacShell python314 false;
          python-314-opt = mkLlacShell python314Opt true;
        };
      }
    );
}
