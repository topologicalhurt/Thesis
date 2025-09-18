#!/bin/bash
set -eo pipefail

. "$VENV_DIR/bin/activate"
cd "$ROOT"

# Run only when staged git diff includes relevant Python sources or the lock tool
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  base=HEAD
else
  base=$(git hash-object -t tree /dev/null)
fi

changed=$(git diff --cached --name-only --diff-filter=ACMRTUXB "$base" || true)
relevant=$(printf '%s\n' "$changed" | grep -E '^(Src/|docs/Notebook/).+\.py$' || true)
if [ -z "$relevant" ]; then
  deactivate
  exit 0
fi

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
