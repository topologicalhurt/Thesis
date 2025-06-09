"""
Writes a generic LUT table into a .hex file
"""


import os
import sys
import datetime as dt

from dataclasses import asdict
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Allocator.Interpreter.dataclass import LUT
from Allocator.Interpreter.helpers import float64_to_hex


HEADER ='// Coefficient memory for {fn}'
'\n// ----------------------------------------------'
'\n//   Bits per coeff.:          {bit_width}'
'\n//   Table mode:               {table_mode}'
'\n//   Table size:               {table_sz}kB'
'\n//   LOP (level of precision): {lop}'
'\n//   Effective scaling factor: {q_multiplier}'
'\n//   Measured avg. accuracy:   {avg_acc}'
'\n//   Min accuracy:             {min_acc}'
'\n//   Max accuracy:             {max_acc}'
'//\n'
'\n// Each line contains a value (coeff.) corresponding to the function: {fn}'
'\n// File generated @ {ts}'
'\n//\n//'


def write_lut_to_hex(fp: Path, fn: str, lut: LUT, ow: bool=False) -> None:
    """# Summary

    Writes a lut to a .hex file at the specified file path &
    with the specified name

    ## Args:
        fp (Path): file path
        fn (str): name
        lut (LUT): lut (see: LUT dataclass)
        ow (bool): overwrite files with same name?
    """
    _, ext = os.path.splitext(fn)
    if not ext:
        fn += '.hex'
    elif ext != '.hex':
        raise ValueError('Lut to hex only supports .hex file extensions')

    file_path = os.path.join(fp, fn)
    if not ow and os.path.exists(file_path):
        raise FileExistsError(f'File already exists at location: {file_path}')

    header = HEADER
    f_map = asdict(lut)
    f_map['fn'] = f_map['fn'].__name__
    f_map['lop'] = f_map['lop'].name.lower()
    f_map['table_mode'] = f_map['table_mode'].name.lower()
    f_map['ts'] = dt.datetime.now()
    acc_report = f_map.pop('acc_report')
    f_map['avg_acc'] = acc_report['avg_acc']
    f_map['min_acc'] = acc_report['min_acc']
    f_map['max_acc'] = acc_report['max_acc']
    f_map['q_multiplier'] = (lut.lop.value + 1) * (1 / (2**lut.table_mode.value))
    header = header.format_map(f_map)

    with open(file_path, 'w') as f:
        f.write(header)
        for entry in lut.lut:
            # TODO: support other float types too
            f.write(f'\n{float64_to_hex(entry)}')
