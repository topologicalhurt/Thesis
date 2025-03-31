#!/usr/bin/env bash
set -e

PWD=`pwd`
VENV_DIR="$PWD/.venv"
ACT_DIR="/usr/local/bin/"

if ! (git rev-parse --git-dir > /dev/null 2>&1) &&\
[ "$(git -C "$directory" rev-parse --show-toplevel)" != "$(realpath "$directory")" ]; then
  exit 1
fi

unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    MSYS_NT*)   MACHINE=MSys;;
    *)          MACHINE="UNKNOWN:${unameOut}"
esac

sudo chown -R "$(whoami)" $PWD
if [ $MACHINE == "Mac" ]; then
  sudo chown -R "$(whoami)" "$HOME/Library/Application Support/virtualenv"
fi

###################
# Github Workflow #
###################

git config --global --add safe.directory $PWD

if ! command -v act &> /dev/null; then
  echo "Act not installed. Installing..."
  sudo curl --proto '=https' --tlsv1.2 \
  -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh \
  | sudo bash -s -- -b /usr/local/bin
fi

##########
# Python #
##########

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Creating one..."
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

sudo -H pip3 install --upgrade pip --quiet
sudo -H pip3 install -r $PWD/Src/Allocator/Interpreter/requirements.txt --quiet

pip3 install pre-commit --quiet
pre-commit install
ln -s $PWD/.github/hooks/.pre-commit-config.yaml $PWD/.pre-commit-config.yaml
pre-commit clean

sudo chmod 777 $PWD/.github/hooks/run_hooks.sh
for subdir in $PWD/.github/hooks/*/;
  do sudo chmod -R 777 $subdir;
done
