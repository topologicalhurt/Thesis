#!/bin/bash
set -euo pipefail

source "$VENV_DIR/bin/activate"

PY_SCRIPT="$ROOT/Src/Scripts/generate_trig_luts.py"
MEM_DIR="$ROOT/Src/RTL/Static/Math/Trig/mem/"

python3 $PY_SCRIPT $MEM_DIR 'Q0.23' --sin --cos --sinc -sinc-k 0.001                                    # lowest precision, standard bit width, [-1, 1) range
python3 $PY_SCRIPT $MEM_DIR 'Q2.21' --acos                                                              # lowest precision, standard bit width, [pi, 0] range
python3 $PY_SCRIPT $MEM_DIR 'Q1.22' --asin --atan -atan-k 0.001                                         # lowest precision, standard bit width, [-pi/2, pi/2] range
python3 $PY_SCRIPT $MEM_DIR 'Q8.15' --tan -tan-k 0.001                                                  # lowest precision, standard bit width, choose tradeoff wisely

python3 $PY_SCRIPT $MEM_DIR 'Q0.52' --sin --cos --sinc -sinc-k 0.001 -bw 64 -prec-mode 'HIGHP'          # highest precision, full 64 bit width
python3 $PY_SCRIPT $MEM_DIR 'Q2.50' --acos -bw 64 -prec-mode 'HIGHP'                                    # highest precision, full 64 bit width
python3 $PY_SCRIPT $MEM_DIR 'Q1.51' --asin --atan -atan-k 0.001 -bw 64 -prec-mode 'HIGHP'               # highest precision, full 64 bit width
python3 $PY_SCRIPT $MEM_DIR 'Q16.36' --tan -tan-k 0.001 -bw 64 -prec-mode 'HIGHP'                       # highest precision, full 64 bit width, 16 bit integer part, 36 bit floating
python3 $PY_SCRIPT $MEM_DIR 'Q8.44' --tan -tan-k 0.001 -bw 64 -prec-mode 'HIGHP'                        # highest precision, full 64 bit width, 8 bit integer part, 44 bit floating

python3 $PY_SCRIPT $MEM_DIR 'Q0.23' --sinc -sinc-k 0.001 -table-mode 'MED' -prec-mode 'LOWP'            # non-compact sinc, lowest precision, standard bit width
python3 $PY_SCRIPT $MEM_DIR 'Q0.52' --sinc -sinc-k 0.001 -table-mode 'MED' -bw 64 -prec-mode 'HIGHP'    # non-compact sinc, highest precision, full 64 bit width

deactivate
