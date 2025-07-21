#!/bin/bash
set -eo pipefail

source "$VENV_DIR/bin/activate"

cd "$ROOT"

IGNORE_REGEX=$(python3 "$ROOT/.github/hooks/pre_commit/codespell_pattern_builder.py")
find . \( -name "*.md" -o -path "*/Scripts/*.py" -o -path "*/Allocator/*.py" \) -print0 | \
    xargs -0 codespell --ignore-multiline-regex="$IGNORE_REGEX"

deactivate
