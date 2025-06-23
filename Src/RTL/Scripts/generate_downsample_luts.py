#!/usr/bin/env python
"""
Generates a LUT for fixed-downsampling coeffs.
Works on a variable range of common sampling rates.
"""

# TODO's
# (1) Build kaiser window automatically based on user thresholds / tolerances (right now, design is very basic)
# (2) Fix / test that the fin / fout parameters work as intended
# (3) Properly initialize the lut w/ all fields (maybe add optional meta field in lut dataclass)


import sys
import functools
import argparse as ap
import numpy as np
from scipy import signal

from Allocator.Interpreter.helpers import pad_lists_to_same_length, underline_matches
from Allocator.Interpreter.dataclass import INT_STR_NPMAP, LUT, ByteOrder

from RTL.Scripts.argparse_helpers import get_action_from_parser_by_name, str2freq, str2path, str2posint, str2bitwidth
from RTL.Scripts.consts import COMMON_RATES, DOWNSAMPLE_COEFFS_NTAPS, SAMPLE_RATE
from RTL.Scripts.hex_utils import DownSamplerLutManager


def design_audio_downsample_filter(fs_in, fs_out, taps=127):
    fc = 0.45 * fs_out # Cutoff frequency (leaving 10% guard band)
    fc_norm = fc / (fs_in / 2) # Normalized cutoff

    # Design filter (Kaiser window for good audio performance)
    # Beta = 8 gives about -80dB stopband attenuation
    h = signal.firwin(taps, fc_norm, window=('kaiser', 8))

    # Normalize for unity gain at DC
    h = h / np.sum(h)

    return h


def main() -> None:
    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('dir', type=str2path,
                    help='The output directory for the LUTs'
                    )

    parser.add_argument('-fin', type=str2freq, nargs='*', default=[SAMPLE_RATE],
                        help='The frequencies to convert FROM (I.e. downsample FROM) matched orderwise'
                        f' with -fout. Defaults to: {SAMPLE_RATE}'
                    )

    parser.add_argument('-fout', type=str2freq, nargs='*', default=None,
                        help='The frequencies to convert TO (I.e. downsample TO) matched orderwise'
                        f' with -fin. Defaults to: {SAMPLE_RATE // 2}.'
                        ' Note: if -fout is < fin the array will be extended based on the last element to match fin'
                        ' prohibitions: --common (see: --common)'
                        )

    parser.add_argument('-ntaps', type=str2posint, default=DOWNSAMPLE_COEFFS_NTAPS,
                        help='The number of FIR taps to use for the downsampling converter'
                        )

    parser.add_argument('-bw', type=functools.partial(str2bitwidth, is_int=True), default=INT_STR_NPMAP.INT32.value,
                        help='The bit width of each value in the LUT (default: float / 32bit)'
                        )

    parser.add_argument('--common', action='store_true', default=False,
                        help='Use common mode to replace -fout with a list of common conversion rates'
                        f' E.g. {COMMON_RATES}.'
                        'prohibitions: -fout (see: -fout)'
                        )

    args = vars(parser.parse_args())

    bw_int, args['bw'] = args['bw'] # Store the actual integer value of the bit_width in bw_int and the type in args['bw']
    bw_int_bytes = bw_int // 8

    # Supplying -fout and specifying --common is prohibited
    if args['fout'] is not None and args['common']:
        err_invoker = get_action_from_parser_by_name(parser, 'common')
        raise ap.ArgumentError(err_invoker,
                               '--common cannot be supplied alongside -fout. I.e.:'
                               f'\n{underline_matches(" ".join(sys.argv[1:]), ("--common", "-fout"))}'
                               )

    if args['common']:
        args['fout'] = COMMON_RATES

    # If -fout not supplied or supplied but not specified then make it the array of half the input conversion rates by default
    if not args['fout']:
        args['fout'] = [a // 2 for a in args['fin']]

    if len(args['fin']) > len(args['fout']):
        err_invoker = get_action_from_parser_by_name(parser, 'fin')
        raise ap.ArgumentError(err_invoker,
                               'the length of -fin should always be <= the length of -fout'
                               f' I.e. don\'t know how to match {args["fin"]} |-> {args["fout"]}'
        )

    # Since args['fin'] <= args['fout'] this will always pad args['fin'] using it's last element to extend to the same size
    args['fin'], args['fout'] = pad_lists_to_same_length(args['fin'], args['fout'])

    cmd_line_args = ' '.join(sys.argv[2:])
    luts_to_w = []
    for fs_in, fs_out in zip(args['fin'], args['fout']):
        h = design_audio_downsample_filter(fs_in, fs_out)
        h_fixed = np.round(h * 2**(bw_int - 1)).astype(args['bw']) # Quantize to 'bw' sized coeffs
        h_fixed = h_fixed[:h_fixed.size//2] # Only store half the window as the kaiser window is perfectly symmetric
        luts_to_w.append(
            LUT(lut=h_fixed,
                endianness=ByteOrder.BIG,
                bit_width=bw_int, table_sz=((bw_int_bytes * np.size(h_fixed)) / 1000),
                lop=None, table_mode=None,
                scale_factor=None,
                fn=design_audio_downsample_filter, acc_report=None,
                cmd=cmd_line_args
                )
            )

    # Done! Write to .hex file
    hexManager = DownSamplerLutManager(args['dir'])
    for lut in luts_to_w:
        fn = (f'dsd_coeff_{lut.bit_width}'
              )
        hexManager.write_lut_to_hex(fn, lut, ow=True, target_order=ByteOrder.BIG)

if __name__ == '__main__':
    main()
