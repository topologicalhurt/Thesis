#!/bin/bash
set -eo pipefail

. "$VENV_DIR/bin/activate"

cd "$ROOT"

IGNORE_REGEX=$(python3 "$ROOT/.github/hooks/pre_commit/codespell_pattern_builder.py")

EXCLUDES=(
  'submodules'
  '.venv'
  '.git'
  '.nix'
  'bin'
  'build'
  'RTL.*'
  "$(basename "$VENV_DIR")"
)

prune=()
for dname in "${EXCLUDES[@]}"; do
  prune+=( -type d -name "$dname" -prune -o )
done

find . \( "${prune[@]}" -false \) -o \
  \( -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.sv" \) -print0 \) \
| xargs -0 codespell --ignore-multiline-regex="$IGNORE_REGEX"

deactivate
