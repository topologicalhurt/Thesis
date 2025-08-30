#!/usr/bin/env bash
set -euo pipefail

# Resolve the list of staged files to check with ruff.
# Defaults to staged Python files; if RUFF_TO_CHECK is set, use it as git pathspecs.

command_exists() { command -v "$1" >/dev/null 2>&1; }

if ! command_exists ruff; then
	echo "[ruff] ruff not found in PATH; skipping lint." >&2
	exit 0
fi

declare -a pathspecs
if [[ -n "${RUFF_TO_CHECK:-}" ]]; then
	# Split space-separated pathspecs
	read -r -a pathspecs <<<"${RUFF_TO_CHECK}"
else
	pathspecs=("*.py")
fi

# Collect staged files matching pathspecs
mapfile -t staged_files < <(git diff --name-only --cached -- "${pathspecs[@]}")

if (( ${#staged_files[@]} == 0 )); then
	exit 0
fi

# Run ruff on the staged files
ruff check --fix --show-fixes -- "${staged_files[@]}"
