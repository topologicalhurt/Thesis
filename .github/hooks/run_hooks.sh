#!/usr/bin/env bash

set -e

CDIR="$(cd "$(dirname "$0")" || exit 1 && pwd)"
DIR="${1:-.}"

FP="$(realpath "$CDIR/$DIR")"
if [[ "$FP" != "$CDIR"/* ]]; then
  exit 1
fi

cd "$FP" || exit 1

for f in $FP/*.sh; do
  bash "$f" | tee "${DIR}.log" || break
done
