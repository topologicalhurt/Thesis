#!/bin/bash
set -eo pipefail

. "$VENV_DIR/bin/activate"
cd "$ROOT"

LOCK_PATH="$ROOT/requirements_lock.json"
	JSON_OUT=$(python3 "$ROOT/.github/hooks/pre_commit/lock_requirements.py" --write-txt --update \
	--resolve-method pypi)
printf '%s
' "$JSON_OUT" > "$LOCK_PATH"
	git add "$LOCK_PATH" || true
	git add "$ROOT/Src/Allocator/requirements.txt" 2>/dev/null || true
	git add "$ROOT/Src/Scripts/requirements.txt" 2>/dev/null || true
	git add "$ROOT/docs/Notebook/requirements.txt" 2>/dev/null || true

deactivate
