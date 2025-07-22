#!/bin/bash

source "$VENV_DIR/bin/activate"

PY_SCRIPT="$ROOT/Src/Scripts/generate_trig_luts.py"
MEM_DIR="$ROOT/Src/RTL/Static/Math/Trig/mem/"

python3 $PY_SCRIPT $MEM_DIR --all -tan-k -atan-k -sinc-k 0.001 --quantize                 # all, lowest precision, standard bit width
python3 $PY_SCRIPT $MEM_DIR --all -tan-k -atan-k -sinc-k 0.001 -bw 64 -hp 2 --quantize    # all, highest precision, full 64 bit width
python3 $PY_SCRIPT $MEM_DIR --sinc -sinc-k 0.001 -table-mode 1 --quantize                 # non-compact sinc, lowest precision, standard bit width
python3 $PY_SCRIPT $MEM_DIR --sinc -sinc-k 0.001 -table-mode 1 -bw 64 -hp 2 --quantize    # non-compact sinc, highest precision, full 64 bit width

deactivate
