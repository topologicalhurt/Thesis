#!/bin/bash
set -euo pipefail

# Strip outputs from every staged .ipynb before the commit is recorded.
notebooks=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.ipynb$' || true)

cd $(git rev-parse --show-toplevel) || exit 1
for nb in $notebooks; do
  [ ! git diff --quiet -- "$nb" ] && {
    jupyter nbconvert --clear-output --inplace "$nb"
    git add "$nb"
  }
done
cd - >/dev/null
exit 0
