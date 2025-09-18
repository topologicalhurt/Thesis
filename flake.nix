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

        # Passthrough's from HOST env
        fastBuildDefault = builtins.getEnv "FAST_BUILD" == "1";
        fastBuildDefaultStr = if fastBuildDefault then "1" else "0";

        llacPackage = if (!fastBuildDefault) then
          pkgs.python3Packages.buildPythonPackage {
            pname = "LLAC";
            version = "0.0.0a";
            format = "pyproject";
            src = ./Src;
            nativeBuildInputs = with pkgs.python3Packages; [ wheel ];
            propagatedBuildInputs = with pkgs.python3Packages; [ numpy ];
            doCheck = true;
            pythonImportsCheck = [ "Allocator" "Src" "Scripts" ];
          }
        else null;

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
          enableGIL = false;
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
                    baseFull = (with ps; [ virtualenv wheel pip pytest ruff packaging build poetry-core ]) ++ [ ps."setuptools-scm" ];
                  in
                    if is314plus then baseMinimal
                    else baseFull ++ (with ps; [ ipython (matplotlib.override { enableQt = true; }) ])
                );

        # Libraries we want in LD_LIBRARY_PATH
        ldLibPath = with pkgs; [ zlib libGL glib.out ];

  baseShellHook = ''
          [[ -v WAS_IN_NIX_SHELL ]] && {
            echo -e "\033[31mYou're already in a Nix shell! Do 'exit' to leave & re-activate the environment.\033[0m"
            exit 1
          }

          # Load project environment
          # Don't overwrite env passthroughs from host
          fast_build_tmp="''${FAST_BUILD:-${fastBuildDefaultStr}}"

          [[ -f "./.env.shared" ]] && {
            . "./.env.shared"
          }

          export FAST_BUILD="$fast_build_tmp"

          [[ -v ROOT ]] || {
            echo -e "\033[31mERROR: ROOT environment variable is not set. Ensure .env.shared is present.\033[0m"
            return 1
          }

          export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/
          export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath ldLibPath}:$LD_LIBRARY_PATH"
          export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.libsForQt5.qt5.qtbase.bin}/lib/qt-${pkgs.libsForQt5.qt5.qtbase.version}/plugins";

          export PATH="$VERILATOR_PREFIX/bin:$PATH"
          export PATH="$RISCV_INSTALL_PREFIX/bin:$PATH"

          export WAS_IN_NIX_SHELL="1"

          # Determine Python version (major.minor) inside the shell
          PY_MM=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' || echo)

          # Helper to install requirements with optional blocklist for latest python builds
          install_requirements() {
            local req_file="$1"
            local blocklist="$ROOT/.nix/python-314-blocklist.txt"
            if [ -f "$req_file" ]; then
              if printf '%s\n%s\n' "$PY_MM" "3.14" | sort -C -V; then
                # PY_MM < 3.14 -> no blocklist
                pip install -r "$req_file" | show_last_line_inplace "[pip - venv] "
              else
                # PY_MM >= 3.14 -> apply blocklist if available
                if [ -f "$blocklist" ]; then
                  tmp_req="$(mktemp)"
                  # Filter out lines that match any blocked package (regex, anchor-friendly)
                  grep -Ev -f "$blocklist" "$req_file" > "$tmp_req" || cp "$req_file" "$tmp_req"
                  echo "Applying Python 3.14+ blocklist from $blocklist for $req_file"
                  echo "Skipped packages (if present):"
                  grep -E -f "$blocklist" "$req_file" || true
                  pip install -r "$tmp_req" | show_last_line_inplace "[pip - venv] "
                  rm -f "$tmp_req"
                else
                  pip install -r "$req_file" | show_last_line_inplace "[pip - venv] "
                fi
              fi
            fi
          }

          # Specify library prefixes for GMP/MPFR/MPC via pkg-config
          # These are needed to build riscv-gnu-toolchain from source
          GMP_PREFIX=$(pkg-config --variable=prefix gmp 2>/dev/null || true)
          MPFR_PREFIX=$(pkg-config --variable=prefix mpfr 2>/dev/null || true)
          MPC_PREFIX=$(pkg-config --variable=prefix mpc 2>/dev/null || pkg-config \
          --variable=prefix libmpc 2>/dev/null || true)

          # Pass these prefixes to riscv-gnu-toolchain's configure script
          # Commented out for now since it seems to find them automatically
          # CONFIG_EXTRA=""
          # [ -n "$GMP_PREFIX" ] && CONFIG_EXTRA="$CONFIG_EXTRA --with-gmp=$GMP_PREFIX"
          # [ -n "$MPFR_PREFIX" ] && CONFIG_EXTRA="$CONFIG_EXTRA --with-mpfr=$MPFR_PREFIX"
          # [ -n "$MPC_PREFIX" ] && CONFIG_EXTRA="$CONFIG_EXTRA --with-mpc=$MPC_PREFIX"
          # export CONFIG_EXTRA

          # # Help the build system find headers/libs when prefixes are non-standard
          # CPATH_PREFIX=""
          # [ -n "$GMP_PREFIX" ] && CPATH_PREFIX="$CPATH_PREFIX$GMP_PREFIX/include:"
          # [ -n "$MPFR_PREFIX" ] && CPATH_PREFIX="$CPATH_PREFIX$MPFR_PREFIX/include:"
          # [ -n "$MPC_PREFIX" ] && CPATH_PREFIX="$CPATH_PREFIX$MPC_PREFIX/include:"
          # if [ -n "$CPATH" ]; then
          #   export CPATH="$CPATH_PREFIX$CPATH"
          # else
          #   export CPATH="$CPATH_PREFIX"
          # fi

          # LIBRARY_PATH_PREFIX=""
          # [ -n "$GMP_PREFIX" ] && LIBRARY_PATH_PREFIX="$LIBRARY_PATH_PREFIX$GMP_PREFIX/lib:"
          # [ -n "$MPFR_PREFIX" ] && LIBRARY_PATH_PREFIX="$LIBRARY_PATH_PREFIX$MPFR_PREFIX/lib:"
          # [ -n "$MPC_PREFIX" ] && LIBRARY_PATH_PREFIX="$LIBRARY_PATH_PREFIX$MPC_PREFIX/lib:"
          # if [ -n "$LIBRARY_PATH" ]; then
          #   export LIBRARY_PATH="$LIBRARY_PATH_PREFIX$LIBRARY_PATH"
          # else
          #   export LIBRARY_PATH="$LIBRARY_PATH_PREFIX"
          # fi

          if [ "''${FAST_BUILD}" != "1" ]; then
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
            VENV_CNFG="$VENV_DIR/pyvenv.cfg"
            upgrade_venv=0
            [ -f "$VENV_CNFG" ] && {
              venv_version=$(awk -F'= *' '/^version/{print $2}' "$VENV_CNFG" | tr -d '[:space:]')
              cur_version=$(python3 -V 2>&1 | awk '{print $2}')
              [[ -n "$venv_version" && -n "$cur_version" && "$venv_version" != "$cur_version" ]] && {
                echo "Python version mismatch in existing venv ($venv_version != $cur_version); upgrading $VENV_DIR..."
                python3 -m venv --upgrade "$VENV_DIR"
                echo -e "\033[32mSuccessfully upgraded venv to Python $cur_version!\033[0m"
              }
            }

            # Make project sources importable without installation
            if [ -d "$ROOT/Src" ]; then
              if [ -n "${PYTHONPATH:-}" ]; then
                export PYTHONPATH="$ROOT/Src:$PYTHONPATH"
              else
                export PYTHONPATH="$ROOT/Src"
              fi
            fi

            [ ! -d $VENV_DIR ] && {
              echo "Creating Python virtual environment in $VENV_DIR..."
              python3 -m venv $VENV_DIR
              if [ $upgrade_venv -eq 1 ]; then
                echo -e "\033[32mSuccessfully upgraded venv to Python $cur_version!\033[0m"
              else
                echo -e "\033[32mSuccessfully created venv for Python $PY_MM!\033[0m"
              fi
            }

            . "$VENV_DIR/bin/activate"

            # Install the main project package in editable mode & any script dependencies
            pip install -e "$ROOT/Src" | show_last_line_inplace "[pip - src package] "
            pip install pipdeptree packaging requests | show_last_line_inplace "[pip - script dependencies] "

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

            echo -e "\033[32m"
            GIL_ENABLED=$(python3 -c 'import sys; print(sys._is_gil_enabled())')
            echo "LLAC development environment loaded on $CUR_BRANCH branch"
            echo "Python virtual environment activated."
            echo "Python: $(which python)"
            echo "Python version: $(python3 --version)"
            echo "GIL status: ''${GIL_ENABLED}"
            echo -e "\033[0m"
          else
            echo "FAST_BUILD is set: skipping Python venv setup and dependency installation"
          fi
        '';

  mkLlacShell = python: optimized: pkgs.mkShell {
          buildInputs = with pkgs; [
            (mkPythonEnv python)
            direnv nix-direnv

            # Build tools
            stdenv.cc.cc.lib zlib zlib-ng gcc gnumake pkg-config autoconf automake libtool m4 bison flex
            cmake ninja libmpc mpfr gmp tcl libffi boost readline

            # Graphics (tested: all of these should be optional)
            glib libGL fontconfig libxkbcommon freetype dbus libsForQt5.wrapQtAppsHook
            graphviz xdot

            # Networking
            libslirp

            # System dependencies
            git curl cacert gnupg coreutils-full ccache perl act docker docker-compose
            gawk texinfo gperf expat zlib xz lzip unzip patchutils gperf bash-completion

            # Git dependencies
            pre-commit codespell
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            # macOS specific packages
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            # Linux specific packages
          ];

          inherit ldLibPath;
          shellHook = ''
            export PY_IS_OPT=${if optimized then "1" else "0"}
          '' + baseShellHook;
        };

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
