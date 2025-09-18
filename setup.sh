#!/bin/bash
set -euo pipefail

# Command line parameters
PARAM_FORCE=0
INSTALL_DEV_TOOLS=0
PRIVILEGE_SCRIPTS=0
UPDATE_SUBMODULES=0
FAST_BUILD=0
SKIP_SUBMODULE_SYNC=1

# Selected developer tools (from --extra-dev-tools)
DEV_TOOLS=()

# These are required for setup on HOST. Try to keep as minimal as possible.
readonly HOST_REQUIREMENTS_DEB=('sudo' 'git' 'curl' 'python3')
readonly HOST_REQUIREMENTS_DARWIN=('bash' 'git' 'curl' 'python3' 'gawk' 'gnu-sed' 'gnu-tar' 'grep' 'findutils' 'coreutils')

# ANSI codes
readonly ITALICS='\033[3m'
readonly BOLD='\033[1m'
readonly RED='\033[0;31m'
readonly ORANGE='\033[0;33m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly MAGENTA='\033[1;35m'
readonly RESET='\033[0m'

readonly GIT_REPO_URL="https://github.com/topologicalhurt/Thesis.git"
readonly TOTAL_STEPS=8

PWD="$(pwd)"

get_os() {
    case "$(uname -s)" in
        Linux*) echo "Linux";;
        Darwin*) echo "Mac";;
        FreeBSD*) echo "FreeBSD";;
        CYGWIN*|MINGW*|MSYS_NT*) echo "Windows";;
        *) echo "UNKNOWN:$(uname -s)";;
    esac
}

readonly ARCH="$(uname -m)"
readonly OS="$(get_os)"

print_logo() {
    art=$(cat <<'EOF'
██╗     ██╗      █████╗  ██████╗    ██████╗ ██████╗  ██████╗      ██╗███████╗ ██████╗████████╗
██║     ██║     ██╔══██╗██╔════╝    ██╔══██╗██╔══██╗██╔═══██╗     ██║██╔════╝██╔════╝╚══██╔══╝
██║     ██║     ███████║██║         ██████╔╝██████╔╝██║   ██║     ██║█████╗  ██║        ██║
██║     ██║     ██╔══██║██║         ██╔═══╝ ██╔══██╗██║   ██║██   ██║██╔══╝  ██║        ██║
███████╗███████╗██║  ██║╚██████╗    ██║     ██║  ██║╚██████╔╝╚█████╔╝███████╗╚██████╗   ██║
╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝ ╚══════╝ ╚═════╝   ╚═╝
EOF
)

    colors=(32 31 31 34)
    num_colors=${#colors[@]}
    num_rows=$(echo "$art" | wc -l)
    num_rows=$(($num_rows - 1))
    row=0
    last_char=0

    echo "$art" | while IFS= read -r line; do
      col=0
      while [ $col -lt ${#line} ]; do
        char="${line:$col:1}"

        color_index=$(((row + col) % num_colors))
        color_code="${colors[$color_index]}"
        printf "\033[${color_code}m%s" "$char"

        last_char=$char
        col=$((col + 1))
      done
      printf "\033[0m\n"
      row=$((row + 1))
    done
}

print_license() {
    echo """
    LLAC  Copyright (C) 2025  topologicalhurt csin0659@uni.sydney.edu.au
    This program comes with ABSOLUTELY NO WARRANTY; for details type --help license_warranty
    This is free software, and you are welcome to redistribute it
    under certain conditions; type --help license_conditions for details.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    """
}

ProgressBar() {
    # Arguments: current, total
    local current=${1}
    local total=${2}
    if [[ ${total} -eq 0 ]]; then
        total=1
    fi
    local progress_percent=$(( (current * 100) / total ))

    local bar_width=40
    local num_done=$(( (progress_percent * bar_width) / 100 ))
    local num_left=$(( bar_width - num_done ))

    local done_str
    done_str=$(printf "%${num_done}s" "")
    local left_str
    left_str=$(printf "%${num_left}s" "")

    printf "\rProgress : [${done_str// /#}${left_str// /-}] ${progress_percent}%%\n"
}

advance_progress() {
    let _progress++ || true; ProgressBar ${_progress} ${TOTAL_STEPS}
}

print_logo
print_license

help_function() {
    cat <<EOF
Usage: $0 [options]

Options:
  --force              Disregard cache and run install from scratch.
  --extra-dev-tools    Install selected developer tools. Accepts: verilator riscv yosys
                       Example: --extra-dev-tools verilator riscv
  --privilege-scripts  Apply privileging to script directories.
  --fast-build         Avoid long build-times by skipping compilation of optional dependencies. E.g submodules distributed as source, use mainline builds etc.
  --update-submodules  Force update and re-clone of git submodules.
  --submodule-sync     'git submodule sync' step (only needed if .gitmodules URLs changed).
  --help               Show this help message.
EOF
    exit 0
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            PARAM_FORCE=1
        shift;;
        --extra-dev-tools)
            INSTALL_DEV_TOOLS=1
            shift
            while [[ $# -gt 0 && $1 != --* ]]; do
                DEV_TOOLS+=("$1")
                shift
            done
        ;;
        --privilege-scripts)
            PRIVILEGE_SCRIPTS=1
        shift;;
        --fast-build)
            export FAST_BUILD=1
            export PYTHON_ENV="python-stable"
        shift;;
        --update-submodules)
            UPDATE_SUBMODULES=1
        shift;;
        --submodule-sync)
            SKIP_SUBMODULE_SYNC=0
        shift;;
        --help) help_function;;
        *) help_function;;
    esac

done

# Returns 0 if the given tool is explicitly selected via --extra-dev-tools
dev_tool_selected() {
    local tool="$1"
    if [[ ${#DEV_TOOLS[@]} -eq 0 ]]; then
        return 1
    fi
    local t
    for t in "${DEV_TOOLS[@]}"; do
        if [[ "$t" == "$tool" ]]; then
            return 0
        fi
    done
    return 1
}

devsh() {
    # Helper: run a command inside the dev shell (nix develop). If already
    # in a nix shell, just run it in bash with login semantics.
    if [ -z "${IN_NIX_SHELL:-}" ]; then
        if [ "${EUID}" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
            sudo -Eu "${SUDO_USER}" nix develop "${ROOT}" --refresh --impure --quiet --command bash -lc "$*" || {
                echo -e "${RED}Error: Command failed inside the Nix dev shell (user ${SUDO_USER}): $*${RESET}"
                exit 1
            }
        else
            nix develop "${ROOT}" --refresh --impure --quiet --command bash -lc "$*" || {
                echo -e "${RED}Error: Command failed inside the Nix dev shell: $*${RESET}"
                exit 1
            }
        fi
    else
        bash -lc "$*" || {
                echo -e "${RED}Error: Command failed inside the Nix dev shell: $*${RESET}"
                exit 1
            }
    fi
}

extract_archive() {
    # Helper: extract a tar or gzip archive
    local f="$1"
    if tar -tzf "$f" >/dev/null 2>&1; then
        tar -xzf "$f"
        return $?
    elif tar -tf "$f" >/dev/null 2>&1; then
        tar -xf "$f"
        return $?
    elif gzip -t "$f" >/dev/null 2>&1; then
        local out="${f%.gz}"
        gzip -dc -- "$f" > "$out"
        return $?
    else
        echo "not a tar or gzip archive: $f" >&2
        return 1
    fi
}

if [[ $EUID -ne 0 ]]; then
    echo -e "${YELLOW}Warning: This script performs actions that require elevated privileges.${RESET}\n"
    echo "Options: Inspect and run steps manually, run inside a privileged container,"
    echo "or allow this script to restart itself under sudo."
    echo
    read -r -n 1 -p "Elevate and re-run as root via sudo? [y/N]: " response; echo
    if [[ ! $response =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborting: root privileges required for automatic setup.${RESET}"
        exit 1
    fi
fi

_progress=0
ProgressBar 0 ${TOTAL_STEPS}

PACKAGES_HOST_REQUIREMENTS=
echo "Checking & installing host packages..."; echo

install_host_packages_linux() {
    for package in "${HOST_REQUIREMENTS_DEB[@]}"; do
        if ! dpkg-query -W -f='${db:Status-Status}\n' "$package" 2>/dev/null \
        | grep -q '^installed$'; then
            PACKAGES_HOST_REQUIREMENTS="$PACKAGES_HOST_REQUIREMENTS_DEB $package"
        fi
    done

    if [ -n "$PACKAGES_HOST_REQUIREMENTS" ]; then
        echo "Installing the following host packages: $PACKAGES_HOST_REQUIREMENTS"
        sudo apt-get -y install $PACKAGES_HOST_REQUIREMENTS | show_last_line_inplace "[host install] " || {
            echo -e "${RED}Error: Failed to install host packages: $PACKAGES_HOST_REQUIREMENTS${RESET}"
            exit 1
        }
        echo -e "${CYAN}Host packages installed successfully.${RESET}\n"
    fi
}

install_host_packages_darwin() {
    for package in "${HOST_REQUIREMENTS_DARWIN[@]}"; do
        if ! brew list "$package" >/dev/null 2>&1; then
            PACKAGES_HOST_REQUIREMENTS="$PACKAGES_HOST_REQUIREMENTS $package"
        fi
    done

    if [ -n "$PACKAGES_HOST_REQUIREMENTS" ]; then
        echo "Installing the following host packages: $PACKAGES_HOST_REQUIREMENTS"
        brew install $PACKAGES_HOST_REQUIREMENTS | show_last_line_inplace "[host install] " || {
            echo -e "${RED}Error: Failed to install host packages: $PACKAGES_HOST_REQUIREMENTS${RESET}"
            exit 1
        }
        echo -e "${CYAN}Host packages installed successfully.${RESET}\n"
    fi
}

case $OS in
    "Linux")
        distribution=$(cat /etc/*-release | grep -oP '(?<=^NAME=")[^"]+')
        kernel=$(uname -r | grep -oP '^[\d.]+')

        command_exists apt-get || {
            echo -e "${RED}Error: Unsupported Linux distro ${distribution}.\n"
            echo "Only Debian-based distros with apt-get are supported.${RESET}"
            exit 1
        }
        echo -e "${ITALICS}"
        echo "Targeting Linux distro ${distribution}"
        echo "Kernel: ${kernel}"
        echo "Architecture: ${ARCH}"
        echo -e "${RESET}\n"

        sudo apt-get -y update > /dev/null 2>&1 || true
        sudo apt-get -y upgrade > /dev/null 2>&1 || true
        install_host_packages_linux
    ;;
    "Mac")
        echo -e "${ITALICS}"
        echo "Targeting macOS / Darwin platform"
        if [[ $ARCH == 'arm' ]]; then
            echo "Architecture: Apple Silicon (ARM architecture)"; echo
        else
            echo "Architecture: Intel/AMD (x86_64 architecture)"; echo
        fi
        echo -e "${RESET}\n"

        command_exists brew || {
            /bin/bash -c "$(curl -fsSL \
            https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >/dev/null 2>&1
        }
        brew update > /dev/null 2>&1

        # Use GNU coreutils tools
        readonly HOMEBREW_PREFIX=$(brew --prefix)
        for d in ${HOMEBREW_PREFIX}/opt/*/libexec/gnubin; do export PATH=$d:$PATH; done

        install_host_packages_darwin
        ;;
    "FreeBSD") echo "Targeting FreeBSD platform"; echo;;
    "Windows") echo "Windows is not supported. Aborting setup."; exit 1;;
esac

advance_progress

echo "Running auxiliary setup steps..." ; echo

. "$PWD/.env.shared"

git rev-parse --git-dir > /dev/null 2>&1 || {
    REPO_NAME=$(basename "${GIT_REPO_URL}" .git)
    echo "Not a git repository. Cloning '${REPO_NAME}'..."
    [ -d "$ROOT/$REPO_NAME" ] && {
        echo -e "${RED}Error: Directory '${REPO_NAME}' already exists. Aborting.${RESET}"
        exit 1
    }
    git clone "${GIT_REPO_URL}" --depth 1
    cd "$ROOT/$REPO_NAME"
}

readonly SUBMODULE_BIN="$ROOT/bin"
readonly SETUP_CACHE="${ROOT}/bin/cache"
readonly HAS_RUN_SETUP_SHELL=$([ "${PARAM_FORCE}" -eq 0 ] && \
[ -f "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE" ] && echo 1 || echo 0)
readonly HOOKS_DIR="${ROOT}/.github/hooks"
readonly RTL_SCRIPTS_DIR="${ROOT}/Src/Scripts"
readonly PRE_COMMIT_CONFIG_YAML="${ROOT}/.github/hooks/.pre-commit-config.yaml"
readonly PRE_COMMIT_DIR="${ROOT}/.github/hooks/pre_commit"
readonly PRE_PUSH_SCRIPT="${ROOT}/.github/hooks/pre-push"

echo -e "${CYAN}Steps ran successfully.${RESET}\n"

advance_progress

echo "Installing / sourcing nix profile..."; echo

install_nix() {
    if [[ $EUID -eq 0 ]]; then
        echo "Nix not found. Installing Nix (multi-user daemon)..."
        su - "${SUDO_USER}" -c 'curl -fsSL https://nixos.org/nix/install | bash -s -- --daemon --yes' > /dev/null 2>&1
    else
        echo "Nix not found. Installing Nix..."
        curl -fsSL https://nixos.org/nix/install | bash -s > /dev/null 2>&1
    fi
}

source_nix_profile() {
    local nix_profiles=()
    if [[ $OS == "Linux" ]]; then
        nix_profiles=("/nix/var/nix/profiles/default" "/nix/var/nix/profiles/default/etc/profile.d/nix.sh" "/etc/profile.d/nix.sh")
    else
        # Annoyingly, on darwin the Nix profile may be mounted on a separate volume
        diskutil list | grep -q "Nix Store" && {
            nix_vol="$(mount | grep 'Nix Store' | awk '{print $3"/var/nix/profiles/default/etc/profile.d/nix.sh"}')"
        }
        nix_profiles=("/opt/homebrew/etc/profile.d/nix.sh" "/nix/var/nix/profiles/default/etc/profile.d/nix.sh" $nix_vol
         "~/.nix-profile/etc/profile.d/nix.sh" "/etc/profile.d/nix.sh")
    fi

    set +u
    for profile in "${nix_profiles[@]}"; do

        [[ -L "$profile" ]] && profile=$(readlink -f "$profile")

        [[ -f "$profile" ]] && {
            . "$profile"

            # On darwin activating the profile doesn't seem to add nix to the PATH correctly (likely due to zshrc differences)
            command_exists nix || {
                if [[ $OS == "Mac" && "$profile" == "/nix/var/nix/profiles/default"* ]]; then
                    export PATH="/nix/var/nix/profiles/default/bin:$PATH"
                else
                    echo -e "${YELLOW}Warning: Nix profile script found at unexpected location: ${profile}."
                    echo -e " You will need to manually add Nix to your shell's environment.${RESET}"
                fi
            }
            return 0
        }
    done
    set -u

    echo -e "${YELLOW}Warning: Could not find the Nix profile script to source."
    echo -e " You may need to manually add Nix to your shell's environment.${RESET}"

    return 1
}

if ! command_exists nix; then
    install_nix
    source_nix_profile && {
        echo -e "${CYAN}Nix installed and profile sourced successfully.${RESET}\n"
    }
else
    source_nix_profile && {
        echo -e "${CYAN}Nix profile sourced successfully.${RESET}\n"
    }
fi

advance_progress

readonly NIX_CONFIG_DIR="${HOME}/.config/nix"
readonly NIX_CONFIG_FILE="${NIX_CONFIG_DIR}/nix.conf"
grep -q "experimental-features = nix-command flakes" "${NIX_CONFIG_FILE}" 2>/dev/null || {
    mkdir -p "${NIX_CONFIG_DIR}"
    echo "experimental-features = nix-command flakes" >> "${NIX_CONFIG_FILE}"
}

echo "Applying privileging to script directories..."; echo

privilege_script_dir() {
    local target_dir="$1"
    shift
    local patterns=("$@")
    local find_args=()
    for pattern in "${patterns[@]}"; do
        [[ ${#find_args[@]} -gt 0 ]] && find_args+=("-o")
        find_args+=("-name" "${pattern}")
    done
    find "${target_dir}" -type d -exec sudo chmod 755 {} +
    while IFS= read -r -d $'\0' file; do
        if head -n 1 "${file}" | grep -q "^#!"; then
            sudo chmod 755 "${file}"
        else
            sudo chmod 644 "${file}"
        fi
    done < <(find "${target_dir}" -type f \( "${find_args[@]}" \) -print0)
}

[[ "$HAS_RUN_SETUP_SHELL" == 0 || "$PRIVILEGE_SCRIPTS" == 1 ]] && {
    echo "Privileging script directories..."
    privilege_script_dir "${HOOKS_DIR}" "*.sh"
    privilege_script_dir "${RTL_SCRIPTS_DIR}" "*.sh" "*.py"
    [ -e "${HOOKS_DIR}/run_hook.sh" ] && sudo chmod 755 "${HOOKS_DIR}/run_hook.sh"
    [ -d "${PRE_COMMIT_DIR}" ] && sudo chmod 755 "${PRE_COMMIT_DIR}"
    [ -e "${PRE_PUSH_SCRIPT}" ] && sudo chmod 755 "${PRE_PUSH_SCRIPT}"
    [ -e "${PRE_COMMIT_CONFIG_YAML}" ] && sudo chmod 644 "${PRE_COMMIT_CONFIG_YAML}"

    echo -e "${CYAN}Script directories privileged successfully.${RESET}\n"
}

advance_progress

echo "Installing dependencies with Nix..."; echo

if [ "${EUID}" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
    sudo -Eu "${SUDO_USER}" nix develop "${ROOT}" --refresh --impure --quiet --command true > /dev/null 2>&1 || {
        echo -e "${RED}Error: Failed to enter the Nix dev shell. Aborting setup.${RESET}"
        exit 1
    }
else
    nix develop "${ROOT}" --refresh --impure --quiet --command true > /dev/null 2>&1 || {
    echo -e "${RED}Error: Failed to enter the Nix dev shell. Aborting setup.${RESET}"
    exit 1
    }
fi
echo -e "${CYAN}Nix dependencies installed successfully.${RESET}\n"

advance_progress

clone_submodules() {

    local _recursion_depth
    if [[ "$FAST_BUILD" == 1 ]]; then
        _recursion_depth=1
    else
        _recursion_depth=2
    fi

    git config -f .gitmodules --get-regexp '^submodule\..*\.url' | while read -r key url; do
        path="$(git config -f .gitmodules "${key/.url/.path}")"

        if [[ "$PARAM_FORCE" == 1 ]]; then
            echo "Removing existing submodule path: ${path}"
            sudo rm -rf "${path}"
        else
            echo -e "${YELLOW}Warning: Skipping removal of existing submodule path ${path}. Use --force to re-clone.${RESET}"
        fi

        [[ -d "${path}" ]] && {
            echo -e "${YELLOW}Warning: Submodule path ${path} already exists. Skipping clone.${RESET}\n"
            continue
        }

        echo "Cloning ${url} -> ${path} (this may take a while)..."

        # On some large submodules (e.g riscv-gnu-toolchain) limit recursion depth to avoid extremely long clone times
        local recursion_depth=$_recursion_depth
        case "$path" in
            "submodules/riscv-gnu-toolchain")
                recursion_depth=1
            ;;
            *) : ;;
        esac

        if ! git clone \
            --recurse-submodules \
            --shallow-submodules \
            --filter=blob:none \
            --jobs "${CORES:-8}" \
            --progress \
            --depth "$recursion_depth" "${url}" "${path}" \
            2>&1 | show_last_line_inplace "[clone] "; then
            echo -e "${RED}Error: Failed to clone submodule ${url} into ${path}.${RESET}"
            exit 1
        fi
        echo -e "${CYAN}Submodule ${path} cloned successfully.${RESET}\n"
    done

    echo -e "${CYAN}All submodules cloned successfully.${RESET}\n"
}

[[ "$HAS_RUN_SETUP_SHELL" == 0 || "$UPDATE_SUBMODULES" == 1 ]] && {
    echo "Updating git submodules..."; echo

    if [[ "$SKIP_SUBMODULE_SYNC" == 0 ]]; then
        git submodule sync --recursive 2>&1 | show_last_line_inplace "[submodule sync] "
    else
        echo "[submodule sync] skipped by flag"
    fi

    git -c protocol.version=2 submodule update --init --recursive \
        --jobs "${CORES:-8}" --recommend-shallow --filter=blob:none \
        2>&1 | show_last_line_inplace "[submodule update] "

    echo -e "${CYAN}Git submodules updated successfully.${RESET}\n"

    clone_submodules
}

advance_progress

[[ "$INSTALL_DEV_TOOLS" == 1 || "$PARAM_FORCE" == 1 || "$UPDATE_SUBMODULES" == 1 ]] && {

    [[ "$PARAM_FORCE" == 1 ]] && {
        echo "Removing existing installations..."
        sudo rm -rf $SUBMODULE_BIN > /dev/null 2>&1 || true
    }

    # Temporarily enable FAST_BUILD for compilation step
    old_fast_build=$FAST_BUILD
    export FAST_BUILD=1

    # Determine default behavior: if --extra-dev-tools was passed without values, build all
    BUILD_ALL_DEV_TOOLS=0
    if [[ "$INSTALL_DEV_TOOLS" == 1 && ${#DEV_TOOLS[@]} -eq 0 ]]; then
        BUILD_ALL_DEV_TOOLS=1
    fi

    # Verilator
    if [[ $BUILD_ALL_DEV_TOOLS -eq 1 ]] || dev_tool_selected verilator; then
        echo "Installing Verilator from source (this will take a while)..."
            devsh '
                set -euo pipefail

                unset VERILATOR_ROOT
                cd "$ROOT/submodules/verilator"
                autoconf 2>&1 | show_last_line_inplace "[autoconf] "

                [[ -z "${VERILATOR_PREFIX:-}" ]] && {
                    VERILATOR_PREFIX="$ROOT/bin/verilator"
                }

                mkdir -p "$VERILATOR_PREFIX"
                if ! ./configure --prefix="$VERILATOR_PREFIX" 2>&1 | show_last_line_inplace "[configure] "; then

                    [[ "${VERILATOR_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                        echo "Warning: Verilator configure failed. Soft failing."
                        exit 0
                    }

                    echo "Error: Verilator configure failed. Aborting."
                    exit 1
                fi

                if ! make -j "$CORES" install 2>&1 | show_last_line_inplace "[make] "; then

                    [[ "${VERILATOR_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                        echo "Warning: Verilator build failed. Soft failing."
                        exit 0
                    }

                    echo "Error: Verilator build failed. Aborting."
                    make clean > /dev/null 2>&1
                    exit 1
                fi
            '

        export PATH="$VERILATOR_PREFIX/bin:${PATH}"

        if ! command_exists verilator; then
            echo -e "${YELLOW}Warning: Verilator couldn't be added to PATH."
            echo    " this doesn't neccesserily mean that the installation failed."
            echo -e " You may need to manually add ${VERILATOR_PREFIX}/bin to your PATH.${RESET}"
        else
            sudo ln -sfn "$VERILATOR_PREFIX" /opt/verilator > /dev/null || true
            echo -e "\n${CYAN}Verilator successfully compiled from source."
            echo -e "Version: $(verilator --version | head -n1)${RESET}\n"
        fi
    fi

    # RISC-V toolchain
    if [[ $BUILD_ALL_DEV_TOOLS -eq 1 ]] || dev_tool_selected riscv; then
        echo "Installing riscv-gnu-toolchain from source (this will take a while)..."
            devsh '
                set -euo pipefail
                cd "$ROOT/submodules/riscv-gnu-toolchain"

                [[ -n "${CONFIG_EXTRA:=}" ]] && {
                    echo "Using configure extras: ${CONFIG_EXTRA}"
                }

                # GCC configure will fail if LIBRARY_PATH includes the current directory
                [[ -n "${LIBRARY_PATH:-}" ]] && {
                    unset LIBRARY_PATH
                }

                # Prevent host CFLAGS/CXXFLAGS leaking into target builds
                for v in CFLAGS_FOR_TARGET CXXFLAGS_FOR_TARGET CFLAGS CXXFLAGS CPPFLAGS LDFLAGS; do
                    if [ -n "${!v:-}" ]; then
                        unset "$v"
                    fi
                done

                [[ -z "${RISCV_INSTALL_PREFIX:-}" ]] && {
                    RISCV_INSTALL_PREFIX="$ROOT/bin/riscv"
                }

                # Bare-metal (newlib) toolchain for RV32GC ILP32D
                mkdir -p "$RISCV_INSTALL_PREFIX"
                if ! ./configure --prefix="$RISCV_INSTALL_PREFIX" --with-arch=rv32gc --with-abi=ilp32d \
                --with-isa-spec=2.2 --with-cmodel=medany --with-languages=c $CONFIG_EXTRA 2>&1 \
                | show_last_line_inplace "[configure] "; then

                    [[ "${RISCV_GNU_TOOLCHAIN_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                        echo "Warning: riscv-gnu-toolchain configure failed. Soft failing."
                        exit 0
                    }

                    echo "Error: riscv-gnu-toolchain configure failed. Aborting."
                    exit 1
                fi

                # Build the bootstrap cross-compiler first
                if ! make -j "$CORES" build-gcc1 2>&1 | show_last_line_inplace "[make gcc1] "; then
                    echo "Error: bootstrap GCC (stage1) build failed."
                    make clean > /dev/null 2>&1
                    exit 1
                fi

                TARGET_CC="riscv32-unknown-elf-gcc"
                TARGET_CXX="riscv32-unknown-elf-g++"

                # Force newlib to use the cross-compiler
                if ! CC_FOR_TARGET="$TARGET_CC" CXX_FOR_TARGET="$TARGET_CXX" \
                    make -j "$CORES" V=1 newlib 2>&1 | show_last_line_inplace "[make newlib] "; then

                    [[ "${RISCV_GNU_TOOLCHAIN_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                        echo "Warning: riscv-gnu-toolchain newlib build failed. Soft failing."
                        exit 0
                    }

                    echo "Error: riscv-gnu-toolchain build failed. Aborting."
                    make clean > /dev/null 2>&1
                    exit 1
                fi

                [[ "$FAST_BUILD" == 1 ]] && {
                    echo "Skipping QEMU build as --fast-build was set."; echo
                    exit 0
                }

                # Optional: build QEMU simulator (not required for the toolchain itself)
                make -j "$CORES" build-sim SIM=qemu 2>&1 | show_last_line_inplace "[make qemu] " || {
                    echo "Warning: QEMU build failed. Continuing without QEMU support."
                }
            '

        export PATH="$RISCV_INSTALL_PREFIX/bin:${PATH}"
        if ! command_exists riscv32-unknown-elf-gcc; then
            echo -e "${YELLOW}Warning: riscv-gnu-toolchain couldn't be added to PATH."
            echo    " this doesn't neccesserily mean that the installation failed."
            echo -e " You may need to manually add ${RISCV_INSTALL_PREFIX}/bin to your PATH.${RESET}"
        else
            sudo ln -sfn "$RISCV_INSTALL_PREFIX" /opt/riscv > /dev/null || true
            echo -e "\n${CYAN}RISC-V GNU Toolchain successfully compiled from source."
            echo -e " Version: $(riscv32-unknown-elf-gcc --version | head -n1)${RESET}\n"
        fi
    fi

    # Yosys
    if [[ $BUILD_ALL_DEV_TOOLS -eq 1 ]] || dev_tool_selected yosys; then
        echo "Installing Yosys from source (this will take a while)..."
            devsh '
                set -euo pipefail
                cd "$ROOT/submodules/yosys"

                # Ensure headers and libs are discoverable via pkg-config
                TCL_CFLAGS=$(pkg-config --cflags tcl 2>/dev/null || true)
                TCL_LIBS=$(pkg-config --libs tcl 2>/dev/null || true)
                READLINE_CFLAGS=$(pkg-config --cflags readline 2>/dev/null || true)
                READLINE_LIBS=$(pkg-config --libs readline 2>/dev/null || echo -lreadline)

                export CPPFLAGS="${TCL_CFLAGS} ${READLINE_CFLAGS} ${CPPFLAGS:-}"
                export LDFLAGS="${TCL_LIBS} ${READLINE_LIBS} ${LDFLAGS:-}"

                [[ -z "${YOSYS_INSTALL_PREFIX:-}" ]] && {
                    YOSYS_INSTALL_PREFIX="$ROOT/bin/yosys"
                }

                make config-gcc 2>&1 | show_last_line_inplace "[make config] "
                if ! make -j "$CORES" install DESTDIR="$YOSYS_INSTALL_PREFIX"; then

                    [[ "${YOSYS_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                        echo "Warning: Yosys build failed. Soft failing."
                        exit 0
                    }

                    echo "Error: Yosys build failed. Aborting."
                    make clean > /dev/null 2>&1
                    exit 1
                fi
            '

        export PATH="$YOSYS_INSTALL_PREFIX/bin:${PATH}"
        if ! command_exists yosys; then
            echo -e "${YELLOW}Warning: yosys couldn't be added to PATH."
            echo    " this doesn't neccesserily mean that the installation failed."
            echo -e " You may need to manually add ${YOSYS_INSTALL_PREFIX}/bin to your PATH.${RESET}"
        else
            echo -e "\n${CYAN}Yosys successfully compiled from source."
            echo -e " Version: $(yosys --version | head -n1)${RESET}\n"
        fi
    fi

    export FAST_BUILD=$old_fast_build

    echo -e "${CYAN}All developer tools installed successfully.${RESET}\n"
}

advance_progress

echo "Configuring git for the repository..."; echo

[[ "$HAS_RUN_SETUP_SHELL" == 0 ]] && {
    # Configure git for the repository
    git config --local --add safe.directory "${ROOT}"
    git config --local --add --bool push.autoSetupRemote true
    git config --local core.hooksPath .github/hooks
    git config --local init.defaultBranch main
    git config --local pull.rebase true

    git fetch origin
}

[[ "$PARAM_FORCE" == 1 ]] && {
    devsh '
        pre-commit clean > /dev/null 2>&1 || true
    '
}

[[ "$HAS_RUN_SETUP_SHELL" == 0 ]] && {
    # FIX: Will not work because of bash-completion dependency issues in nix shell
    # devsh '
    #     pre-commit install > /dev/null 2>&1 || {
    #         echo -e "'${RED}'Error: pre-commit install failed. Aborting.'${RESET}'"
    #         exit 1
    #     }
    #     ln -sf "${PRE_COMMIT_CONFIG_YAML}" "${ROOT}/.pre-commit-config.yaml" > /dev/null || true
    # '
    :
}

[[ "$HAS_RUN_SETUP_SHELL" == 0 ]] && {
    mkdir -p "${SETUP_CACHE}"
    touch "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE"
}

echo -e "${CYAN}Git configured successfully.${RESET}\n"

advance_progress

echo -e "${GREEN}Setup complete!${RESET}\n"
exit 0
