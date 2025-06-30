#!/usr/bin/env bash

CUR_DIR=$(pwd)
TEST_PATH="$CUR_DIR/tests"
ROOT_PATH=$(git rev-parse --show-toplevel)
VENV_DIR="$ROOT_PATH/.venv"

. "$VENV_DIR/bin/activate"
pytest "$TEST_PATH" -p no:cacheprovider -s
