#!/usr/bin/env bash
set -euo pipefail

PARAM_FORCE=0
INSTALL_DEV_TOOLS=0
PRIVILEGE_SCRIPTS=0

PWD="$(pwd)"

readonly VENV_DIR="${PWD}/.venv"
readonly SETUP_CACHE="${PWD}/bin/cache"
readonly HOOKS_DIR="${PWD}/.github/hooks"
readonly RTL_SCRIPTS_DIR="${PWD}/Src/Scripts"
readonly PRE_COMMIT_CONFIG_YAML="${PWD}/.github/hooks/.pre-commit-config.yaml"
readonly PRE_COMMIT_DIR="${PWD}/.github/hooks/pre_commit"
readonly PRE_PUSH_SCRIPT="${PWD}/.github/hooks/pre-push"

readonly RAN_LLAC_SETUP_SHELL=$([ "${PARAM_FORCE}" -eq 0 ] && [ -f "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE" ] && echo 1 || echo 0)
readonly GIT_REPO_URL="https://github.com/topologicalhurt/Thesis.git"

# ANSI color codes
readonly RED='\033[0;31m'
readonly ORANGE='\033[0;33m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly MAGENTA='\033[1;35m'
readonly RESET='\033[0m'

print_logo() {
    art=$(cat <<'EOF'
 *--------------------------------------------------------------------------------------------------------------*
 |                                                                                                              |
 |                               ██▓     ██▓     ▄▄▄       ▄████▄                                               |
 |                              ▓██▒    ▓██▒    ▒████▄    ▒██▀ ▀█                                               |
 |                              ▒██░    ▒██░    ▒██  ▀█▄  ▒▓█    ▄                                              |
 |                              ▒██░    ▒██░    ░██▄▄▄▄██ ▒▓▓▄ ▄██▒                                             |
 |                              ░██████▒░██████▒ ▓█   ▓██▒▒ ▓███▀ ░                                             |
 |                              ░ ▒░▓  ░░ ▒░▓  ░ ▒▒   ▓▒█░░ ░▒ ▒  ░                                             |
 |                              ░ ░ ▒  ░░ ░ ▒  ░  ▒   ▒▒ ░  ░  ▒                                                |
 |                                $ $     $ $     $   ▒   $                                                     |
 |                                  $  $    $  $      $  $░ $                                                   |
 |                                                        $                                                     |
 |                                                                                                              |
 |   ▒▓███████▓▒░  ░▒▓███████▓▒░   ░▒▓██████▓▒░        ░▒▓█▓████░▒▓███████▓▒░    ░▒▓██████▓▒░   ▒▓████████▓▒░   |
 |     ░▒▓█▓   ▒▓█▓▒░ ░▒▓█▓▒  ▓█▓▒░ ░▒▓█▓▒ ░▒▓█▓▒░       ░▒▓█▓▒░  ▒▓█▓▒░        ░▒▓█▓▒  ▒▓█▓▒░    ░▒▓█▓▒░       |
 |     ░▒▓█▓   ▒▓█▓▒░ ░▒▓█▓▒  ▒▓█▓▒░ ░▒▓█▓▒░░▒▓█▓▒░       ░▒▓█▓▒ ░▒▓█▓▒░          ░▒▓█▓          ░▒▓█▓▒░        |
 |       ░▒▓███████▓▒░░▒▓███████▓▒░░▒▓█▓▒  ░▒▓█▓▒░         ▒▓█▓▒░  ░▒▓██████▓  ░ ▓█▓▒░            ░▒▓█▓▒░       |
 |     ░▒▓█▓▒░        ░▒▓█▓▒  ▒▓█▓▒░ ░▒▓█▓▒░ ▒▓█▓▒░   █▓▒  ▒▓█▓▒░ ░▒▓█▓▒░        ░▒▓█▓▒░            ░▒▓█▓▒░     |
 |     ░▒▓█▓▒░        ░▒▓█▓▒  ▒▓█▓▒░ ░▒▓█▓▒  ▒▓█▓▒░  ▓█▓▒  ▒▓█▓▒░ ░▒▓█▓▒░        ░▒▓█▓▒  ▒▓█▓▒░    ░▒▓█▓▒░      |
 |   ░   ▒▓█▓▒░        ░▒▓█▓▒  ▒▓█▓▒░  ░▒▓██████▓▒░     ▒▓██████▓▒░░▒▓████████▓▒░  ░▒▓██████▓▒░     ░▒▓█▓▒░     |
 |                                                                                                              |
 *______________________________________________________________________________________________________________*
EOF
)

    colors=(40 42 40 43 40 44 40 45 40)
    num_colors=${#colors[@]}
    num_rows=$(echo "$art" | wc -l)
    num_rows=$(($num_rows - 1))
    row=0
    last_char=0

    echo "$art" | while IFS= read -r line; do
      col=0
      while [ $col -lt ${#line} ]; do
        char="${line:$col:1}"

        # Table border
        if [[ "$char" == "*" ]]; then
          printf "\033[0;1m%s" "$char"
          col=$((col + 1))
          continue
        elif [[ "$char" == " "|| $row == $num_rows || $row == 0 || "$char" == '|' || "$char" == "_" ]]; then
          printf "\033[40m%s" "$char"
          col=$((col + 1))
          continue
        fi

        # Inside text
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
    """

    echo """    This program is free software: you can redistribute it and/or modify
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

    printf "\rProgress : [${done_str// /#}${left_str// /-}] ${progress_percent}%%"
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
  --extra-dev-tools    Install auxiliary developer tools.
  --privilege-scripts  Apply privileging to script directories.
  --help               Show this help message.
EOF
    exit 0
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) PARAM_FORCE=1; shift;;
        --extra-dev-tools) INSTALL_DEV_TOOLS=1; shift;;
        --privilege-scripts) PRIVILEGE_SCRIPTS=1; shift;;
        --help) help_function;;
        *) help_function;;
    esac

done

readonly TOTAL_STEPS=10
_progress=0
ProgressBar 0 ${TOTAL_STEPS}

git rev-parse --git-dir > /dev/null 2>&1 || {
    REPO_NAME=$(basename "${GIT_REPO_URL}" .git)
    echo "Not a git repository. Cloning '${REPO_NAME}'..."
    [ -d "${REPO_NAME}" ] && {
        echo "Error: Directory '${REPO_NAME}' already exists. Aborting."
        exit 1
    }
    git clone "${GIT_REPO_URL}" --depth 1
    cd "$PWD/$REPO_NAME"
}

advance_progress

install_nix() {
    echo "Nix not found. Installing Nix..."
    (curl -L https://nixos.org/nix/install | sh) >/dev/null 2>&1
}

source_nix_profile() {
    set +u
    if [ -f "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh" ]; then
        source "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
    elif [ -f "${HOME}/.nix-profile/etc/profile.d/nix.sh" ]; then
        source "${HOME}/.nix-profile/etc/profile.d/nix.sh"
    else
        echo "Warning: Could not find the Nix profile script to source."
        echo "You may need to manually add Nix to your shell's environment."
        return 1
    fi
    set -u
    echo "Successfully sourced nix profile"
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

echo "Installing dependencies with Nix..."
nix develop --command true

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

[[ RAN_LLAC_SETUP_SHELL == 0 || PRIVILEGE_SCRIPTS == 1 ]] && {
    privilege_script_dir "${HOOKS_DIR}" "*.sh"
    privilege_script_dir "${RTL_SCRIPTS_DIR}" "*.sh" "*.py"
    sudo chmod 755 "${HOOKS_DIR}/run_hook.sh"
    sudo chmod 755 "${PRE_COMMIT_DIR}"
    sudo chmod 755 "${PRE_PUSH_SCRIPT}"
    sudo chmod 644 "${PRE_COMMIT_CONFIG_YAML}"
}

advance_progress

get_os() {
    case "$(uname -s)" in
        Linux*) echo "Linux";;
        Darwin*) echo "Mac";;
        FreeBSD*) echo "FreeBSD";;
        CYGWIN*|MINGW*|MSYS_NT*) echo "Windows";;
        *) echo "UNKNOWN:$(uname -s)";;
    esac
}

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    case "$(get_os)" in
        "Linux")
            echo "Targeting Linux distro..."
            command_exists docker && sudo usermod -aG docker "${USER}"
            ;;
        "Mac") echo "Targeting MacOS / Darwin platform";;
        "FreeBSD") echo "Targeting FreeBSD platform";;
        "Windows") echo "Windows is not supported. Aborting setup."; exit 1;;
    esac
}

advance_progress

clone_submodules() {
    git config -f .gitmodules --get-regexp '^submodule\..*\.url' | while read -r key url; do
        path="$(git config -f .gitmodules "${key/.url/.path}")"
        echo "Cloning ${url} -> ${path}"
        git clone --recurse-submodules --depth 1 "${url}" "${path}"
    done
}

[[ ! -d "${PWD}/submodules" || PARAM_FORCE == 1 ]] && {
    git submodule sync --recursive
    git submodule update --init --remote --recursive
    clone_submodules

    (( INSTALL_DEV_TOOLS == 1 )) && {
        echo "Installing Verilator from source..."
        unset VERILATOR_ROOT
        cd "${PWD}/submodules/verilator"
        autoconf
        ./configure
        make -j "$(nproc)"
        sudo make install
        cd "-"
    }
}

advance_progress

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    git config --add safe.directory "${PWD}"
    git config --add --bool push.autoSetupRemote true
    git config core.hooksPath .github/hooks
}

advance_progress

[ ! -d "${VENV_DIR}" ] && {
    echo "Virtual environment not found. Creating one..."
    python3 -m venv --system-site-packages "${VENV_DIR}"
    sudo chown -R "${USER}" "${VENV_DIR}"
}

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

! grep -q "export PYTHONDONTWRITEBYTECODE=1" "${VENV_DIR}/bin/activate" && {
    echo "export PYTHONDONTWRITEBYTECODE=1" >> "${VENV_DIR}/bin/activate"
}

pre-commit clean

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    pre-commit install > /dev/null
    ln -sf "${PRE_COMMIT_CONFIG_YAML}" "${PWD}/.pre-commit-config.yaml" 2>/dev/null
}

advance_progress

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    mkdir -p "${SETUP_CACHE}"
    touch "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE"
}

advance_progress

deactivate
echo "Setup complete"
exit 0
