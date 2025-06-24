#!/usr/bin/env bash
set -eo pipefail

# TODO's
# (1) Ensure works for fresh docker image
# (2) Ensure works for mac, debian, ubuntu at a minimum
# (3) Use NIX
# (4) Switch to using packages directly (I.e. dpkg) rather than apt


helpFunction()
{
   echo ""
   echo "Usage: $0 --force --extra-dev-tools"
   echo -e "\t--privilege-scripts will apply privileging to script dirs"
   echo -e "\t--extra-dev-tools installs auxiliary dev tools that aren't needed for non-developers"
   echo -e "\t--force means the setup script attempts to disregard cache & runs install naively (I.e. from new)"
   exit 0
}

paramForce=0
installDevTools=0
pScripts=0
while [[ $# -gt 0 ]]; do
   case "$1" in
      --force ) paramForce=1
      shift;;
      --extra-dev-tools ) installDevTools=1
      shift;;
      --privilege-scripts ) pScripts=1
      shift;;
      --help ) helpFunction ;;
      *) helpFunction ;;
   esac
done

PWD=$(pwd)
VENV_DIR="$PWD/.venv"
ACT_DIR="/usr/local/bin/"
SETUP_CACHE="$PWD/bin/cache"

HOOKS_DIR="$PWD/.github/hooks"
RTL_SCRIPTS_DIR="$PWD/Src/RTL/Scripts"
RUN_HOOKS_SCRIPT="$HOOKS_DIR/run_hooks.sh"
PRE_COMMIT_CONFIG_YAML="$PWD/.github/hooks/.pre-commit-config.yaml"
PRE_COMMIT_DIR="$PWD/.github/hooks/pre_commit"
PRE_PUSH_SCRIPT="$PWD/.github/hooks/pre-push"

RAN_LLAC_SETUP_SHELL=$([ "$paramForce" -eq 0 ] && [ -f "$SETUP_CACHE/.LLAC_SETUP_SHELL_DONE" ] && echo 1 || echo 0)

git rev-parse --git-dir > /dev/null 2>&1 ||
[ "$(git -C "$directory" rev-parse --show-toplevel)" = "$(realpath "$directory")" ]

###############
# PRIVILEGING #
###############

privilegeScriptDir() {
  local target_dir="$1"
  local patterns_ref="${2}[@]"
  local script_patterns=("${!patterns_ref}")

  # Root script directory gets 755 permission (r+w+e)
  find "$target_dir" -type d -exec sudo chmod -R 755 {} \;

  local include_patterns=()
  for pattern in "${script_patterns[@]}"; do
    [ ${#include_patterns[@]} -gt 0 ] && {
      include_patterns+=("-o")
    }
    include_patterns+=("-name" "$pattern")
  done

  # all is every script matching a pattern
  # script_p is every script with a shebang in it's header (indicating it should be priveleged)
  # normal_p is every script in All that is NOT in script_p (set difference of all, script_p)
  all=$(find "$target_dir" -type f \( "${include_patterns[@]}" \))
  script_p=$(find "$target_dir" -type f -exec awk 'NR==1 && /^#!/ {print FILENAME}' {} \;)
  normal_p=$(comm -23 <(sort <<< "$all") <(sort <<< "$script_p"))

  # Regular files (normal_p) get 644 permissions
  # Privileged files (script_p) get more advanced permissions
  [ -n "$normal_p" ] && {
    echo "$normal_p" | xargs -I {} sudo chmod 644 {}
  }

  [ -n "$script_p" ] && {
    echo "$script_p" | xargs -I {} sudo chmod 755 {}
  }
}

[[ ("$RAN_LLAC_SETUP_SHELL" -eq 0) || ("$pScripts" -eq 1) ]] && {
  git config --add safe.directory "$PWD"
  git_hook_ptrns=( "*.sh" )
  rtl_script_ptrns=( "*.sh" "*.py" )
  privilegeScriptDir "$HOOKS_DIR" "git_hook_ptrns"
  privilegeScriptDir "$RTL_SCRIPTS_DIR" "rtl_script_ptrns"
  sudo chmod 755 "$RUN_HOOKS_SCRIPT"
  sudo chmod 755 "$PRE_COMMIT_DIR"
  sudo chmod 755 "$PRE_PUSH_SCRIPT"
  sudo chmod -x "$PRE_COMMIT_CONFIG_YAML"
}

###############
# SYS TARGETS #
###############

unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    MSYS_NT*)   MACHINE=MSys;;
    *)          MACHINE="UNKNOWN:${unameOut}"
esac

# Apply OS specific patches
[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || {
  case "$MACHINE" in
    "Linux")
      distro="$(lsb_release -d | sed -r 's/^Description:\s*//')"
      distro_n="$(echo "${distro}" | grep -oP "^\w+")"
      distro_con=($distro_n "$(echo "${distro}" | sed -r "s/^${distro_n}\s*//")")
      echo "Targeting linux distro: ${distro_con[0]}"

      case "${distro}" in
        Debian* | Ubuntu*)
          sudo add-apt-repository ppa:deadsnakes/ppa
          sudo apt-get -y -q install gcc help2man perl python3.11 make autoconf g++ flex bison ccache \
          libgoogle-perftools-dev mold numactl perl-doc libfl2 libfl-dev zlib1g zlib1g-dev \
          python3.11-venv python3-pip verilator > /dev/null

          # Copied from the docker debian install guide
          # https://docs.docker.com/engine/install/debian/
          sudo apt-get update
          sudo apt-get install ca-certificates curl
          sudo install -m 0755 -d /etc/apt/keyrings
          sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
          sudo chmod a+r /etc/apt/keyrings/docker.asc

          # Add the repository to Apt sources:
          echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
            $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

          sudo apt-get -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

          # Add current user to docker group for Docker permissions
          sudo usermod -aG docker $USER

          sudo apt-get update

          ;;
      esac
      ;;
    "Mac")
      echo "Targeting MacOS / Darwin platform"

      brew install gcc help2man perl python@3.11 make autoconf flex bison ccache gperftools mold zlib verilator
      ;;
  esac
}

#######
# GIT #
#######

clone_submodules () {
  git config -f .gitmodules --get-regexp '^submodule\..*\.url$' |
  while read -r key url; do
      path=$(git config -f .gitmodules "${key/.url/.path}")
      echo "Cloning ${url} -> ${path}"
      git clone --recurse-submodules --depth 1 "${url}" "${path}"
  done
}

[[ ! -d "$PWD/submodules" || "$paramForce" -eq 1 ]] && {
  git submodule sync
  git submodule update --init --remote
  clone_submodules

  [ "$installDevTools" -eq 1 ] && {
    unset VERILATOR_ROOT
    cd "$PWD/submodules/verilator"
    autoconf
    ./configure
    make -j `nproc`
    sudo make install
    cd -
  }
}

###################
# Github Workflow #
###################

[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || command -v act &> /dev/null || {
  echo "Act not installed. Installing..."
  sudo curl --proto '=https' --tlsv1.2 \
  -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh \
  | sudo bash -s -- -b /usr/local/bin
}


[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || {
  git config --add --bool push.autoSetupRemote true
  git config core.hooksPath .github/hooks
}

##########
# Python #
##########

[ -d "$VENV_DIR" ] || {
  echo "Virtual environment not found. Creating one..."
  python3 -m venv "$VENV_DIR"
  pip3 install -e ./Src --quiet
  pip3 install -u pytest --quiet
}

. "$VENV_DIR/bin/activate"
export PYTHONDONTWRITEBYTECODE=1

pip3 install --upgrade pip --quiet
pip3 install -r "$PWD/Src/Allocator/Interpreter/requirements.txt" --quiet

pre-commit clean

[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || {
  pip3 install ruff codespell pre-commit --quiet
  pre-commit install > /dev/null
  ln -sf "$PWD/.github/hooks/.pre-commit-config.yaml" "$PWD/.pre-commit-config.yaml" 2>/dev/null
}

# Create cache marker when done with first-time setup
[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || {
  mkdir -p "$SETUP_CACHE"
  touch "$SETUP_CACHE/.LLAC_SETUP_SHELL_DONE"
}
