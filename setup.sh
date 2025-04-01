#!/usr/bin/env bash
set -e

helpFunction()
{
   echo ""
   echo "Usage: $0 --force"
   echo -e "\t--force means the setup script attempts to disregard cache & runs install naively (I.e. from new)"
   exit 0
}

paramForce=0
while [[ $# -gt 0 ]]; do
   case "$1" in
      --force ) paramForce=1
      shift;;
      --help ) helpFunction ;;
      *) helpFunction ;;
   esac
done

PWD=`pwd`
VENV_DIR="$PWD/.venv"
ACT_DIR="/usr/local/bin/"
SETUP_CACHE="$PWD/bin/cache"
RAN_LLAC_SETUP_SHELL=$([[ "$paramForce" -eq 0 && -f "$SETUP_CACHE/.LLAC_SETUP_SHELL_DONE" ]]\
 && echo 1 || echo 0)

if ! (git rev-parse --git-dir > /dev/null 2>&1) &&\
[ "$(git -C "$directory" rev-parse --show-toplevel)" != "$(realpath "$directory")" ]; then
  exit 1
fi

###############
# PRIVILEGING #
###############

if [[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 0 ]]; then
  sudo chown -R "$(whoami)" $PWD
  git config --global --add safe.directory $PWD
  sudo chmod 777 $PWD/.github/hooks/run_hooks.sh
  for subdir in $PWD/.github/hooks/*/;
    do sudo chmod -R 777 $subdir;
  done
fi

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
if [[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 0 ]]; then
  if [ $MACHINE == "Linux" ]; then
    distro="$(lsb_release -d | sed -r 's/^Description:\s*//')"
    distro_n="$(echo "${distro}" | grep -oP "^\w+")"
    distro_con=($distro_n "$(echo "${distro}" | sed -r "s/^${distro_n}\s*//")")
    echo "Targeting ${distro_con[0]}"

    case "${distro}" in
      Debian* | Ubuntu*)

        # Attempt to automatically update package manager ~ no promises
        set +e
        sudo apt -y -q update > /dev/null 2>&1 && sudo apt -y upgrade > /dev/null 2>&1
        set -e

        sudo apt -y -q install python3.11-venv python3-pip > /dev/null
        ;;
      *)
        ;;
    esac
  elif [ $MACHINE == "Mac" ]; then
    sudo chown -R "$(whoami)" "$HOME/Library/Application Support/virtualenv"
  fi
fi

###################
# Github Workflow #
###################

if [[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 0 && !$(command -v act &> /dev/null 2>&1) ]]; then
  echo "Act not installed. Installing..."
  sudo curl --proto '=https' --tlsv1.2 \
  -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh \
  | sudo bash -s -- -b /usr/local/bin
fi

##########
# Python #
##########

source "$VENV_DIR/bin/activate" || exit 1

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Creating one..."
  python3 -m venv "$VENV_DIR"
fi

pip3 install --upgrade pip --quiet
pip3 install -r $PWD/Src/Allocator/Interpreter/requirements.txt --quiet

pre-commit clean

if [[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 0 ]]; then
  pip3 install ruff
  pip3 install pre-commit --quiet
  pre-commit install > /dev/null
  ln -s $PWD/.github/hooks/.pre-commit-config.yaml $PWD/.pre-commit-config.yaml > /dev/null 2>&1
fi

if [[ "${RAN_LLAC_SETUP_SHELL:-1}" -eq 0 ]]; then
  mkdir -p $SETUP_CACHE
  touch $SETUP_CACHE/.LLAC_SETUP_SHELL_DONE
fi
