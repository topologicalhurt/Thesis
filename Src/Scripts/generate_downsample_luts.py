#!/usr/bin/env python
"""
------------------------------------------------------------------------
Filename: 	generate_downsample_luts.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Generates a LUT for fixed-downsampling coeffs.
Works on a variable range of common sampling rates.

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

# TODO's
# (1) Fix / test that the fin / fout parameters work as intended
# (2) Properly initialize the lut w/ all fields (maybe add optional meta field in lut dataclass)


import sys
import functools
import argparse as ap
import numpy as np
import matplotlib.pyplot as plt

from collections.abc import Sequence
from typing import assert_never
from scipy import signal

from Allocator.Interpreter.helpers import pad_lists_to_same_length, underline_matches
from Allocator.Interpreter.dataclass import FLOAT_STR_NPMAP, LUT, BYTEORDER, FILTERTYPE

from Scripts.argparse_helpers import get_action_from_parser_by_name, str2freq, str2path, str2float_in_range, str2posint, str2bitwidth
from Scripts.consts import COMMON_RATES, DOWNSAMPLE_COEFFS_NTAPS, SAMPLE_RATE
from Scripts.hex_utils import DownSamplerLutManager
from Scripts.dataclass import KaiserParameters, KaiserSchematic


def main() -> None:
    global args

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

    parser.add_argument('-tw', '-transition-width',
                    type=functools.partial(str2float_in_range, range(0, 1), lower_inclusive=False, upper_inclusive=False),
                    default=0.01,
                    help='The transition width of the kaiser window after the cutoff point.'
                    ' E.g. a floating point value in the range (0, 1) which effects the "delay" of the cutoff'
                    ' setting this closer to 0 will incur an increasing penalty to both computational & memory peformance'
                    ' Note: default value is 1%% of the nyquist frequency'
                    )

    parser.add_argument('-at', '-attenuation',
                type=functools.partial(str2float_in_range, range(-120, 0), lower_inclusive=False, upper_inclusive=False),
                default=-80.0,
                help='The attenuation threshold (in dB), applied at the main lobe in the kaiser window'
                ' E.g. a floating point value in the range (-120dB, 0dB)'
                ' setting this closer to 0 will incur an increasing penalty to both computational & memory peformance'
                ' Note: default value is -80dB'
                )

    parser.add_argument('-bw', type=str2bitwidth, default=FLOAT_STR_NPMAP.FLOAT32.value,
                        help='The bit width of each value in the LUT (default: float / 32bit)'
                        )

    parser.add_argument('--common', action='store_true', default=False,
                        help='Use common mode to replace -fout with a list of common conversion rates'
                        f' E.g. {COMMON_RATES}.'
                        'prohibitions: -fout (see: -fout)'
                        )

    parser.add_argument('--verbose', action='store_true', default=False,
                    help='Verbose printing mode. Show all debug print statements & stub calls'
                    )

    parser.add_argument('--no-plot', action='store_true', default=False,
                help='Don\'t show a plot of the resulting kaiser window after generating the LUT.'
                'Note: plot is shown by default. Only the first conversion window is plotted.'
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
    for i, (fs_in, fs_out) in enumerate(zip(args['fin'], args['fout'])):
        # Design a stopband kaiser filter for downsampling coeffs.
        D = fs_out / fs_in
        filter_result = design_kaiser_filter(
            D,                                  # Normalized cutoff frequency (I.e. same as the downsample conversion factor)
            args['at'],                         # Attenuation (in dB)
            SAMPLE_RATE,
            transition_width_norm=args['tw'],   # Transition width (value in (0, 1))
            guard_band=0.1,
            filter_type=FILTERTYPE.LOWPASS
        )

        if args['verbose']:
            print(filter_result)

        if not args['no_plot'] and not i:
            plot_kaiser_schematic(filter_result)

        h = filter_result.coeffs
        h = h[:h.size//2] # Only store half the window as the kaiser window is perfectly symmetric
        luts_to_w.append(
            LUT(lut=h,
                endianness=BYTEORDER.BIG,
                bit_width=bw_int, table_sz=((bw_int_bytes * np.size(h)) / 1000),
                lop=None, table_mode=None,
                scale_factor=None,
                fn=design_kaiser_filter, acc_report=None,
                cmd=cmd_line_args
                )
            )

    # Done! Write to .hex file
    hexManager = DownSamplerLutManager(args['dir'])
    for lut in luts_to_w:
        fn = (f'dsd_coeff_{lut.bit_width}'
              )
        hexManager.write_lut_to_hex(fn, lut, ow=True, target_order=BYTEORDER.BIG)


def kaiser_design_parameters(stopband_attenuation_db: float, transition_width_rad: float | None = None,
                           transition_width_norm: float | None = None, sample_rate: int | None = None,
                           transition_width_hz: int | None = None) -> KaiserParameters:
    """# Summary
    Calculate Kaiser window parameters for specified stopband attenuation.

    ## Args:
    stopband_attenuation_db: Desired stopband attenuation (positive dB value)
    transition_width_rad: Transition width in radians
    transition_width_norm: Transition width in normalized frequency (0-1)
    sample_rate: Sample rate (Hz) - needed if using transition_width_hz
    transition_width_hz: Transition width in Hz

    ## Returns:
    KaiserParameters dataclass containing beta, window_length, and other parameters
    """

    As = abs(stopband_attenuation_db)

    # Calculate beta using Kaiser's formula
    # https://tomroelandts.com/articles/how-to-create-a-configurable-filter-using-a-kaiser-window
    if As > 50:
        beta = 0.1102 * (As - 8.7)
    elif As >= 21:
        beta = 0.5842 * (As - 21)**0.4 + 0.07886 * (As - 21)
    else:
        beta = 0

    # Convert transition width to radians if needed
    if transition_width_norm is not None:
        transition_width_rad = transition_width_norm * np.pi
    elif transition_width_hz is not None and sample_rate is not None:
        transition_width_rad = 2 * np.pi * transition_width_hz / sample_rate
    elif transition_width_rad is None:
        # Default: use a reasonable transition width
        transition_width_rad = 0.1  # radians

    # Calculate required window length
    if transition_width_rad > 0:
        N = (As - 8) / (2.285 * transition_width_rad)
        N = int(np.ceil(N))
        # Ensure odd length for symmetric filter
        if N % 2 == 0:
            N += 1
    else:
        N = None

    kaiser_parameter_args = {
            'beta': beta,
            'window_length': N,
            'transition_width_rad': transition_width_rad,
            'transition_width_norm': transition_width_rad / np.pi,
            'transition_width_hz': transition_width_hz,
            'sample_rate': sample_rate,
            'estimated_attenuation': As
    }

    return KaiserParameters(**kaiser_parameter_args)


def design_kaiser_filter(cutoff_freq: float | Sequence[float], stopband_attenuation_db: float, sample_rate: int,
                        transition_width_norm: float = 0.1, guard_band: float = 0,
                        filter_type: FILTERTYPE = FILTERTYPE.BANDSTOP) -> KaiserSchematic:
    """# Summary
    Design a complete Kaiser window filter.
    ## Args:
    cutoff_freq: Cutoff frequency (Hz or normalized [0, 1] or tuple of the cutoff frequencies in bandpass or bandstop mode)
    stopband_attenuation_db: Desired stopband attenuation (positive dB)
    transition_width_norm: Transition width as fraction of Nyquist freq
    guard_band: The guard band (a percentage value normalized [0, 1) to multiply together with nyquist frequency
    sample_rate: Sample rate (Hz)
    filter_type: see: FILTERTYPE dataclass
    plot: Whether to plot frequency response
    ## Returns:
    dict with filter coefficients and parameters
    """
    # Get Kaiser parameters
    params = kaiser_design_parameters(
        stopband_attenuation_db,
        transition_width_norm=transition_width_norm
    )
    beta = params.beta
    N = params.window_length
    print(f'Design Parameters:'
          f'\n\tBeta: {beta:.3f}'
          f'\n\tWindow Length: {N}'
          f'\n\tTransition Width: {transition_width_norm:.3f} (normalized)'
    )
    if guard_band < 0 or guard_band >= 1:
        raise ValueError('The guard band must be a value in [0, 1)')

    # Validate cutoff_freq for bandpass/bandstop filters
    if filter_type in [FILTERTYPE.BANDPASS, FILTERTYPE.BANDSTOP]:
        if not isinstance(cutoff_freq, Sequence) or len(cutoff_freq) != 2:
            raise ValueError(f'{filter_type} filter requires a sequence of two cutoff frequencies')
        if cutoff_freq[0] >= cutoff_freq[1]:
            raise ValueError('First cutoff frequency must be less than second cutoff frequency')
    else:
        if not isinstance(cutoff_freq, (int, float)):
            raise ValueError(f'{filter_type} filter requires a single cutoff frequency')

    # Normalize cutoff frequencies
    nyquist = 0.5 * (1 - guard_band) * sample_rate  # Cutoff frequency is the nyquist frequency, with a guard_band applied
    if filter_type in [FILTERTYPE.BANDPASS, FILTERTYPE.BANDSTOP]:
        # Check if frequencies are already normalized
        if all(f <= 1.0 for f in cutoff_freq):
            cutoff_norm = cutoff_freq
        else:
            cutoff_norm = [f / nyquist for f in cutoff_freq]
        # Validate normalized frequencies
        if any(f >= 1.0 for f in cutoff_norm):
            raise ValueError(f'Cutoff frequencies must be less than Nyquist frequency ({nyquist} Hz)')
    else:
        # Single cutoff frequency
        if isinstance(cutoff_freq, float) and cutoff_freq <= 1.0:
            # Already normalized
            cutoff_norm = cutoff_freq
        else:
            # Frequency in Hz
            cutoff_norm = cutoff_freq / nyquist
        if cutoff_norm >= 1.0:
            raise ValueError(f'Cutoff frequency must be less than Nyquist frequency ({nyquist} Hz)')

    # Create filter using Kaiser window
    match filter_type:
        case FILTERTYPE.LOWPASS | FILTERTYPE.BANDSTOP:
            h = signal.firwin(N, cutoff_norm, window=('kaiser', beta))
        case FILTERTYPE.HIGHPASS | FILTERTYPE.BANDPASS:
            h = signal.firwin(N, cutoff_norm, window=('kaiser', beta), pass_zero=False)
        case _:
            assert_never("filter_type must be 'lowpass', 'highpass', 'bandpass', or 'bandstop'")
    h = h.astype(args['bw'])

    # Analyze the filter
    w, H = signal.freqz(h, worN=8192)
    H_db = 20 * np.log10(np.abs(H) + 1e-12)

    # Find actual stopband attenuation based on filter type
    if filter_type == FILTERTYPE.LOWPASS:
        # Find minimum in stopband
        stopband_start_idx = int(len(w) * (cutoff_norm + transition_width_norm))
        if stopband_start_idx < len(H_db):
            actual_stopband_atten = np.min(H_db[stopband_start_idx:])
        else:
            actual_stopband_atten = np.min(H_db[-100:])  # Last part of spectrum
    elif filter_type == FILTERTYPE.HIGHPASS:
        # Find minimum in stopband (before cutoff)
        stopband_end_idx = int(len(w) * (cutoff_norm - transition_width_norm))
        if stopband_end_idx > 0:
            actual_stopband_atten = np.min(H_db[:stopband_end_idx])
        else:
            actual_stopband_atten = np.min(H_db[:100])  # First part of spectrum
    elif filter_type == FILTERTYPE.BANDPASS:
        # Find minimum in both stopbands
        stopband1_end_idx = int(len(w) * (cutoff_norm[0] - transition_width_norm))
        stopband2_start_idx = int(len(w) * (cutoff_norm[1] + transition_width_norm))
        min1 = np.min(H_db[:max(1, stopband1_end_idx)]) if stopband1_end_idx > 0 else -np.inf
        min2 = np.min(H_db[min(len(H_db)-1, stopband2_start_idx):]) if stopband2_start_idx < len(H_db) else -np.inf
        actual_stopband_atten = max(min1, min2)  # Worst case attenuation
    elif filter_type == FILTERTYPE.BANDSTOP:
        # Find minimum in stopband (between cutoffs)
        stopband_start_idx = int(len(w) * (cutoff_norm[0] + transition_width_norm))
        stopband_end_idx = int(len(w) * (cutoff_norm[1] - transition_width_norm))
        if stopband_start_idx < stopband_end_idx:
            actual_stopband_atten = np.min(H_db[stopband_start_idx:stopband_end_idx])
        else:
            actual_stopband_atten = np.min(H_db)  # Fallback
    else:
        actual_stopband_atten = np.min(H_db)

    kaiser_schematic_args = {
        'coeffs': h,
        'cutoff_norm': cutoff_norm,
        'filter_type': filter_type,
        'measured_stopband_attenuation': actual_stopband_atten,
        'target_stopband_attenuation': -stopband_attenuation_db,
        'frequency_response': (w, H),
        'parameters': params
    }
    return KaiserSchematic(**kaiser_schematic_args)


def compare_stopband_attenuations(attenuations: Sequence[int] = [40, 60, 80, 100],
                                  transition_width: float = 0.05) -> None:
    """Compare different stopband attenuation requirements."""

    print('Kaiser Window Parameters for Different Stopband Attenuations:'
          f'\n{"=" * 70}'
          f"\n{'Attenuation (dB)':<15} {'Beta':<8} {'Window Length':<15} {'Main Lobe Width'}"
          f'\n{"-" * 70}'
          )

    for atten in attenuations:
        params = kaiser_design_parameters(atten, transition_width_norm=transition_width)

        # Estimate main lobe width (approximate)
        main_lobe_width = 4 * np.pi / params['window_length'] if params['window_length'] else 'N/A'

        print(f"{-atten:<15} {params['beta']:<8.3f} {params['window_length']:<15} "
              f'{main_lobe_width:.4f}' if isinstance(main_lobe_width, float) else f'{main_lobe_width}')


def plot_kaiser_schematic(schematic: KaiserSchematic) -> None:
        w, H = schematic.frequency_response
        H_db = 20 * np.log10(np.abs(H) + 1e-12)

        plt.figure(figsize=(12, 8))
        # Plot frequency response
        plt.subplot(2, 1, 1)
        plt.plot(w / np.pi, H_db)
        plt.axhline(schematic.target_stopband_attenuation, color='r', linestyle='--',
                   label=f'Target: {schematic.target_stopband_attenuation} dB')
        plt.axhline(schematic.measured_stopband_attenuation, color='g', linestyle='--',
                   label=f'Actual: {schematic.measured_stopband_attenuation:.1f} dB')

        # Add vertical lines for cutoff frequencies
        if schematic.filter_type in [FILTERTYPE.BANDPASS, FILTERTYPE.BANDSTOP]:
            for i, fc in enumerate(schematic.cutoff_norm):
                plt.axvline(fc, color='orange', linestyle=':',
                           label=f'Cutoff {i+1}: {fc:.3f}' if i < 2 else '')
        else:
            plt.axvline(schematic.cutoff_norm, color='orange', linestyle=':',
                       label=f'Cutoff: {schematic.cutoff_norm:.3f}')

        plt.xlabel('Normalized Frequency (×π rad/sample)')
        plt.ylabel('Magnitude (dB)')
        plt.title(f'Kaiser {schematic.filter_type} Filter - Frequency Response')
        plt.grid(True)
        plt.legend()
        plt.ylim([-100, 5])

        # Plot impulse response
        plt.subplot(2, 1, 2)
        plt.stem(range(schematic.coeffs.size), schematic.coeffs)
        plt.xlabel('Sample')
        plt.ylabel('Amplitude')
        plt.title('Impulse Response')
        plt.grid(True)
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    main()
