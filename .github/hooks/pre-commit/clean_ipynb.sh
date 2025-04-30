#!/bin/bash
set -euo pipefail

# Strip outputs from every staged .ipynb before the commit is recorded.
notebooks=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.ipynb$' || true)

[ -z "$notebooks" ] && exit 0

for nb in $notebooks; do
  [ -f "$nb" ] || continue
  jupyter nbconvert --clear-output --inplace "$nb"
  git add "$nb"                        # restage the cleaned notebook
done
