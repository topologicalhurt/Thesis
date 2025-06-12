#!/usr/bin/env bash

CUR_DIR=$(pwd)
TEST_PATH="$CUR_DIR/tests"

pytest "$TEST_PATH" -p no:cacheprovider
