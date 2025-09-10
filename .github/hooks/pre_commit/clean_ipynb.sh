#!/bin/bash
set -eo pipefail

. "$VENV_DIR/bin/activate"

# Strip outputs from every staged .ipynb before the commit is recorded.
notebooks=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.ipynb$' || true)

cd "$ROOT"

unapplied=0
for nb in $notebooks; do
  base=$(basename "$nb" .ipynb)
  grep -q '"output_type":' "$nb" && {
    jupyter nbconvert "$nb" --clear-output --to notebook
    git add "$nb.ipynb"
    unapplied=1
  }
done

deactivate
exit $unapplied
