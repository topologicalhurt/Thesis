#!/usr/bin/env bash

set -e

CDIR="$(cd "$(dirname "$0")" || exit 1 && pwd)"
DIR="${1:-.}"

FP="$(realpath "$CDIR/$DIR")"

[[ "$FP" == "$CDIR"/* ]] || exit 1

cd "$FP" || exit 1

BLACKLIST=("codespell.sh")

for f in "$FP"/*.sh; do
  basename "$f" | grep -q -F -f <(printf "%s\n" "${BLACKLIST[@]}") && {
    echo "Skipping blacklisted script: $f"
    continue
  }

  bash "$f" | tee "${DIR}.log" || break
done
