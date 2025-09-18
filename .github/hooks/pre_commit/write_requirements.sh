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

RESOLVE_METHOD="${LOCK_RESOLVE_METHOD:-pypi}"
LOCK_TIMEOUT="${LOCK_TIMEOUT:-10s}"

tmp_lock="$(mktemp)"
if timeout "$LOCK_TIMEOUT" python3 "$ROOT/.github/hooks/pre_commit/lock_requirements.py"\
 --write-txt --update --resolve-method "$RESOLVE_METHOD" > "$tmp_lock"; then
	if [ ! -f "$LOCK_PATH" ] || ! cmp -s "$tmp_lock" "$LOCK_PATH"; then
		mv "$tmp_lock" "$LOCK_PATH"
	else
		rm -f "$tmp_lock"
	fi
else
	echo "[write_requirements] Timed out after $LOCK_TIMEOUT; skipping lock update" >&2
	rm -f "$tmp_lock"
fi

# create_pre_commit_marker
# echo "[write_requirements] Updated $LOCK_PATH"
# add_file_in_pre_commit "$LOCK_PATH"
# echo "[write_requirements] Updated requirements.txt files"
# add_file_in_pre_commit "$ROOT/Src/Allocator/requirements.txt"
# add_file_in_pre_commit "$ROOT/Src/Scripts/requirements.txt"
# add_file_in_pre_commit "$ROOT/docs/Notebook/requirements.txt"
# destroy_pre_commit_marker

deactivate
