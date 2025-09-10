#!/bin/bash
set -euo pipefail

# Command line parameters
PARAM_FORCE=0
INSTALL_DEV_TOOLS=0
PRIVILEGE_SCRIPTS=0
UPDATE_SUBMODULES=0
FAST_BUILD=0
SKIP_SUBMODULE_SYNC=1

# These are required for setup on HOST. Try to keep as minimal as possible.
readonly HOST_REQUIREMENTS_DEB=('sudo' 'git' 'curl' 'python3')
readonly HOST_REQUIREMENTS_DARWIN=('git' 'curl' 'python3' 'gawk' 'gnu-sed' 'gnu-tar' 'grep' 'findutils' 'coreutils')

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

readonly ARCH="$(uname -p)"
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

show_last_line_inplace() {
    # Usage: some_command 2>&1 | show_last_line_inplace "[prefix] "
    # - Rewrites the same terminal line with the most recent line from stdin.
    # - If stdout isn't a TTY, it falls back to a plain passthrough (cat), unless FORCE_INLINE_OUTPUT=1.
    local raw_prefix="${1-}"
    local bold_on=$'\033[1m'
    local bold_off=$'\033[22m'
    local italics=$'\033[3m'
    local reset=$'\033[0m'

    # If not a TTY and not forced, passthrough without ANSI to preserve logs
    if [[ ! -t 1 && -z "${FORCE_INLINE_OUTPUT:-}" ]]; then
        cat
        return 0
    fi

    trap 'printf "\n"' INT TERM

    # Determine terminal width (fallback to 80)
    local cols=80
    if [[ -n "${COLUMNS:-}" ]]; then
        cols=${COLUMNS}
    elif command -v tput >/dev/null 2>&1; then
        cols=$(tput cols 2>/dev/null || echo 80)
    fi

    local line disp
    while IFS= read -r line; do
        # Use the last segment after any carriage-return updates
        disp="${line##*$'\r'}"
        local max_len=$(( cols > 1 ? cols - 1 : 1 ))
        local len_prefix=${#raw_prefix}

        printf '\r\033[J'
        if [[ -n "$raw_prefix" && $len_prefix -lt $max_len ]]; then
            # Show full prefix in bold if it fits, then truncate message if needed
            local avail=$(( max_len - len_prefix ))
            local msg="$disp"
            if (( ${#msg} > avail )); then
                local keep=$(( avail > 3 ? avail - 3 : avail ))
                msg="...${msg: -$keep}"
            fi
            printf '%s%s%s%s%s' "$italics" "$bold_on" "$raw_prefix" "$bold_off" "${msg}${reset}"
        else
            # Prefix doesn't fit or is empty: show tail of combined text
            local combined
            if [[ -n "$raw_prefix" ]]; then
                combined="$raw_prefix$disp"
            else
                combined="$disp"
            fi
            if (( ${#combined} > max_len )); then
                local keep=$(( max_len > 3 ? max_len - 3 : max_len ))
                combined="...${combined: -$keep}"
            fi
            printf '%s%s%s' "$italics" "$combined" "$reset"
        fi
    done
    printf '\n'
}
export -f show_last_line_inplace 2>/dev/null || true

print_logo
print_license

help_function() {
    cat <<EOF
Usage: $0 [options]

Options:
  --force              Disregard cache and run install from scratch.
  --extra-dev-tools    Install auxiliary developer tools.
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
        shift;;
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

devsh() {
    # Helper: run a command inside the dev shell (nix develop). If already
    # in a nix shell, just run it in bash with login semantics.
    if [ -z "${IN_NIX_SHELL:-}" ]; then
        nix develop --quiet --impure --command bash -lc "$*" || {
                echo -e "${RED}Error: Command failed inside the Nix dev shell: $*${RESET}"
                exit 1
            }
    else
        bash -lc "$*" || {
                echo -e "${RED}Error: Command failed inside the Nix dev shell: $*${RESET}"
                exit 1
            }
    fi
}

PACKAGES_HOST_REQUIREMENTS=

install_host_packages_linux() {
    for package in "${HOST_REQUIREMENTS_DEB[@]}"; do
        if ! dpkg-query -W -f='${db:Status-Status}\n' "$package" 2>/dev/null \
        | grep -q '^installed$'; then
            PACKAGES_HOST_REQUIREMENTS="$PACKAGES_HOST_REQUIREMENTS_DEB $package"
        fi
    done

    if [ -n "$PACKAGES_HOST_REQUIREMENTS" ]; then
        echo "Installing host packages: $PACKAGES_HOST_REQUIREMENTS"
        sudo apt-get -y install $PACKAGES_HOST_REQUIREMENTS >/dev/null 2>&1 || {
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
        echo "Installing host packages: $PACKAGES_HOST_REQUIREMENTS"
        brew install $PACKAGES_HOST_REQUIREMENTS >/dev/null 2>&1 || {
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

        # Manage system dependencies with apt-get
        command_exists apt-get || {
            echo -e "${RED}Error: Unsupported Linux distro ${distribution}.\n"
            echo "Only Debian-based distros with apt-get are supported.${RESET}"
            exit 1
        }
        echo "Targeting Linux distro ${distribution}"
        echo "Kernel: ${kernel}"
        echo "Architecture: ${ARCH}"; echo

        sudo apt-get -y update > /dev/null 2>&1 && sudo apt-get -y upgrade > /dev/null 2>&1
        install_host_packages_linux

        command_exists docker && sudo usermod -aG docker "${USER}"
    ;;
    "Mac")
        echo "Targeting macOS / Darwin platform"
        if [[ $ARCH == 'arm' ]]; then
            echo "Running on Apple Silicon (ARM architecture)"; echo
        else
            echo "Running on Intel/AMD (x86_64 architecture)"; echo
        fi

        # Manage system dependencies with Homebrew
        command_exists brew || {
            /bin/bash -c "$(curl -fsSL \
            https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >/dev/null 2>&1
        }
        brew update > /dev/null 2>&1

        # Use GNU coreutils tools by default for compatibility
        readonly HOMEBREW_PREFIX=$(brew --prefix)
        for d in ${HOMEBREW_PREFIX}/opt/*/libexec/gnubin; do export PATH=$d:$PATH; done

        install_host_packages_darwin
        ;;
    "FreeBSD") echo "Targeting FreeBSD platform"; echo;;
    "Windows") echo "Windows is not supported. Aborting setup."; exit 1;;
esac

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

advance_progress

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
        nix_profiles=("/nix/var/nix/profiles/default/etc/profile.d/nix.sh" "/etc/profile.d/nix.sh")
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
            if [ -f "$profile" ]; then
                . "$profile"

                # On darwin, if the expected path location is matched add nix to PATH
                # activating the profile doesn't seem to add nix to the PATH correctly (likely due to zshrc differences)
                command_exists nix || {
                    if [[ $OS == "Mac" && "$profile" == "/nix/var/nix/profiles/default"* ]]; then
                        export PATH="/nix/var/nix/profiles/default/bin:$PATH"
                    else
                        echo -e "${YELLOW}Warning: Nix profile script found at unexpected location: ${profile}."
                        echo -e "You will need to manually add Nix to your shell's environment.${RESET}"
                    fi
                }
                return 0
            fi
    done

    echo -e "${YELLOW}Warning: Could not find the Nix profile script to source."
    echo -e "You may need to manually add Nix to your shell's environment.${RESET}"
    set -u
    return 1
}

source_nix_profile >/dev/null 2>&1 || true

command_exists nix || {
    (install_nix) || true
    source_nix_profile || exit 1
}

advance_progress

readonly NIX_CONFIG_DIR="${HOME}/.config/nix"
readonly NIX_CONFIG_FILE="${NIX_CONFIG_DIR}/nix.conf"
grep -q "experimental-features = nix-command flakes" "${NIX_CONFIG_FILE}" 2>/dev/null || {
    mkdir -p "${NIX_CONFIG_DIR}"
    echo "experimental-features = nix-command flakes" >> "${NIX_CONFIG_FILE}"
}

advance_progress

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

echo "Installing dependencies with Nix..."
nix develop --impure --quiet --command true > /dev/null 2>&1 || {
    echo -e "${RED}Error: Failed to enter the Nix dev shell. Aborting setup.${RESET}"
    exit 1
}
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

        # Stream concise, single-line progress; speed up via shallow+filtered clone and parallel submodules
        if ! git clone \
            --recurse-submodules \
            --shallow-submodules \
            --filter=blob:none \
            --jobs "${CORES:-8}" \
            --progress \
            --depth "$recursion_depth" "${url}" "${path}" \
            2>&1 | tr '\r' '\n' | show_last_line_inplace "[clone] "; then
            echo -e "${RED}Error: Failed to clone submodule ${url} into ${path}.${RESET}"
            exit 1
        fi
        echo -e "${CYAN}Submodule ${path} cloned successfully.${RESET}\n"
    done

    echo -e "${CYAN}All submodules cloned successfully.${RESET}\n"
}

[[ "$HAS_RUN_SETUP_SHELL" == 0 || "$UPDATE_SUBMODULES" == 1 ]] && {
    sudo rm -rf .git/submodules

    echo "Updating git submodules..."; echo

    git submodule deinit --all --force 2>&1 | show_last_line_inplace "[submodule deinit] " || true
    if [[ "$SKIP_SUBMODULE_SYNC" == 0 ]]; then
        git submodule sync --recursive 2>&1 | show_last_line_inplace "[submodule sync] " || true
    else
        echo "[submodule sync] skipped by flag"
    fi
    git -c protocol.version=2 submodule update --init --recursive \
        --depth 1 --jobs "${CORES:-8}" --recommend-shallow --filter=blob:none \
        2>&1 | show_last_line_inplace "[submodule update] " || true

    echo -e "${CYAN}Git submodules updated successfully.${RESET}\n"

    clone_submodules
}

advance_progress

[[ "$INSTALL_DEV_TOOLS" == 1 ]] && {

    [[ "$PARAM_FORCE" == 1 ]] && {
        echo "Removing existing installations..."
        sudo rm -rf $SUBMODULE_BIN > /dev/null 2>&1 || true
    }

    # Temporarily enable FAST_BUILD for compilation of optional dependencies to skip
    # unnecessary nix shell hooks
    old_fast_build=$FAST_BUILD
    export FAST_BUILD=1

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

    echo "Installing riscv-gnu-toolchain from source (this will take a while)..."
        devsh '
            set -euo pipefail
            cd "$ROOT/submodules/riscv-gnu-toolchain"

            [[ -n "${CONFIG_EXTRA:=}" ]] && {
                echo "Using configure extras: ${CONFIG_EXTRA}"
            }

            # GCC configure will fail if LIBRARY_PATH includes the current directory
            # Sanitize by unsetting it for this build.
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

            # Clean previous partial builds to ensure flags/toolchain changes take effect
            sudo rm -rf build-gcc-newlib-stage1 build-newlib build-newlib-nano stamps/build-newlib* \
            build-newlib/riscv32-unknown-elf/newlib || true

            # Build the bootstrap cross-compiler first (target name is build-gcc1)
            if ! make -j "$CORES" build-gcc1 2>&1 | show_last_line_inplace "[make gcc1] "; then
                echo "Error: bootstrap GCC (stage1) build failed."
                exit 1
            fi

            # Prefer the installed cross driver wrapper for target compiler
            TARGET_CC="riscv32-unknown-elf-gcc"
            TARGET_CXX="riscv32-unknown-elf-g++"

            # Force newlib to use the cross-compiler by setting CC_FOR_TARGET/CXX_FOR_TARGET
            # (honored by the riscv-gnu-toolchain newlib build via environment).
            if ! CC_FOR_TARGET="$TARGET_CC" CXX_FOR_TARGET="$TARGET_CXX" \
                make -j "$CORES" V=1 newlib 2>&1 | show_last_line_inplace "[make newlib] "; then

                [[ "${RISCV_GNU_TOOLCHAIN_BUILD_CAN_SOFTFAIL:-0}" == 1 ]] && {
                    echo "Warning: riscv-gnu-toolchain newlib build failed. Soft failing."
                    exit 0
                }

                echo "Error: riscv-gnu-toolchain build failed. Aborting."
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

    export FAST_BUILD=$old_fast_build
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

    echo -e "${CYAN}All developer tools installed successfully.${RESET}\n"
}

advance_progress

[[ "$HAS_RUN_SETUP_SHELL" == 0 ]] && {
    # Configure git for the repository
    git config --local --add safe.directory "${ROOT}"
    git config --local --add --bool push.autoSetupRemote true
    git config --local core.hooksPath .github/hooks
    git config --local init.defaultBranch main
    git config --local pull.rebase true

    # Any other git setup tasks go here
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

advance_progress

echo -e "${GREEN}Setup complete!${RESET}\n"
exit 0
