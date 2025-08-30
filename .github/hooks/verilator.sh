#!/bin/bash
set -eo pipefail

# Only run on non WIP branches
echo "$CUR_BRANCH" | grep -Eq "$LENIENT_BRANCHES" || "$VERILATOR_LINT_OFF"=0
[[ "$run_verilator_lint" -eq 1 ]] && {
    find "$ROOT/Src/RTL" -name "*.sv" -or -name "*.svh" \
    | xargs ./submodules/verilator/bin/verilator --lint-only
}

exit 0
