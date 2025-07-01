#!/usr/bin/env bash
set -euo pipefail

PARAM_FORCE=0
INSTALL_DEV_TOOLS=0
PRIVILEGE_SCRIPTS=0

readonly PWD="$(pwd)"
readonly VENV_DIR="${PWD}/.venv"
readonly SETUP_CACHE="${PWD}/bin/cache"
readonly HOOKS_DIR="${PWD}/.github/hooks"
readonly RTL_SCRIPTS_DIR="${PWD}/Src/Scripts"
readonly PRE_COMMIT_CONFIG_YAML="${PWD}/.github/hooks/.pre-commit-config.yaml"
readonly PRE_COMMIT_DIR="${PWD}/.github/hooks/pre_commit"
readonly PRE_PUSH_SCRIPT="${PWD}/.github/hooks/pre-push"

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

readonly RAN_LLAC_SETUP_SHELL=$([ "${PARAM_FORCE}" -eq 0 ] && [ -f "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE" ] && echo 1 || echo 0)

command_exists nix || {
    echo "Nix not found. Installing Nix..."
    curl -L https://nixos.org/nix/install | sh

    # Source the Nix profile script, trying common locations
    if [ -f "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh" ]; then
        # shellcheck source=/dev/null
        . "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
    elif [ -f "${HOME}/.nix-profile/etc/profile.d/nix.sh" ]; then
        # shellcheck source=/dev/null
        . "${HOME}/.nix-profile/etc/profile.d/nix.sh"
    else
        echo "Warning: Could not find the Nix profile script to source."
        echo "You may need to manually add Nix to your shell's environment."
    fi
}

readonly NIX_CONFIG_DIR="${HOME}/.config/nix"
readonly NIX_CONFIG_FILE="${NIX_CONFIG_DIR}/nix.conf"
grep -q "experimental-features = nix-command flakes" "${NIX_CONFIG_FILE}" 2>/dev/null || {
    mkdir -p "${NIX_CONFIG_DIR}"
    echo "experimental-features = nix-command flakes" >> "${NIX_CONFIG_FILE}"
}

echo "Installing dependencies with Nix..."
nix develop --command true

readonly GIT_REPO_URL="https://github.com/topologicalhurt/Thesis.git"

git rev-parse --git-dir > /dev/null 2>&1 || {
    readonly REPO_NAME=$(basename "${GIT_REPO_URL}" .git)
    echo "Not a git repository. Cloning '${REPO_NAME}'..."
    [ -d "${REPO_NAME}" ] && {
        echo "Error: Directory '${REPO_NAME}' already exists. Aborting."
        exit 1
    }
    git clone "${GIT_REPO_URL}" --depth 1
    cd "${REPO_NAME}"
    echo "Repository cloned. Re-executing setup script..."
    exec "./setup.sh" "$@"
}

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

(( RAN_LLAC_SETUP_SHELL == 0 || PRIVILEGE_SCRIPTS == 1 )) && {
    privilege_script_dir "${HOOKS_DIR}" "*.sh"
    privilege_script_dir "${RTL_SCRIPTS_DIR}" "*.sh" "*.py"
    sudo chmod 755 "${HOOKS_DIR}/run_hook.sh"
    sudo chmod 755 "${PRE_COMMIT_DIR}"
    sudo chmod 755 "${PRE_PUSH_SCRIPT}"
    sudo chmod 644 "${PRE_COMMIT_CONFIG_YAML}"
}

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

clone_submodules() {
    git config -f .gitmodules --get-regexp '^submodule\..*\.url$' |
    while read -r key url; do
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

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    git config --add safe.directory "${PWD}"
    git config --add --bool push.autoSetupRemote true
    git config core.hooksPath .github/hooks
}

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

(( RAN_LLAC_SETUP_SHELL == 0 )) && {
    mkdir -p "${SETUP_CACHE}"
    touch "${SETUP_CACHE}/.LLAC_SETUP_SHELL_DONE"
}

deactivate
echo "Setup complete"
exit 0
