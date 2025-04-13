#!/usr/bin/env bash
set -e

helpFunction()
{
   echo ""
   echo "Usage: $0 --force"
   echo -e "\t--extra-dev-tools installs auxiliary dev tools that some devs probably don't care for"
   echo -e "\t--force means the setup script attempts to disregard cache & runs install naively (I.e. from new)"
   exit 0
}

paramForce=0
installDevTools=0
while [[ $# -gt 0 ]]; do
   case "$1" in
      --force ) paramForce=1
      shift;;
      --extra-dev-tools ) installDevTools=1
      shift;;
      --help ) helpFunction ;;
      *) helpFunction ;;
   esac
done

PWD=$(pwd)
VENV_DIR="$PWD/.venv"
ACT_DIR="/usr/local/bin/"
SETUP_CACHE="$PWD/bin/cache"

RAN_LLAC_SETUP_SHELL=$([ "$paramForce" -eq 0 ] && [ -f "$SETUP_CACHE/.LLAC_SETUP_SHELL_DONE" ] && echo 1 || echo 0)

git rev-parse --git-dir > /dev/null 2>&1 ||
[ "$(git -C "$directory" rev-parse --show-toplevel)" = "$(realpath "$directory")" ] ||
exit 1

###############
# PRIVILEGING #
###############

[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || {
  sudo chown -R "$(whoami)" "$PWD"
  git config --global --add safe.directory "$PWD"
  sudo chmod 777 "$PWD/.github/hooks/run_hooks.sh"
  find "$PWD/.github/hooks/" -type d -exec sudo chmod -R 777 {} \;
  sudo chmod 644 "$PWD/.github/hooks/.pre-commit-config.yaml"
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

          # Attempt to automatically update package manager ~ no promises
          set +e
          sudo apt -y -q update > /dev/null 2>&1 && sudo apt -y upgrade > /dev/null 2>&1
          set -e

          sudo apt-get -y -q install help2man perl python3 make autoconf g++ flex bison ccache \
          libgoogle-perftools-dev mold numactl perl-doc libfl2 libfl-dev zlibc zlib1g zlib1g-dev > /dev/null
          sudo apt -y -q install python3.11-venv python3-pip > /dev/null
          ;;
      esac
      ;;
    "Mac")
      echo "Targeting MacOS / Darwin platform"
      sudo chown -R "$(whoami)" "$HOME/Library/Application Support/virtualenv"
      ;;
  esac
}

#######
# GIT #
#######

[[ ! -d "$PWD/submodules" || "$paramForce" -eq 1 ]] && {
  mkdir -p "$PWD/submodules"
  git submodule update --init --remote

  [ "$installDevTool" -eq 1 ] && {
    Setup verilator
    unset VERILATOR_ROOT
    cd "$PWD/submodules/verilator" || exit 1
    autoconf
    ./configure
    make -j `nproc`
    sudo make install
    cd - || exit 1
  }
}

###################
# Github Workflow #
###################

git config --global --add --bool push.autoSetupRemote true

[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 1 ] || command -v act &> /dev/null || {
  echo "Act not installed. Installing..."
  sudo curl --proto '=https' --tlsv1.2 \
  -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh \
  | sudo bash -s -- -b /usr/local/bin
}

##########
# Python #
##########

. "$VENV_DIR/bin/activate" || exit 1

[ -d "$VENV_DIR" ] || {
  echo "Virtual environment not found. Creating one..."
  python3 -m venv "$VENV_DIR"
}

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
