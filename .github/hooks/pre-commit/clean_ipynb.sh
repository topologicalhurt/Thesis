#!/bin/bash
set -euo pipefail

# Strip outputs from every staged .ipynb before the commit is recorded.
notebooks=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.ipynb$' || true)

unapplied=0
cd $(git rev-parse --show-toplevel) || exit 1
for nb in $notebooks; do
  base=$(basename "$nb" .ipynb)
  [[ "$base" == *_fixes ]] && {
    echo "Unapplied fixes in ${base}_fixes.ipynb. Please apply (see docs/CONTRIBUTING.md)"
    exit 1
  }
  [ $(grep -q '"output_type":' "$nb")] && {
    jupyter nbconvert --clear-output --to notebook --output "${base}_fixes.ipynb" "$nb"
    echo "Wrote fixes to ${base}_fixes.ipynb. Please apply"
    unapplied=1
  }
done
cd - >/dev/null
exit $unapplied
