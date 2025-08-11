#!/bin/bash
set -eo pipefail

# Only run on non WIP branches
echo "$CUR_BRANCH" | grep -Eq "^(.*WIP.*)|(.*research.*)|(devops)|(security)$" && run_verilator_lint=0 || run_verilator_lint=1
[[ "$run_verilator_lint" -eq 1 ]] && {
    find "$ROOT/Src/RTL" -name "*.sv" -or -name "*.svh" \
    | xargs ./submodules/verilator/bin/verilator --lint-only
}

exit 0
