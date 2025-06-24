#!/bin/bash

. .venv/bin/activate

exec codespell --ignore-regex="(https?:\/\/|www\.)(\w+\.)+\w+(\/\w+)+.\w+" \
    --skip "*.sv" "*.svh"
