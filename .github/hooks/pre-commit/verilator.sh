#!/bin/bash

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Only run on non WIP branches
echo "$BRANCH" | grep -Eq "^.*WIP.*$" && run_verilator_lint=0 || run_verilator_lint=1
[[ "$run_verilator_lint" -eq 1 ]] && {
    find ./Src/RTL -name "*.sv" -or -name "*.svh" \
    | xargs ./submodules/verilator/bin/verilator --lint-only
}

exit 0
