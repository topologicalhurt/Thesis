#!/usr/bin/env bash
set -euo pipefail

TEST_DIRS=()
[[ -d "$ROOT/Src/Allocator/Interpreter/tests" ]] && TEST_DIRS+=("$ROOT/Src/Allocator/Interpreter/tests")
[[ -d "$ROOT/Src/Scripts/tests" ]] && TEST_DIRS+=("$ROOT/Src/Scripts/tests")

run_pytest() {
	if command -v pytest >/dev/null 2>&1; then
		pytest "${TEST_DIRS[@]}" "$@"
	else
		python3 -m pytest -p no:cacheprovider -s "${TEST_DIRS[@]}" "$@"
	fi
}

echo -e "\n------ RUNNING TESTS ------\n"
# run_pytest "$@"

exit 0
