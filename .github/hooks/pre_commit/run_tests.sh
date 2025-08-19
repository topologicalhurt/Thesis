#!/usr/bin/env bash
set -euo pipefail

cd "$ROOT/Src"

run_pytest() {
	if command -v pytest >/dev/null 2>&1; then
		pytest "$@"
	else
		TEST_DIRS=()
		[[ -d "./Allocator/Interpreter/tests" ]] && TEST_DIRS+=("./Allocator/Interpreter/tests")
		[[ -d "./Scripts/tests" ]] && TEST_DIRS+=("./Scripts/tests")
		python3 -m pytest -p no:cacheprovider -s "${TEST_DIRS[@]}" "$@"
	fi
}

echo -e "\n------ RUNNING TESTS ------\n"
run_pytest "$@"

exit 0
