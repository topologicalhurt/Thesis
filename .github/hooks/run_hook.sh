#!/usr/bin/env bash

set -eo pipefail

CDIR="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:-.}"

FP="$(realpath "$CDIR/$DIR")"

[[ "$FP" == "$CDIR"/* ]] || exit 1

cd "$FP"

EXIT_CODE=0
for f in "$FP"/*.sh; do
  if ! bash "$f" 2>&1 | show_last_line_inplace "[${f##*/}]: " | tee -a 'pre_commit.log'; then
    EXIT_CODE=1
  fi
done

exit $EXIT_CODE
