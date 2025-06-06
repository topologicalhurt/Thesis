"""
Generates a LUT for various trig functions (sin, cos, tan, asin, acos, atan)
with variable precision, size & options to use a heuristic to determine
the 'best' fit automatically
"""

# TODO's:
# 1. Option to automatically determine ideal size based on threshold detector (like atan, tan)
# 2. Fix atan so it can generate a quarter table LUT as well
# 3. Refactor into the allocator itself (to dynamically generate LUT's based on signal functions)


import argparse as ap
import numpy as np
import regex as re
import sys
import os
import functools
import itertools

from collections.abc import Sequence, Callable
from typing import assert_never

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Allocator.Interpreter.dataclasses import ExtendedEnum
from Allocator.Interpreter.helpers import str2enumval, bools2bitstr, eval_arithmetic_str_unsafe, str2path, pairwise,\
get_action_from_parser_by_name, underline_matches
from dataclasses import TRIGLUTDEFS, TRIGLUTS, TRIGFOLD, TRIGPREC


def bram(v: int | str) -> int:
    if isinstance(v, str):
        v = int(eval_arithmetic_str_unsafe(v))
    if isinstance(v, int):
        if v <= 4:
            raise ap.ArgumentTypeError('bram must hold at least one double (sizeof(double) = 4)')
        v = np.log2(v) - 2 # Convert to table width, - 2 as units are in bytes
        return int(np.ceil(v))


def highp(v: str) -> ExtendedEnum:
    if v in TRIGLUTDEFS:
        return str2enumval(v, TRIGLUTDEFS)
    return str2enumval(v, TRIGPREC)


def main() -> None:
    """# Summary

    Entry-point into lut generator. Run this script with the -h option for help.
    """
    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('-bram', type=bram, default=bram(1024),
                        help='The maximum allowable bram (I.e. if in quarter table mode table is of size'
                         ' requested_bram / 4)'
                       )

    parser.add_argument('out', type=str2path,
                        help='The output directory for the LUTs'
                        )

    qt_enum_description = ''.join(TRIGFOLD.__doc__.strip().splitlines())
    qt_enum_description = re.sub(r'\s{2,}', ' ', qt_enum_description)
    qt_enum_description = qt_enum_description.removeprefix('# Summary Enum corresponding to ')
    parser.add_argument('-qt', type=functools.partial(str2enumval, target_enum=TRIGFOLD),
                         default=TRIGFOLD.HIGH,
                         help='Over which period all LUT\'s will be built E.G. a value or field from either:'
                         f' {TRIGFOLD.fields()} | {TRIGFOLD.values()}.'
                         f' The following description might proove valuable: "{qt_enum_description}"'
                        )

    parser.add_argument('-k', type=float,
                        help='A floating point threshold value which determines the error tolerance for all trig functions'
                        ' NOTE: this will not be applied to tan & atan (see: -tan-k, -atan-k)'
                        )

    parser.add_argument('-excl-auto', type=functools.partial(str2enumval, target_enum=TRIGLUTS),
                        nargs='+', default=None,
                        help='A list of values to exclude from auto mode (see: --auto)'
                        ' prohibitions: -tan-k (see: -tan-k) -atan-k (see: -atan-k)'
                        )

    parser.add_argument('-hp', type=highp, nargs='*', default=None,
                        help=f'A list of trig values I.e. {TRIGLUTDEFS.fields()} (applies to all values if none provided)'
                        ' to apply high precision mode to OR a list of trig values & explicit precision mode to use'
                        ' E.g. -hp cos medp sin medp tan highp'
                        ' For example, if -qt (see: -qt) is in the highest mode [quarter table mode]'
                        ' then the default behaviour is to also reduce the LUT size'
                        ' by a factor of 4. In hp mode the requested table size remains the same (effective x4 oversampling)'
                        ' meaning it operates in a higher mode of precision.'
                        ' If a value is explicitly provided & qt differs E.g. cos medp then the factors are multiplied'
                        ' to size the table. That is: -qt high -hp med'
                        ' => a quarter table lookup method is used for half the period of the function (effective x2 oversampling)'
                        )

    parser.add_argument('-tan-k', type=float, default=0.05,
                        help='A floating point threshold value which determines the error tolerance for tan'
                        ' prohibitions: -excl-auto (see: -excl-auto)'
                        )

    parser.add_argument('-atan-k', type=float, default=0.1,
                        help='A floating point threshold value which determines the error tolerance for atan'
                        ' prohibitions: -excl-auto (see: -excl-auto)'
                        )

    parser.add_argument('--auto', action='store_true', default=False,
                        help='Sets auto-mode to on (generate all rec. luts & find ideal table sizes based on global threshold.)'
                        ' This is done by using the newton raphson method or a known bound'
                        ' dependencies: -k (see: -k)'
                        )

    parser.add_argument('--sin', action='store_true', default=False,
                        help='Creates a sin LUT'
                        )

    parser.add_argument('--cos', action='store_true', default=False,
                        help='Creates a cos LUT. Not turned on by default.'
                        )

    parser.add_argument('--tan', action='store_true', default=False,
                        help='Creates a tan LUT'
                        )

    parser.add_argument('--asin', action='store_true', default=False,
                        help='Creates an asin (arcsin) LUT'
                        )

    parser.add_argument('--acos', action='store_true', default=False,
                        help='Creates an acos (arccos) LUT. Not turned on by default.'
                        )

    parser.add_argument('--atan', action='store_true', default=False,
                        help='Creates an atan (arctan) LUT'
                        )

    args = vars(parser.parse_args())

    NON_FLAGS = [action.option_strings for action in parser._actions]
    NON_FLAGS = [opt.removeprefix('-').replace('-', '_') for opt in
                 itertools.chain.from_iterable(NON_FLAGS)
                 if not opt.startswith('--')] # Excl. flags
    NON_FLAGS.extend([action.dest for action in parser._get_positional_actions()]) # Excl. positionals
    TRIG_LUTS = TRIGLUTS(**{k : 1 for k in TRIGLUTDEFS.fields()})
    N_TABLE_ENTRIES = 1 << args['bram']

    trig_args = {k : v for k, v in args.items() if k not in NON_FLAGS}
    if sum(trig_args.values()) == 0:
        trig_opts = (1 << len(trig_args)) - 1
        trig_opts ^= (TRIG_LUTS.COS.value | TRIG_LUTS.ACOS.value) # Don't generate both acos & asin / cos & sin lut's unless explicitly specified
    else:
        trig_opts = bools2bitstr(*trig_args.values())

    if args['hp'] is not None and not args['hp']:
        # If hp parameter provided, but nothing specified, represent all functions as highest precision by default
        args['hp'] = {k: TRIGPREC.HIGHP for k in TRIGLUTDEFS.fields()}
    else:
        # If hp parameter provided check that each trig value is adjacent to a precision arg
        if len(args['hp']) % 2 != 0:

            err_invoker = get_action_from_parser_by_name(parser, 'hp')
            err_msg = [val.name for val in args['hp']]
            last_w = err_msg[-1]
            err_msg.append('*missing value*')
            err_msg = ' '.join(err_msg)
            last_w_index = err_msg.rindex(last_w)
            raise ap.ArgumentError(err_invoker,
                                   '-hp takes <trig function> <precision mode> pairs as argument'
                                   ' but the argument length was odd. I.e.:'
                                   f'\n{underline_matches(err_msg, last_w, start_index=last_w_index)}'
                                   )

        for trig_v, pmode in pairwise(args['hp']):
            if not isinstance(trig_v, TRIGLUTDEFS) or not isinstance(pmode, TRIGPREC):
                err_invoker = get_action_from_parser_by_name(parser, 'hp')
                err_msg = ' '.join([val.name for val in args['hp']])
                raise ap.ArgumentError(err_invoker,
                        '-hp takes <trig function> <precision mode> pairs as argument'
                        ' but a pair was out of order. I.e.:'
                        f'\n{underline_matches(err_msg, (trig_v.name, pmode.name))}'
                        )

    if args['excl_auto'] and args['hp'] and set(args['excl_auto']).intersection(args['hp'].values()):
        err_invoker = get_action_from_parser_by_name(parser, 'excl_auto')
        raise ap.ArgumentError(err_invoker,
                               'Arguments specified in excl must not also appear in hp'
                               ' (can\'t simultaneously )'
                               )

    if trig_opts & (TRIG_LUTS.SIN.value | TRIG_LUTS.COS.value):
        """
        sin(-x) = -sin(x)
        => x |-> [0, pi]

        The 2nd observation is that:
        sin(x) 0 <= x <= pi / 2 ~looks~ like a flipped version of sin(x) pi/2 <= x <= pi

        To show this:
        sin(x + pi/2) is the part we want to show is horizontally flipped
        d/dx sin(x + pi/2) = d/dx cos(x) = -sin(x)
        sin(x) + (-sin(x)) = 0
        => It is horizontally flipped => x |-> [0, pi/2]
        """
        match args['qt']:
            case TRIGFOLD.HIGH:
                stop = np.pi / 2
                sz = N_TABLE_ENTRIES >> 2
            case TRIGFOLD.MEDIUM:
                raise NotImplementedError('Half table not yet supported')
            case TRIGFOLD.LOW:
                stop = np.pi * 2
                sz = N_TABLE_ENTRIES
            case _:
                assert_never(args['qt'])

        phi = np.linspace(0, stop, sz, dtype=np.double)

    if trig_opts & TRIG_LUTS.TAN.value:
        """
        tan(-x) = -tan(x)
        => x |-> [0, pi/2)

        tan(x) = 1 / tan(0.5 * pi - x)
        I.e. if pi/4 <= x < pi/2
        let u = 0.5 * pi - x => u |-> (0, pi/4]
        => we can recover the interval x \in [pi/4, pi/2) by:
        1 / tan(0.5 * pi - u)

        => x |-> [0, pi/4]

        To find err within some threshold, k, consider:
        M.V.T states: tan(x_i + 1) - tan(x_i) = h * d/dx tan(x) = h * sec^2(x)
        To ensure the error is always <= k

        the max err, k <= delta(tan(x_i)) <= h * max(|sec^2(x)|)
        Rearranging:
        k / max(|sec^2(x)|) >= h

        tan(x) is obviously monotonically increasing on the interval [0, pi/4]
        => max(|sec^2(x)|) = (1/cos(pi/4))^2 = sqrt(2)^2 = 2 => h <= k/2
        """
        match args['qt']:
            case TRIGFOLD.HIGH:
                k = args['tan_k']
                start = 0
                stop = np.pi / 4
                sz = np.ceil(np.pi / (2 * k)) + 1 # ((pi/4) / (k / 2)) = pi/2
                sz = 1 << int(np.ceil(np.log2(sz)))
            case TRIGFOLD.MED:
                raise NotImplementedError('Half table not yet supported')
            case TRIGFOLD.LOW:
                # Naive (no optimisation)
                # Avoid pi/2 exactly
                stop = (np.pi * (sz - 1)) / (2 * sz) # = 0.5 * pi - step_size = 0.5 * pi - (np.pi/4) / sz
                start = -stop
                sz = N_TABLE_ENTRIES
            case _:
                assert_never(args['qt'])

        phi2 = np.linspace(start, stop, sz, dtype=np.double)

    if trig_opts & (TRIG_LUTS.ASIN.value | TRIG_LUTS.ACOS.value):
        """
        arcsin(-x) = -arcsin(x)
        => x |-> [0, 1]
        if x > sqrt(2) / 2
        => arcsin(x) = pi/2 - arcsin(sqrt(1 - x^2))
        => x |-> [0, sqrt(2) / 2]
        """
        match args['qt']:
            case TRIGFOLD.HIGH:
                stop = np.sqrt(2) / 2
                sz = N_TABLE_ENTRIES >> 2
            case TRIGFOLD.MED:
                raise NotImplementedError('Half table not yet supported')
            case TRIGFOLD.LOW:
                # Naive (no optimisation)
                stop = 1
                sz = N_TABLE_ENTRIES >> 1
            case _:
                assert_never(args['qt'])

        x = np.linspace(0, stop, sz, dtype=np.double)

    if trig_opts & TRIG_LUTS.ATAN.value:
        """
        Firstly, the function is odd atan(-x) = -atan(x)
        => x |-> [0, inf)

        Also atan(x) may be written as 0.5*i*ln(1 - i*x) - 0.5*i*ln(1 + i*x)
        => Indefinite integral of atan(x) from 0 to N for some natural number N is:
        x * arctan(x) - 0.5 * ln(x^2 + 1) + C
        => integral from 0 to N is:
        y = N * arctan(N) - 0.5 * ln(N^2 + 1)

        => y/N = arctan(N) - (0.5 * ln(N^2 + 1)) / N
        => err for y/N = (0.5 * ln(N^2 + 1)) / N

        let (0.5 * ln(N^2 + 1)) / N = k
        where k is the ideal threshold.

        (I don't know if there is a closed form for N,
        so the newton raphson method is used)
        """

        def newton_raphson_N(k: int, tolerance: float = 1e-7, max_iter: int = 100) -> float | None:
            N_current = 8 # This value seems stable
            for _ in range(max_iter):
                # Define f(N) = ln(N^2 + 1) - 2 * N * k
                f_N = np.log(N_current**2 + 1) - 2 * N_current * k

                # Define f'(N) = (2N / (N^2 + 1)) - 2k (zero not possible for real N)
                denominator_f_prime = N_current**2 + 1
                f_prime_N = (2 * N_current / denominator_f_prime) - 2 * k

                if abs(f_prime_N) < tolerance: # Avoid division by a very small number (or zero)
                    break

                # Newton-Raphson iteration
                try:
                    N_next = N_current - f_N / f_prime_N
                except OverflowError | ZeroDivisionError:
                    break

                # Check for convergence
                if abs(N_next - N_current) < tolerance:
                    return N_next

                # Update N for the next iteration
                N_current = N_next

            return

        match args['qt']:
            case TRIGFOLD.HIGH:
                k = args['atan_k']
                N = newton_raphson_N(k)
                if N is not None:
                    err = 0.5 * np.log(N**2 + 1) / N
                err_threshold = 0.1 * k # I.e. 10% of the threshold value
                if k > k + err_threshold or k < k - err_threshold:
                    print('---Building atan LUT---'
                        f'\n\tError: couldn\'t find an optimal table size N based on precision threshold {k}'
                        ' Try using a bigger value.'
                        f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
                        )

                print('---Building atan LUT---'
                    f'\n\tFound optimal value for N {N}'
                    f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
                    )

                sz = 1 << int(np.ceil(np.log2(N)))
                stop = int(np.ceil(N))
            case TRIGFOLD.MED:
                raise NotImplementedError('Half table not yet supported')
            case TRIGFOLD.LOW:
                # Naive (no optimisation)
                N = 1000 # Arbitrarily chosen
                start = -N
                stop = N
                sz = N_TABLE_ENTRIES
            case _:
                assert_never(args['qt'])

        x2 = np.linspace(0, stop, sz)

    if trig_opts & TRIG_LUTS.SIN.value:
        sin_tbl = np.sin(phi)
        assess_lut_accuracy(np.sin, sin_tbl, phi, oversample_factor=8)
    if trig_opts & TRIG_LUTS.COS.value:
        cos_tbl = np.cos(phi)
        assess_lut_accuracy(np.cos, cos_tbl, phi, oversample_factor=8)
    if trig_opts & TRIG_LUTS.TAN.value:
        tan_tbl = np.tan(phi2)
        acc_scores = assess_lut_accuracy(np.tan, tan_tbl, phi2, oversample_factor=8)
        k_avg_err = max(np.average(acc_scores) - args['tan_k'], 0)
        print(f'\tk (threshold): {args["tan_k"]}'
              f'\n\tErr W.R.T k {k_avg_err}'
             )
    if trig_opts & TRIG_LUTS.ASIN.value:
        asin_tbl = np.arcsin(x)
        assess_lut_accuracy(np.arcsin, asin_tbl, x, oversample_factor=8)
    if trig_opts & TRIG_LUTS.ACOS.value:
        acos_tbl = np.arccos(x)
        assess_lut_accuracy(np.arccos, acos_tbl, x, oversample_factor=8)
    if trig_opts & TRIG_LUTS.ATAN.value:
        atan_tbl = np.arctan(x2)
        acc_scores = assess_lut_accuracy(np.arctan, atan_tbl, x2, oversample_factor=8)
        k_avg_err = max(np.average(acc_scores) - args['atan_k'], 0)
        print(f'\tk (threshold): {args["atan_k"]}'
              f'\n\tErr W.R.T k {k_avg_err}'
             )


def assess_lut_accuracy(fn: Callable, tbl: Sequence[float], axis: Sequence[float],
                         oversample_factor: int) -> None:
    tbl_arr = np.asarray(tbl, dtype=np.double)
    axis_arr = np.asarray(axis, dtype=np.double)
    l_axis = np.size(axis_arr)
    min_ax_val, max_ax_val = np.min(axis_arr), np.max(axis_arr)

    if l_axis == 0:
        print(f'---Accuracy test results for {fn.__name__}---\n\tAxis is empty. Cannot perform test.')
        return

    if np.size(tbl_arr) != l_axis:
        print(f'---Accuracy test results for {fn.__name__}---\n\tTable size ({np.size(tbl_arr)}) '
              f'does not match axis size ({l_axis}). Cannot perform test')
        return

    fn_eval_points: np.ndarray
    if l_axis == 1:
        fn_eval_points = np.array([axis_arr[0]], dtype=np.double)
    else:
        l_test_axis_orig = oversample_factor * l_axis
        test_axis_orig = np.linspace(min_ax_val, max_ax_val, l_test_axis_orig, dtype=np.double)
        actual_indices_for_tbl = np.arange(l_axis)
        fn_eval_indices = actual_indices_for_tbl * oversample_factor
        fn_eval_indices = np.clip(fn_eval_indices, 0, l_test_axis_orig - 1)
        fn_eval_points = test_axis_orig[fn_eval_indices]

    fn_values_at_eval_points = np.asarray(fn(fn_eval_points), dtype=np.double)

    if fn_values_at_eval_points.shape != tbl_arr.shape:
        print(f'---Accuracy test results for {fn.__name__}---\n'
              f'\tShape mismatch between evaluated function values ({fn_values_at_eval_points.shape}) '
              f'and table values ({tbl_arr.shape}). Cannot compute scores.')
        return

    acc_scores = np.abs(tbl_arr - fn_values_at_eval_points)

    print(f'---Accuracy test results for {fn.__name__}---'
          f'\n\tLUT size in bytes: {np.size(tbl_arr) * 4} ({np.size(tbl_arr) / 250:.3f}kB)'
          f'\n\tAvg. acc score (lower is better): {np.average(acc_scores)}'
          f'\n\tOver-sample factor for fn evaluation grid: x{oversample_factor}'
          f'\n\tMin-acc loss: {np.min(acc_scores)}'
          f'\n\tMax-acc loss: {np.max(acc_scores)}')

    return acc_scores


if __name__ == '__main__':
    main()
