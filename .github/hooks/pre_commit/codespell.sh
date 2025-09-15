#!/bin/bash
set -eo pipefail

. "$VENV_DIR/bin/activate"

cd "$ROOT"

IGNORE_REGEX=$(python3 "$ROOT/.github/hooks/pre_commit/codespell_pattern_builder.py")

EXCLUDES=(
  './submodules/*'
  './.venv/*'
  './.git/*'
  './.nix/*'
  './bin/*'
  './Src/*/build/*'
)

prune=()
for pat in "${EXCLUDES[@]}"; do
  prune+=( -path "$pat" -prune -o )
done

find . \( "${prune[@]}" -false \) -o \
( -type f \( -name "*.md" -o -path "*/Scripts/*.py" -o -path "*/Allocator/*.py" \) -print0 \) \
| xargs -0 codespell --skip "submodules,.venv" --ignore-multiline-regex="$IGNORE_REGEX"

deactivate
