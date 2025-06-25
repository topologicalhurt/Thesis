#!/usr/bin/env python
"""
Generates a LUT for various trig functions (sin, cos, tan, asin, acos, atan)
with variable precision, size & options to use a heuristic to determine
the 'best' fit automatically
"""

# TODO's:
# (1) Fix atan so it can generate a quarter table LUT as well
# (2) Refactor into the allocator itself (to dynamically generate LUT's based on signal functions)


import argparse as ap
import collections
import numpy as np
import regex as re
import sys
import functools
import itertools

from collections.abc import Sequence, Callable
from typing import assert_never

from Allocator.Interpreter.dataclass import LUT, LUT_ACC_REPORT, ExtendedEnum, FLOAT_STR_NPMAP
from Allocator.Interpreter.helpers import pairwise, underline_matches

from RTL.Scripts.decorators import warning
from RTL.Scripts.argparse_helpers import str2bitwidth, str2enumval, bools2bitstr, eval_arithmetic_str_unsafe, str2path,\
get_action_from_parser_by_name, str2float, str2posint
from RTL.Scripts.dataclass import TRIGLUTDEFS, TRIGLUTFNDEFS, TRIGLUTS, TRIGFOLD, TRIGPREC, BYTEORDER
from RTL.Scripts.hex_utils import TrigLutManager


@warning('Function {f_name} can evaluate potentially unsafe arithmetic expressions. Enable with caution.')
def bram(v: int | str) -> int:
    if isinstance(v, str):
        return int(eval_arithmetic_str_unsafe(v))
    return v


def precmode(v: str) -> ExtendedEnum:
    if v.upper() in TRIGLUTDEFS.fields():
        return str2enumval(v, TRIGLUTDEFS)
    return str2enumval(v, TRIGPREC)


@warning('Function {f_name} can evaluate potentially unsafe arithmetic expressions. Enable with caution.')
def kthresh(v: float | str) -> float:
    if isinstance(v, str):
        if v.isdigit():
            v = str2float(v)
        v = float(eval_arithmetic_str_unsafe(v))

    v: float
    if v >= 1 or v <= 0:
        raise ap.ArgumentTypeError('Value must be positive float in range (0, 1)'
                                   f' but got {v} instead'
                                   )
    return v


@warning('Function {f_name} can evaluate potentially unsafe arithmetic expressions. Enable with caution.')
def os_factor(v: int | str) -> int:
    if isinstance(v, str):
        if v.isdigit():
            v = str2posint(v)
        else:
            v = int(eval_arithmetic_str_unsafe(v))

    if not float(np.log2(v)).is_integer():
        raise ap.ArgumentTypeError('Value must be a power of 2'
                                f' but got {v} instead'
                                )
    return v


def main() -> None:
    """# Summary

    Entry-point into lut generator. Run this script with the -h option for help.
    """
    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('dir', type=str2path,
                        help='The output directory for the LUTs'
                        )

    parser.add_argument('-bram', type=bram, default=2048,
                        help='The maximum allowable bram in bytes (I.e. if in quarter table mode table is of size'
                            ' requested_bram / 4)'
                        )

    parser.add_argument('-bw', type=functools.partial(str2bitwidth, is_int=False), default=FLOAT_STR_NPMAP.FLOAT32.value,
                        help='The bit width of each value in the LUT (default: float / 32bit)'
                        )

    parser.add_argument('-k', type=kthresh,
                    help='A floating point threshold value which determines the error tolerance for all trig functions'
                    ' NOTE: this will not be applied to tan & atan (see: -tan-k, -atan-k)'
                    )

    parser.add_argument('-osf', type=os_factor, default=128,
                        help='The oversampling factor to use on the reference LUT on the accuracy testbench'
                       )

    table_mode_enum_description = ''.join(TRIGFOLD.__doc__.strip().splitlines())
    table_mode_enum_description = re.sub(r'\s{2,}', ' ', table_mode_enum_description)
    table_mode_enum_description = table_mode_enum_description.removeprefix('# Summary Enum corresponding to ')
    parser.add_argument('-table_mode', type=functools.partial(str2enumval, target_enum=TRIGFOLD),
                        nargs='*', default=TRIGFOLD.HIGH,
                        help='Over which period all LUT\'s will be built'
                        ' (highest optimisation mode used if none specified, applies to all values if none provided)'
                        ' E.G. a value or field from either:'
                        f' {TRIGFOLD.fields()} | {TRIGFOLD.values()}.'
                        f' The following description might proove valuable: "{table_mode_enum_description}"'
                        )

    parser.add_argument('-hp', type=precmode, nargs='*', default=TRIGPREC.LOWP,
                        help=f'A list of trig values I.e. {TRIGLUTDEFS.fields()}'
                        ' to apply low precision mode to OR a list of trig values & explicit precision mode to use'
                        ' E.g. -hp cos medp sin medp tan highp.'
                        ' (lowest p-mode used if none specified, applies to all values if none provided)'
                        ' For example, if -table_mode (see: -table_mode) is in the highest mode (quarter table mode)'
                        ' then the default behaviour is to also reduce the LUT size'
                        ' by a factor of 4. In hp mode the requested table size remains the same (effective x4 oversampling)'
                        ' meaning it operates in a higher mode of precision.'
                        ' If a value is explicitly provided & table_mode differs E.g. -table_mode -hp cos medp | 1 then the factors are multiplied'
                        ' to size the table. I.e. in this scenario'
                        ' => a quarter table lookup method is used for half the period of the function (effective x2 oversampling)'
                        )

    parser.add_argument('-auto', type=functools.partial(str2enumval, target_enum=TRIGLUTDEFS),
                        nargs='*', default=True,
                        help='A list of values to include in auto mode'
                        ' This generates all luts in an ideal table size based on a global threshold (see: -k)'
                        ' This is done by using the newton raphson method, a known bound or other estimation techniques.'
                        ' If none supplied the default behaviour is to use auto.'
                        ' NOTE: the value of the gloal threshold, -k (see: -k), is independent of -tan-k (see: -tan-k)'
                        ' & -atan-k (see: -atan-k) which are individually supplied'
                        ' dependencies: -k (see: -k)'
                        ' prohibitions: -excl-auto (see: -excl-auto)'
                        )

    parser.add_argument('-excl-auto', type=functools.partial(str2enumval, target_enum=TRIGLUTDEFS),
                        nargs='*', default=False,
                        help='A list of values to exclude from auto mode'
                        ' prohibitions: -auto (see: -auto)'
                        )

    parser.add_argument('-tan-k', type=kthresh, default=0.05,
                        help='A floating point threshold value which determines the error tolerance for tan'
                        )

    parser.add_argument('-atan-k', type=kthresh, default=0.1,
                        help='A floating point threshold value which determines the error tolerance for atan'
                        )

    parser.add_argument('--auto-off', action='store_true', default=False,
                        help='Turns auto mode off if specified'
                        )

    parser.add_argument('--all', action='store_true', default=False,
                        help='Will generate cosine, arccos (in addition to sin, arcsin) if specified'
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

    bw_int, args['bw'] = args['bw'] # Store the actual integer value of the bit_width in bw_int and the type in args['bw']

    NON_FLAGS = [action.option_strings for action in parser._actions]
    NON_FLAGS = [opt.removeprefix('-').replace('-', '_') for opt in
                 itertools.chain.from_iterable(NON_FLAGS)
                 if not opt.startswith('--')] # Excl. non flags
    NON_FLAGS.extend(('auto_off', 'all')) # Excl. flags manually
    NON_FLAGS.extend([action.dest for action in parser._get_positional_actions()]) # Excl. positionals
    TRIG_LUTS = TRIGLUTS(**{k : 1 for k in TRIGLUTDEFS.fields()})

    # Calculate the table size based on the entry size
    bw_int_bytes = bw_int // 8
    if args['bram'] < bw_int_bytes:
        raise ap.ArgumentTypeError('bram must hold at least one value of the provided size')
    N_TABLE_ENTRIES = args['bram'] // bw_int_bytes

    trig_args = {k : v for k, v in args.items() if k not in NON_FLAGS}
    if sum(trig_args.values()) == 0:
        trig_opts = (1 << len(trig_args)) - 1
        if not args['all']:
            # Don't generate both acos & asin / cos & sin lut's unless explicitly specified
            trig_opts ^= (TRIG_LUTS.COS.value | TRIG_LUTS.ACOS.value)
    else:
        trig_opts = bools2bitstr(*trig_args.values())

    if not args['table_mode'] or args['table_mode'] in TRIGFOLD:
        # If table_mode parameter is provided but with no arg represent all functions as highest optimisation by default
        # If table_mode parameter wasn't provided at all it fallsback to the singular default value
        table_mode_default = get_action_from_parser_by_name(parser, 'table_mode').default
        args['table_mode'] = {k: table_mode_default for k in TRIGLUTDEFS}

    if args['hp'] and isinstance(args['hp'], Sequence) and len(args['hp']) == 1 and args['hp'][0] in TRIGPREC:
        # If hp is provided as just a precision mode use that precision mode on all functions
        args['hp'] = {k: args['hp'][0] for k in TRIGLUTDEFS}
    elif not args['hp'] or args['hp'] in TRIGPREC:
        # If hp parameter provided but with no arg represent all functions as lowest precision by default
        # If hp parameter wasn't provided at all it fallsback to the singular default value (same as above)
        hp_default = get_action_from_parser_by_name(parser, 'hp').default
        args['hp'] = {k: hp_default for k in TRIGLUTDEFS}
    else:
        err_invoker = get_action_from_parser_by_name(parser, 'hp')
        counts = collections.Counter([a for a in args['hp'] if a.name in TRIGLUTDEFS])
        counts_gt_one = {k.name: v for k, v in counts.items() if v > 1}
        if any(counts_gt_one):
            err_msg = ' '.join([val.name for val in args['hp']])
            raise ap.ArgumentError(err_invoker,
                                   '-hp takes only unique values for <trig function>'
                                   ' but the argument contains duplicate pairs. I.e.:'
                                   f'\n{underline_matches(err_msg, counts_gt_one.keys(), match_all=True)}'
                                   )

        # If hp parameter provided check that each trig value is adjacent to a precision arg
        if len(args['hp']) % 2 != 0:
            err_msg = [val.name for val in args['hp']]
            last_w = err_msg[-1]
            err_msg.append('*missing value*')
            err_msg = ' '.join(err_msg)
            raise ap.ArgumentError(err_invoker,
                                   '-hp takes <trig function> <precision mode> pairs as argument'
                                   ' but the argument length was odd. I.e.:'
                                   f'\n{underline_matches(err_msg, last_w)}'
                                   )

        for trig_v, pmode in pairwise(args['hp']):
            if trig_v not in TRIGLUTDEFS or pmode not in TRIGPREC:
                err_msg = ' '.join([val.name for val in args['hp']])
                raise ap.ArgumentError(err_invoker,
                        '-hp takes <trig function> <precision mode> pairs as argument'
                        ' but a pair was out of order. I.e.:'
                        f'\n{underline_matches(err_msg, (trig_v.name, pmode.name))}'
                        )

        args['hp'] = {k: v for k, v in pairwise(args['hp'])}

    member_set = set(TRIGLUTDEFS.__members__.values())
    def _parse_auto(s1: Sequence[ExtendedEnum] | bool, s2: Sequence[ExtendedEnum] | bool) -> Sequence[ExtendedEnum]:
        """
        Case I: If s1 was specified but no argument was supplied OR s1 was not specified at all THEN |->
        Case I.I: If s2 was specified & supplied find the set difference
        Case I.II: If s2 was specified but not supplied it contains all elements
        Case I.III: If s2 wasn't specified at all then the boolean value of s1 determines if it contains all elements or is empty
        Case II: s1 was specified so just return s1 as a set
        """
        if s1 == [] or type(s1) is bool:
            s2_was_supplied = isinstance(s2, Sequence)
            if s2_was_supplied and s2:
                return member_set.difference(s2)
            elif not s2:
                return member_set
            else:
                return member_set if s1 is True else set()
        return set(s1)

    if type(args['auto']) is not bool and args['auto_off']:
        err_invoker = get_action_from_parser_by_name(parser, 'auto')
        err_msg = ' '.join(sys.argv[1:])
        raise ap.ArgumentError(err_invoker,
                               'Supplied -auto and --auto-off simultaneously. A contradiction. Use one or the other. I.e.:'
                               f'\n{underline_matches(err_msg, ("-auto-off", "-auto"), match_all=True)}'
                              )

    if args['auto_off']:
        args['auto'] = set()
        args['excl_auto'] = member_set
    else:
        args['auto'] = _parse_auto(args['auto'], args['excl_auto'])
        args['excl_auto'] = _parse_auto(args['excl_auto'], args['auto'])

    # Check that args appearing in auto mask don't also appear in excl_auto mask
    if intersect := args['excl_auto'].intersection(args['auto']):
        err_invoker = get_action_from_parser_by_name(parser, 'excl_auto')
        auto_msg = ' '.join([v.name for v in args['auto']])
        excl_auto_msg = ' '.join([v.name for v in args['excl_auto']])
        err_msg = f'-auto {{{auto_msg}}} -excl-auto {{{excl_auto_msg}}}'
        common_msg = [v.name for v in intersect]
        raise ap.ArgumentError(err_invoker,
                               'Arguments specified in -auto must not also appear in -excl-auto'
                               ' (can\'t simultaneously be in both). I.e.:'
                               f'\n{underline_matches(err_msg, common_msg, match_all=True)}'
                               )

    # Check that (if auto mode isn't just the tuple (TAN, ATAN) as these supply default thresholds)
    # k is specified
    if not args['auto_off'] and\
        (len(args['auto']) != 2 or (TRIGLUTDEFS.TAN not in args['auto'] or\
        TRIGLUTDEFS.ATAN not in args['auto'])) and args['k'] is None:
        err_invoker = get_action_from_parser_by_name(parser, 'k')
        raise ap.ArgumentError(err_invoker,
                               'k must be supplied if auto mode is turned on'
                               )

    def _calculate_scale_factor(table_mode: TRIGFOLD, table_prec: TRIGPREC):
        return max(table_mode.value * (TRIGPREC.HIGHP.value - table_prec.value), 1)

    phis = {}
    xs = {}
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
        sinusoids = {k: v for k, v in args['table_mode'].items() if k.value in TRIGLUTDEFS._SINUSOIDS.value}
        for k, table_mode in sinusoids.items():
            sz = N_TABLE_ENTRIES // _calculate_scale_factor(args['table_mode'][k], args['hp'][k])
            match table_mode:
                case TRIGFOLD.HIGH:
                    stop = np.pi / 2
                case TRIGFOLD.MED:
                    raise NotImplementedError('Half table not yet supported')
                case TRIGFOLD.LOW:
                    stop = np.pi * 2
                case _:
                    assert_never(args['table_mode'])

            # https://zipcpu.com/dsp/2017/08/26/quarterwave.html
            # Minimize harmonic distortion
            phis[k] = (np.pi * 2 * np.arange(sz, dtype=args['bw'])) / N_TABLE_ENTRIES
            phis[k] += np.pi / N_TABLE_ENTRIES

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
        match args['table_mode'][TRIGLUTDEFS.TAN]:
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
                assert_never(args['table_mode'])

        phis[TRIGLUTDEFS.TAN] = np.linspace(start, stop, sz, dtype=args['bw'])

    if trig_opts & (TRIG_LUTS.ASIN.value | TRIG_LUTS.ACOS.value):
        """
        arcsin(-x) = -arcsin(x)
        => x |-> [0, 1]
        if x > sqrt(2) / 2
        => arcsin(x) = pi/2 - arcsin(sqrt(1 - x^2))
        => x |-> [0, sqrt(2) / 2]
        """
        arc_sinusoids = {k: v for k, v in args['table_mode'].items() if k.value in TRIGLUTDEFS._ARC_SINUSOIDS.value}
        for k, table_mode in arc_sinusoids.items():
            sz = N_TABLE_ENTRIES // _calculate_scale_factor(args['table_mode'][k], args['hp'][k])
            match table_mode:
                case TRIGFOLD.HIGH:
                    stop = np.sqrt(2) / 2
                case TRIGFOLD.MED:
                    raise NotImplementedError('Half table not yet supported')
                case TRIGFOLD.LOW:
                    # Naive (no optimisation)
                    stop = 1
                case _:
                    assert_never(args['table_mode'])

            xs[k] = np.linspace(0, stop, sz, dtype=args['bw'])

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

        match args['table_mode'][TRIGLUTDEFS.ATAN]:
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
                assert_never(args['table_mode'])

        xs[TRIGLUTDEFS.ATAN] = np.linspace(0, stop, sz, dtype=args['bw'])

    luts_to_w = []
    cmd_line_args = ' '.join(sys.argv[2:])
    for m, bit_v in zip(TRIGLUTDEFS.get_members(), TRIG_LUTS.__members__.values()):
        k = args['k']
        if trig_opts & bit_v.value:
            match m:
                case TRIGLUTDEFS.SIN:
                    domain = phis
                case TRIGLUTDEFS.COS:
                    domain = phis
                case TRIGLUTDEFS.TAN:
                    domain = phis
                    k = args['tan_k']
                case TRIGLUTDEFS.ASIN:
                    domain = xs
                case TRIGLUTDEFS.ACOS:
                    domain = xs
                case TRIGLUTDEFS.ATAN:
                    domain = xs
                    k = args['atan_k']
                case _:
                    assert_never(m)

            # Lut is nothing more than the given function evaluated over the proper domain
            # Effort was in 'folding' the domain, determining periodicity, error, etc.
            fn = TRIGLUTFNDEFS.get_member_via_value_from_name(m.name).value
            lut = fn(domain[m])

            acc_report = assess_lut_accuracy(fn, lut, domain[m],
                                             oversample_factor=args['osf'], type=args['bw'],
                                             test_type=args['bw']
                                            )

            # If k specified print the err compared to avg acc.
            if args['k'] and (m in TRIGLUTDEFS._SINUSOIDS.value or m in TRIGLUTDEFS._ARC_SINUSOIDS.value)\
            or (args['tan_k'] and m == TRIG_LUTS.TAN) or (args['atan_k'] and m == TRIG_LUTS.ATAN):
                k_avg_err = max(np.average(acc_report.acc_scores) - k, 0)
                print(f'\tk (threshold): {args[m]}'
                      f'\n\tErr W.R.T k {k_avg_err}'
                     )

            # The factor that indicates mix of precision and optimisation
            scale_factor = _calculate_scale_factor(args['table_mode'][m], args['hp'][m])

            luts_to_w.append(
                LUT(lut=lut,
                    endianness=BYTEORDER.BIG,
                    bit_width=bw_int, table_sz=((bw_int_bytes * np.size(lut)) / 1000),
                    lop=args['hp'][m], table_mode=args['table_mode'][m],
                    scale_factor=scale_factor,
                    fn=fn, acc_report=acc_report,
                    cmd=underline_matches(cmd_line_args, m.name, match_all=True)
                    )
            )

    # Done! Write to .hex file
    hexManager = TrigLutManager(args['dir'])
    for lut in luts_to_w:
        fn = (f'{lut.fn.__name__}_{lut.bit_width}'
              f'_{lut.table_mode.name.lower()}_{lut.lop.name.lower()}'
              )
        hexManager.write_lut_to_hex(fn, lut, ow=True, target_order=BYTEORDER.BIG)


def assess_lut_accuracy(fn: Callable[..., float],
                         lut: Sequence[float], axis: Sequence[float],
                         oversample_factor: int, type: float,
                         test_type: float = np.float32) -> LUT_ACC_REPORT:
    """ # Summary

    Assesses the lut accuracy against a function, fn, sampled at oversample_factor
    over the axis, axis.
    """
    lut_arr = np.asarray(lut, dtype=type)
    axis_arr = np.asarray(axis, dtype=type)
    l_axis = np.size(axis_arr)
    min_ax_val, max_ax_val = np.min(axis_arr), np.max(axis_arr)

    if l_axis == 0:
        print(f'---Accuracy test results for {fn.__name__}---\n\tAxis is empty. Cannot perform test.')
        return

    if np.size(lut_arr) != l_axis:
        print(f'---Accuracy test results for {fn.__name__}---\n\tTable size ({np.size(lut_arr)}) '
              f'does not match axis size ({l_axis}). Cannot perform test')
        return

    fn_eval_points: np.ndarray
    if l_axis == 1:
        fn_eval_points = np.array([axis_arr[0]], dtype=type)
    else:
        l_test_axis_orig = oversample_factor * l_axis
        test_axis_orig = np.linspace(min_ax_val, max_ax_val, l_test_axis_orig, dtype=test_type)
        actual_indices_for_tbl = np.arange(l_axis)
        fn_eval_indices = actual_indices_for_tbl * oversample_factor
        fn_eval_indices = np.clip(fn_eval_indices, 0, l_test_axis_orig - 1)
        fn_eval_points = test_axis_orig[fn_eval_indices]

    fn_values_at_eval_points = np.asarray(fn(fn_eval_points), dtype=type)

    if fn_values_at_eval_points.shape != lut_arr.shape:
        print(f'---Accuracy test results for {fn.__name__}---\n'
              f'\tShape mismatch between evaluated function values ({fn_values_at_eval_points.shape}) '
              f'and table values ({lut_arr.shape}). Cannot compute scores.')
        return

    acc_scores = np.abs(lut_arr - fn_values_at_eval_points)

    acc_report = LUT_ACC_REPORT(avg_acc=np.average(acc_scores), min_acc=np.min(acc_scores),
                                 max_acc=np.max(acc_scores), acc_scores=acc_scores)

    type_sz = np.size(lut_arr) * np.dtype(type).itemsize
    print(f'---Accuracy test results for {fn.__name__}---'
          f'\n\tLUT size in bytes: {type_sz} ({type_sz / 1000:.3f}kB)'
          f'\n\tOver-sample factor for fn evaluation grid: x{oversample_factor}'
          f'{acc_report}'
          )

    return acc_report


if __name__ == '__main__':
    main()
