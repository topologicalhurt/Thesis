#!/usr/bin/env python
"""
------------------------------------------------------------------------
Filename: 	unwrap_veo.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Creates a systemverilog instantiation module representation from
A Synthesized Vivado IP core

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------

"""


import itertools
import os
import argparse as ap
import regex as re

from pathlib import Path

from Scripts.argparse_helpers import str2bool, str2path
from Scripts.consts import CURRENT_DIR, DEFAULT_VEO_LOCATION


def veo(v) -> Path:
    if not v.endswith('.veo'):
        raise ap.ArgumentTypeError('A verilog instantiation file (.veo) is expected')
    return Path(v)


def out(v) -> tuple[bool, Path]:
    """Returns (bool, path) where bool corresponds to if v is a directory (T) or not (F)"""
    if re.match(r'.*\.', v):
        if not v.endswith('.sv') and not v.endswith('.v'):
            raise ap.ArgumentTypeError('The output file must match one of: .v, .sv')
        return False, Path(v)
    return True, Path(v)


def main() -> None:
    parser = ap.ArgumentParser(description=__doc__.strip())
    parser.add_argument('-sv', type=str2bool, default=True,
                     help='Determines if the file output is in systemverilog')
    parser.add_argument('--n', type=veo, default=None,
                help='The module name. Must be supplied')
    parser.add_argument('--d', type=str2path, default=DEFAULT_VEO_LOCATION,
            help='The module directory. This is pre-fixed to the module name location')
    parser.add_argument('--o', type=out, default=(True, CURRENT_DIR),
            help='The output file location')
    args = vars(parser.parse_args())

    if args['n'] is None:
        raise ap.ArgumentTypeError('Must supply the module name')

    n_wo_ext = str(args['n']).strip('.veo')
    veo_location = os.path.join(args['d'], n_wo_ext, args['n'])

    with open(veo_location, 'r') as f:
        match = re.search(
            r'INST_TAG\n((?:.|\n)*)\n\/\/\sINST_TAG_END',
            ''.join(f.readlines())
        )
        module_code = match.group(1)
        if module_code is None:
            raise ValueError('The .veo template looks invalid (couldn\'t match INST_TAG ... INST_TAG_END)')

        raw_text = []

        # Extended SysVerilog‑aware port‑comment matcher
        rx_port = re.compile(r'''
            (?P<dir>input|output|inout)\s+                # direction
            (?P<qual>(?:static|automatic|var|const)\s+)?  # optional qualifiers
            (?P<dtype>                                    # SV data‑type
                wire|logic|reg|bit|byte|shortint|int|longint|integer|
                time|shortreal|real|realtime|chandle|string|event|
                interface(?:\s+\w+)?                      # interface or interface instance
            )
            (?:\s+(?P<signed>signed|unsigned))?           # optional sign
            \s*
            (?:\[\s*(?P<msb>[^\]:]+)\s*:\s*(?P<lsb>[^\]]+)\s*\])?  # optional packed vector
            \s*
            (?P<name>[a-zA-Z_]\w*)                        # signal name
        ''', re.VERBOSE | re.IGNORECASE)

        # Get comments only
        annotations = [match.group(1) if (match := re.search(r'^.*\/\/\s?(.*)$', ln))
                        is not None else None for ln in module_code.splitlines()]
        annotations = [a for a in annotations if a is not None]

        # extract fields
        ports = [m.groupdict() for m in map(rx_port.match, annotations) if m]

        # example grouping: by (dir, has_vector)
        def _key(p):
            return p['dir'], bool(p['msb'])
        groups = itertools.groupby(sorted(ports, key=_key), _key)

        # Outer module wrapper
        raw_text.append(f'module {n_wo_ext} (')
        for _, g in groups:
            params = ['\t']

            g0 = next(g, None)
            g0 = {k : v.strip() if v is not None else ' ' for k, v in g0.items()}

            packed_vec = f'[{g0["msb"]}:{g0["lsb"]}] ' if g0['msb'] != ' ' else ''
            params.append(f'{g0["dir"]}{g0["qual"]}{g0["dtype"]}{g0["signed"]}{packed_vec}')
            params.append(', '.join([p['name'] for p in itertools.chain([g0], g)]))

            params.append(',')
            raw_text.append(''.join(params))

        raw_text.append(');')
        raw_text.append('\nendmodule\n')

        # Inner instantiation
        raw_text = '\n'.join(raw_text)
        raw_text = ''.join(raw_text.rsplit(',', 1)) # replace last occurance of comma with empty string

    is_dir, out_f = args['o']
    if is_dir:
        out_f = os.path.join(out_f, f'{n_wo_ext}{".sv" if args["sv"] else ".v"}')
    else:
        out_f = os.path.join(CURRENT_DIR, out_f)

    with open(out_f, 'w+') as f:
        f.write(raw_text)


if __name__ == '__main__':
    main()
