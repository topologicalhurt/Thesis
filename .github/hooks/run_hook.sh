#!/usr/bin/env bash

set -e

CDIR="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:-.}"

FP="$(realpath "$CDIR/$DIR")"

[[ "$FP" == "$CDIR"/* ]] || exit 1

cd "$FP"

BLACKLIST=("codespell.sh" "verilator.sh" "clean_ipynb.sh")

for f in "$FP"/*.sh; do
  basename "$f" | grep -q -F -f <(printf "%s\n" "${BLACKLIST[@]}") && {
    echo "Skipping blacklisted script: $f"
    continue
  }

  bash "$f" | tee "${DIR}.log" || break
done
