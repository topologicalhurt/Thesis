#!/usr/bin/env python
"""
------------------------------------------------------------------------
Filename:	generate_trig_luts.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Generates a LUT for various trig functions (sin, cos, tan, asin, acos, atan)
with variable precision, size & options to use a heuristic to determine
the 'best' fit automatically

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:	GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------

"""

# TODO's:
# (1) Full opt coverage for all functions
# (2) More descriptive argparse error messages (E.G. what to do instead, remove bin unless in verbose mode etc.)
#   - Including errors for precision mismatches, high memory usage etc.
# (3) Introduce RMS, mean, max, newtown raphson modes for each k estimation technique
# (4) Introduce way to prioritize phase distortion or frequency response or both
# (5) Methods to test phase distortion, harmonic distortion
# (6) Introduce chebyshev polynomial for max opt mode
# (7) Non-uniform spacing for 'denser' functions I.e. tan which requires higher precision around the pole at pi/2
# (8) Ensure bram is correctly enforced (it isn't on sinc)
# (9) Refactor into the allocator itself (to dynamically generate LUT's based on signal functions)
# (10) Option to generate another LUT to generate the target LUT e.g. arcsin on high mode requires computation of sqrt(1 - x).
# so an option would be to store the arcsin LUT recovery method itself in a LUT for a ~2 cycle lookup, but at the cost of more memory


import collections
import sys
import functools
import regex as re
import argparse as ap
import numpy as np
import scipy as sp

from collections.abc import Mapping, Sequence, Callable, Set
from typing import Any, assert_never

from Allocator.Interpreter.bitfield import BITFIELD
from Allocator.Interpreter.extendedenum import ExtendedEnum
from Allocator.Interpreter.nptypes import FLOAT_STR_NPMAP, INT_STR_NPMAP
from Allocator.Interpreter.dataclass import LUT, BYTEORDER, LUT_ACC_REPORT, LUT_TYPE
from Allocator.Interpreter.lut_acc_metrics import LutAccMetrics
from Allocator.Interpreter.helpers import bitfield_from_enum_mask, bitstr_from_enum_mask, pairwise, underline_matches, quantize

from Scripts.argparse_helpers import get_non_flags, str2Qfixedformat, str2bitwidth, str2enumval, eval_arithmetic_str_safe, str2path, get_action_from_parser_by_name,\
str2float, str2posint
from Scripts.dataclass import TRIG_ATAN_OPTS, TRIG_OPTS, TRIG_SINC_OPTS, TRIG_DEFS, TRIG_FN_DEFS, TRIG_OPT_MODE, TRIG_MUST_HAVE_KSET, TRIG_PRECISION
from Scripts.hex_utils import TrigLutManager
from Scripts.consts import GENERATE_TRIG_LUTS_PREFIX, LOGGER, LUT_DEFAULT_BRAM, log_wrapper


#######################
# Main control flow   #
#######################


def main() -> None:
    """# Summary

    Entry-point into lut generator. Run this script with the -h option for help.
    """
    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('dir', type=str2path,
                        help='The output directory for the LUTs'
                        )

    parser.add_argument('q', type=str2Qfixedformat,
                    help='The Qm.n fixed point float format to convert the data into.'
                    ' Format is Q<integer_part>.<floating_part>.'
                    ' Also accepts the value "auto" which will automatically determine the minimum integer & floating part'
                    ' for you. However, it is strongly recommended that you explicitly specify the q format as decoding'
                    ' / dealing with q format is not FPGA agnostic'
                    )

    parser.add_argument('-bram', type=_TrigArgParser.bram, default=LUT_DEFAULT_BRAM,
                        help='The maximum allowable bram in bytes (I.e. if in quarter table mode table is of size'
                            ' requested_bram / 4)'
                        )

    parser.add_argument('-bw', type=functools.partial(str2bitwidth, is_int=False), default=FLOAT_STR_NPMAP.FLOAT32.value,
                        help='The bit width of each value in the LUT (default: float32 / 32bit)'
                        )

    parser.add_argument('-k', type=_TrigArgParser.kthresh, default=0.01,
                        help='A floating point threshold value which determines the error tolerance for all trig functions'
                        ' NOTE: this will not be applied to tan & atan (see: -tan-k, -atan-k)'
                        )

    parser.add_argument('-osf', type=_TrigArgParser.os_factor, default=128,
                        help='The oversampling factor to use on the reference LUT on the accuracy testbench'
                        )

    table_mode_enum_description = ''.join(TRIG_OPT_MODE.__doc__.strip().splitlines())
    table_mode_enum_description = re.sub(r'\s{2,}', ' ', table_mode_enum_description)
    table_mode_enum_description = table_mode_enum_description.removeprefix('# Summary Enum corresponding to ')
    parser.add_argument('-table-mode', type=functools.partial(str2enumval, target_enum=TRIG_OPT_MODE),
                        nargs='*', default=TRIG_OPT_MODE.HIGH,
                        help='Over which period all LUT\'s will be built'
                        ' (highest optimisation mode used if none specified, applies to all values if none provided)'
                        ' E.G. a value or field from either:'
                        f' {TRIG_OPT_MODE.fields()} | {TRIG_OPT_MODE.values()}.'
                        f' The following description might proove valuable: "{table_mode_enum_description}"'
                        )

    parser.add_argument('-prec-mode', type=_TrigArgParser.precmode, nargs='*', default=TRIG_PRECISION.LOWP,
                        help=f'A list of trig values I.e. {TRIG_DEFS.fields()}'
                        ' to apply low precision mode to OR a list of trig values & explicit precision mode to use'
                        ' E.g. -prec-mode cos medp sin medp tan highp.'
                        ' (lowest p-mode used if none specified, applies to all values if none provided)'
                        ' For example, if -table_mode (see: -table_mode) is in the highest mode (quarter table mode)'
                        ' then the default behaviour is to also reduce the LUT size'
                        ' by a factor of 4. In prec mode the requested table size remains the same (effective x4 oversampling)'
                        ' meaning it operates in a higher mode of precision.'
                        ' If a value is explicitly provided & table_mode differs E.g. -table_mode -prec-mode cos medp | 1 then the factors are multiplied'
                        ' to size the table. I.e. in this scenario'
                        ' => a quarter table lookup method is used for half the period of the function (effective x2 oversampling)'
                        )

    parser.add_argument('-auto', type=functools.partial(str2enumval, target_enum=TRIG_DEFS),
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

    parser.add_argument('-excl-auto', type=functools.partial(str2enumval, target_enum=TRIG_DEFS),
                        nargs='*', default=False,
                        help='A list of values to exclude from auto mode'
                        ' prohibitions: -auto (see: -auto)'
                        )

    parser.add_argument('-tan-k', type=_TrigArgParser.kthresh, const=_TrigArgParser.DEFAULT_THRESHOLD, nargs='?',
                        help='A floating point threshold value which determines the error tolerance for tan'
                        )

    parser.add_argument('-atan-k', type=_TrigArgParser.kthresh, const=_TrigArgParser.DEFAULT_THRESHOLD, nargs='?',
                        help='A floating point threshold value which determines the error tolerance for atan'
                        )

    parser.add_argument('-sinc-k', type=_TrigArgParser.kthresh, const=_TrigArgParser.DEFAULT_THRESHOLD, nargs='?',
                        help='A floating point threshold value which determines the error tolerance for sinc'
                        )

    parser.add_argument('--auto-off', action='store_true', default=False,
                        help='Turns auto mode off if specified'
                        )

    parser.add_argument('--no-quantize', action='store_true', default=False,
                        help='Forcibly quantize the generated LUT to nearest power of 2'
                        )

    parser.add_argument('--all', action='store_true', default=False,
                        help='Will generate cosine, arccos (in addition to sin, arcsin) if specified'
                        )

    parser.add_argument('--nw', action='store_true', default=False,
                        help='Will not write anything out into a .hex file if specified'
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

    parser.add_argument('--sinc', action='store_true', default=False,
                    help='Creates a sinc LUT'
                    ' Note: the opt mode works differently here: '
                    ' Lowest optimisation level: store sinc up to err threshold (I.e. zero crossing up to attenuation target)'
                    ' Medium optimisation level: store a half-symmetry LUT (I.e. mirror about origin)'
                    ' High optimisation level (reccomended): approximate using lobe & envelope'
                    ' (TODO) Highest optimisation level: Chebyshev polynomial approximation'
                    )

    args = vars(parser.parse_args())
    trig_parser = _TrigArgParser(parser, **args)
    args = trig_parser.parse()
    lut_select = trig_parser.trig_opts.lut_select

    phis = {}                                           # Mapping from fn: domain for theta -> x functions
    xs = {}                                             # Mapping from fn: domain for x -> theta functions

    if lut_select & _TrigArgParser.SIN_COS:
        generate_sin_cos_domain(phis, trig_parser=trig_parser)

    if lut_select & _TrigArgParser.TRIG_LUTS_BITFIELD.TAN.value:
        generate_tan_domain(phis, trig_parser=trig_parser)

    if lut_select & _TrigArgParser.ASIN_ACOS:
        generate_asin_acos_domain(xs, trig_parser=trig_parser)

    if lut_select & _TrigArgParser.TRIG_LUTS_BITFIELD.ATAN.value:
        generate_atan_domain(xs, trig_parser=trig_parser)

    if lut_select & _TrigArgParser.TRIG_LUTS_BITFIELD.SINC.value:
        generate_sinc_domain(xs, trig_parser=trig_parser)

    luts_to_w = _generate_luts(trig_parser=trig_parser, phis=phis, xs=xs)
    _write_out_luts(luts_to_w, trig_parser=trig_parser)    # Done! Write to .hex file


###############
# Arg parsing #
###############


class _TrigArgParser():

    TRIG_LUTS_BITFIELD = BITFIELD(**{k : 1 for k in TRIG_DEFS.fields()}) # BitField for which trig luts get built
    TRIG_LUTS_TO_EXCLUDE_BY_DEFAULT = TRIG_LUTS_BITFIELD.COS.value | TRIG_LUTS_BITFIELD.ACOS.value | TRIG_LUTS_BITFIELD.SINC.value
    SIN_COS = TRIG_LUTS_BITFIELD.SIN.value | TRIG_LUTS_BITFIELD.COS.value
    ASIN_ACOS = TRIG_LUTS_BITFIELD.ASIN.value | TRIG_LUTS_BITFIELD.ACOS.value
    DEFAULT_THRESHOLD = np.float32(0.001)

    def __init__(self, parser: ap.ArgumentParser, **kwargs: Mapping[str, Any]):
        self.args = kwargs
        self.parser = parser
        self.non_flags = get_non_flags(parser)

        self.k_lut_mask = [field.lower() for field in TRIG_MUST_HAVE_KSET.fields()]
        self.k_fields = {f'{field}_k': self.args[f'{field}_k'] for field in self.k_lut_mask}

        # self.args['bw'] is an enum member storing (<type_sz>, <type>) I.e. (32, np.int32)
        # Store the actual integer value (I.e 32) of the bit_width in bw_sz & the type in args['bw']
        self.bw_sz, self.args['bw'] = self.args['bw']

        self.bw_sz_bytes = self.bw_sz // 8
        self.n_entries = self.args['bram'] // self.bw_sz_bytes                        # Num. of entries in table / lut
        self.bw_type_int = INT_STR_NPMAP.get_member_via_value(self.bw_sz).value[1]    # Integer equiv. of bw_sz

        self.trig_opts = None

    @staticmethod
    def bram(val: str) -> np.uint:
        return np.uint64(eval_arithmetic_str_safe(val))

    @staticmethod
    def precmode(val: str) -> ExtendedEnum:
        if val in TRIG_DEFS:
            return str2enumval(val, TRIG_DEFS)
        return str2enumval(val, TRIG_PRECISION)

    @staticmethod
    def kthresh(val: str) -> np.floating:
        if val.isdigit():
            val = str2float(val)
        else:
            val = eval_arithmetic_str_safe(val)

        if val >= 1 or val <= 0:
            raise ap.ArgumentTypeError('Value must be positive float in range (0, 1)'
                                       f' but got {val:.6f} instead'
                                       )
        return val

    @staticmethod
    def os_factor(val: str) -> np.uint:
        if val.isdigit():
            val = str2posint(val)
        else:
            val = np.uint(eval_arithmetic_str_safe(val))

        if not float(np.log2(val)).is_integer():
            raise ap.ArgumentTypeError('Value must be a power of 2'
                                       f' but got {val} instead'
                                       )
        return val

    def _check_bram_sz(self) -> bool:
        """
        Check that the size of the bram can contain at-least one element of the specified size
        """
        return self.args['bram'] > self.bw_sz_bytes

    def _check_auto_autooff(self) -> bool:
        """
        Check that, if --auto is supplied, that --auto-off isn't simultaneously supplied
        """
        return not isinstance(self.args['auto'], bool) and self.args['auto'] and self.args['auto_off']

    def _check_auto_autooff_for_k(self) -> bool:
        """
        Check that if the auto off option is supplied, k is supplied for all options except those to which auto applies by default
        """
        return self.args['auto_off'] and set(TRIG_MUST_HAVE_KSET.fields()).intersection('auto') and self.args['k'] is None

    def _parse_option_values(self) -> TRIG_OPTS:
        lut_mask = {k : v for k, v in self.args.items() if k in TRIG_DEFS}    # LUTS to generate masked by boolean I.e. {'sin': True, 'cos': False ...}

        # Lut select selects the lut values that were selected from the command line, encoding as bitstr.
        # If no values are supplied, then generate all luts except those specified in TRIG_LUTS_TO_EXCLUDE_BY_DEFAULT
        lut_select = bitstr_from_enum_mask(TRIG_DEFS, None, True, *lut_mask.values())
        if lut_select == 0:
            lut_select = (1 << len(lut_mask)) - 1
            if not self.args['all']:
                lut_select ^= _TrigArgParser.TRIG_LUTS_TO_EXCLUDE_BY_DEFAULT

        # This selects the lut values that *need* to be supplied from trig_opts, encoding as bitstr
        k_mask_bitfield = bitfield_from_enum_mask(TRIG_DEFS, mask=self.k_lut_mask)
        k_mask_bitfield = k_mask_bitfield.get_bit_str() & lut_select

        # This selects the lut values that *were* selected by the command line, encoding as bitstr
        lut_values_specified = [self.args[field] for field in self.k_lut_mask]
        k_lut_select = bitstr_from_enum_mask(TRIG_DEFS, self.k_lut_mask, True, *lut_values_specified)

        # This selects the k values that *were* selected by the command line, encoding as bitstr
        k_values_specified = [v is not None for v in self.k_fields.values()]
        k_values_select = bitstr_from_enum_mask(TRIG_DEFS, self.k_lut_mask, True, *k_values_specified)

        # Occurs IFF. no lut AND no k were supplied I.e. empty command line args or using --all
        no_k_no_vals = (k_values_select == k_lut_select == 0) and k_mask_bitfield != 0

        err_invoker = get_action_from_parser_by_name(self.parser, 'k')

        trig_opts = TRIG_OPTS(lut_select=lut_select, k_mask_bitfield=k_mask_bitfield,
                              k_lut_select=k_lut_select, k_values_select=k_values_select)

        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            'Attempting to parse trig opts. Received the following:'
            f'{trig_opts}'
        ))

        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            'Script was invoked with the following *options*:'
            f'\n\tCommand: {sys.argv[1:]}'
            f'\nReceving the following values (before parsing):'
            f'\n{log_wrapper.fill(text=str(self.args))}'
        ))

        # Case I: Ensure that there are as many k values as trig values, if supplied
        # Case II: Ensure that all k values are manually supplied for args specified in TRIGMUSTHAVEKSET
        if  (k_values_select > k_lut_select and k_mask_bitfield ^ k_values_select) and not no_k_no_vals:
            raise ap.ArgumentError(err_invoker,
                                    'A k / threshold value was provided but the corresponding trig function was not explicitly declared:'
                                    f'\n{underline_matches(' '.join(sys.argv[1:]), r'-\w+-k', match_all=True, literal=False)}'
                                    '\nif LUT is to be generated.'
                                    )

        elif k_mask_bitfield ^ k_values_select and not no_k_no_vals:
            to_underline = [v.lower() for v in self.k_lut_mask]
            raise ap.ArgumentError(err_invoker,
                                    'k must be individually supplied for:'
                                    f'\n{underline_matches(' '.join(sys.argv[1:]), to_underline, match_all=True)}'
                                    '\nif LUT is to be generated.'
                                    )

        return trig_opts

    def _parse_k_vals(self) -> Mapping[str, bool]:
        return {k: _TrigArgParser.DEFAULT_THRESHOLD if v is None else v for k, v in self.k_fields.items()}

    def _parse_table_mode(self) -> Mapping[TRIG_DEFS, TRIG_OPT_MODE]:
        table_mode_default = get_action_from_parser_by_name(self.parser, 'table_mode').default
        if not self.args['table_mode'] or self.args['table_mode'] in TRIG_OPT_MODE:
            """
            If table_mode parameter wasn't provided at all, or provided but no args supplied,
            It should fallback to the singular default value.
            args['table_mode'] in TRIGFOLD triggers on default (no parameter provided, so is a value not a list).
            args['table_mode'] is [] I.e. empty if specified without argument.
            """
            return {k: table_mode_default for k in TRIG_DEFS.get_members()}

        if len(self.args['table_mode']) == 1:
            # If args['table_mode'] is a singleton, set that as the global value instead of the default value
            table_mode_default = self.args['table_mode'][0]
            return {k: table_mode_default for k in TRIG_DEFS.get_members()}

        # If args['table_mode'] isn't a singleton, set all values to default then update only the arguments specified
        # (An ordered list corresponding to order of TRIGLUTDEFS)
        default_table_mode = {k: table_mode_default for k in TRIG_DEFS.get_members()}
        table_mode_order = {k : v for k, v in zip(TRIG_DEFS.get_members(), self.args['table_mode'])}
        default_table_mode.update(table_mode_order)
        return default_table_mode

    def _parse_optimisation_mode(self) -> Mapping[TRIG_DEFS, TRIG_PRECISION]:
        opt_mode_default = get_action_from_parser_by_name(self.parser, 'prec_mode').default
        if not self.args['prec_mode'] or self.args['prec_mode'] in TRIG_PRECISION:
            """
            If prec-mode parameter provided but with no args supplied, then represent all luts as lowest precision by default
            O.T.W ifprec-mode parameter wasn't provided at all, fallback to the default value for all luts
            (see: same control logic as _parse_table_mode)
            """
            return {k: opt_mode_default for k in TRIG_DEFS}

        if len(self.args['prec_mode']) == 1:
            # If prec mode is provided as a single precision mode value, use that precision mode on all luts
            opt_mode_default = self.args['prec_mode'][0]
            return {k: opt_mode_default for k in TRIG_DEFS}

        # If multiple args were supplied check that the arg only specifies unique luts (I.e. illegal: sin |-> mode 0, sin |-> mode 2)
        err_invoker = get_action_from_parser_by_name(self.parser, 'prec_mode')
        counts = collections.Counter([a for a in self.args['prec_mode'] if a.name in TRIG_DEFS])
        counts_gt_one = {k.name: v for k, v in counts.items() if v > 1}
        if any(counts_gt_one):
            raise ap.ArgumentError(err_invoker,
                                    '-prec-mode takes only unique values for <trig function>'
                                    ' but the argument contains duplicate pairs. I.e.:'
                                    f'\n{underline_matches(' '.join([val.name for val in self.args['prec_mode']]), counts_gt_one.keys(), match_all=True)}'
                                    )

        # If multiple args were supplied check that each adjacent value is a precision arg
        if len(self.args['prec_mode']) % 2 != 0:
            err_msg = [val.name for val in self.args['prec_mode']]
            last_w = err_msg[-1]
            err_msg.append('*missing value*')
            err_msg = ' '.join(err_msg)
            raise ap.ArgumentError(err_invoker,
                                    '-prec-mode takes <trig function> <precision mode> pairs as argument'
                                    ' but the argument length was odd. I.e.:'
                                    f'\n{underline_matches(err_msg, last_w)}'
                                    )

        # Now it is safe to iterate pairwise
        for trig_v, pmode in pairwise(self.args['prec_mode']):
            if trig_v not in TRIG_DEFS or pmode not in TRIG_PRECISION:
                err_msg = ' '.join([val.name for val in self.args['prec_mode']])
                raise ap.ArgumentError(err_invoker,
                                        '-prec-mode takes <trig function> <precision mode> pairs as argument'
                                        ' but a pair was out of order. I.e.:'
                                        f'\n{underline_matches(err_msg, (trig_v.name, pmode.name))}'
                                       )

        return {k: v for k, v in pairwise(self.args['prec_mode'])}

    def _parse_auto(self) -> Sequence[Set[ExtendedEnum], Set[ExtendedEnum]]:
        auto_member_set = set(TRIG_DEFS.__members__.values())

        def __parse_auto(s1: Sequence[ExtendedEnum] | bool, s2: Sequence[ExtendedEnum] | bool) -> Sequence[ExtendedEnum]:
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
                    return auto_member_set.difference(s2)
                if not s2:
                    return auto_member_set
                return auto_member_set if s1 is True else set()
            return set(s1)

        if self.args['auto_off']:
            auto, excl_auto = set(), auto_member_set
        else:
            auto, excl_auto = __parse_auto(self.args['auto'], self.args['excl_auto']), __parse_auto(self.args['excl_auto'], self.args['auto'])

        # Check that args appearing in auto mask don't also appear in excl_auto mask
        if intersect := excl_auto.intersection(auto):
            err_invoker = get_action_from_parser_by_name(self.parser, 'excl_auto')
            auto_msg = ' '.join([v.name for v in auto])
            excl_auto_msg = ' '.join([v.name for v in excl_auto])
            err_msg = f'-auto {{{auto_msg}}} -excl-auto {{{excl_auto_msg}}}'
            common_msg = [v.name for v in intersect]
            raise ap.ArgumentError(err_invoker,
                                'Arguments specified in -auto must not also appear in -excl-auto'
                                ' (can\'t simultaneously be in both). I.e.:'
                                f'\n{underline_matches(err_msg, common_msg, match_all=True)}'
                                )

        return auto, excl_auto

    def parse(self) -> Mapping[Any, Any]:
        self.trig_opts = self._parse_option_values()

        if not self._check_bram_sz():
            raise ap.ArgumentTypeError('bram must hold at least one value of the provided size')

        if not self._check_auto_autooff:
            err_invoker = get_action_from_parser_by_name(self.parser, 'k')
            raise ap.ArgumentError(err_invoker,
                                   'k must be supplied if auto mode is turned on'
                                   )

        if not self._check_auto_autooff_for_k:
            err_invoker = get_action_from_parser_by_name(self.parser, 'auto')
            err_msg = ' '.join(sys.argv[1:])
            raise ap.ArgumentError(err_invoker,
                                'Supplied -auto and --auto-off simultaneously. A contradiction. Use one or the other. I.e.:'
                                f'\n{underline_matches(err_msg, ('-auto-off', '-auto'), match_all=True)}'
                                )

        k_vals = self._parse_k_vals()
        for field, v in k_vals.items():
            self.args[field] = v

        self.args['table_mode'] = self._parse_table_mode()
        self.args['prec_mode'] = self._parse_optimisation_mode()
        self.args['auto'], self.args['excl_auto'] = self._parse_auto()

        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            'Successfully parsed the command line args. Args is the following (after) parsing:'
            f'\n{log_wrapper.fill(str(self.args))}'
        ))

        return self.args


#######################################
# K (tolerance) estimation heuristics #
#######################################


def chebyshev_sin_N_k(k: np.floating) -> np.uint:
    """
    Based on the method used here:
    https://math.stackexchange.com/questions/1333449/could-this-approximation-be-made-simpler-solve-n-an-10k

    Returns the minimum degree of the partial sin chebyshev polynomial
    in order to be under the desired threshold, k
    """
    k = np.abs(np.log10(k))             # I.e. 0 < k < 1 => log(k) < 0 and the bound is 10^-k I.e. k is positive
    t = 4/(np.pi * np.e) * np.log((8 * 10**(2*k)) / np.pi**2)
    lw = sp.special.lambertw(t)
    n = np.pi/8 * np.exp(1 + lw) - 1.5
    return np.uint(np.ceil(np.real(n)))


def tan_k_N_pi4(k: np.floating) -> np.floating:
    """# Summary

    Finds the minimum domain size N for tan on the domain [0, pi/4]
    such that the average error is less than the tolerance.

    ## Parameters:
    tolerance: the desired average error tolerance.

    ## Returns:
    N: The minimum domain size.
    """

    """
    To find err within some threshold, k, consider:
    M.V.T states: tan(x_i + 1) - tan(x_i) = h * d/dx tan(x) = h * sec^2(x)
    To ensure the error is always <= k:

    h * max(|sec^2(x)|) <= k

    Rearranging:

    h <= k / max(|sec^2(x)|)

    tan(x) is obviously monotonically increasing on the interval [0, pi/4]
    => max(|sec^2(x)|) = (1/cos(pi/4))^2 = sqrt(2)^2 = 2 => h <= k/2
    """
    return np.ceil(np.pi / (2 * k) + 1)


def newton_raphson_atan_N(k: np.floating, k_tolerance: np.floating = 1e-7, max_iter: np.uint = 100) -> np.floating | None:
    """
    atan(x) may be written as 0.5*i*ln(1 - i*x) - 0.5*i*ln(1 + i*x)
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
    N_current = 8 # This value seems stable
    for _ in range(max_iter):
        # Define f(N) = ln(N^2 + 1) - 2 * N * k
        f_N = np.log(N_current**2 + 1) - 2 * N_current * k

        # Define f'(N) = (2N / (N^2 + 1)) - 2k (zero not possible for real N)
        denominator_f_prime = N_current**2 + 1
        f_prime_N = (2 * N_current / denominator_f_prime) - 2 * k

        if abs(f_prime_N) < k_tolerance:
            break

        # Newton-Raphson iteration
        try:
            N_next = N_current - f_N / f_prime_N
        except OverflowError | ZeroDivisionError:
            break

        if abs(N_next - N_current) < k_tolerance:
            return N_next

        N_current = N_next

    return


def sinc_k_N(x: np.ndarray[np.floating], epsilon: np.floating, max_iter: np.uint = 100) -> np.floating:
    """# Summary

    Find minimum N such that |cos(x) - cos_N(x)| < epsilon.
    Prioritize numerical stability.

    ## Parameters:
    x: input domain
    epsilon: desired error tolerance

    ## Returns:
    N: minimum N satisfying the error bound
    """

    if epsilon <= 0:
        raise ValueError('Epsilon value must be strictly positive.')

    x_array = np.atleast_1d(x).astype(np.double)
    nz_x = x_array[x_array != 0]
    log_x = np.log(np.abs(nz_x))
    log_epsilon = np.log(epsilon)

    # Start with rough estimate for each x
    N_values = np.maximum(0, (np.abs(nz_x) * np.e / 2 - 1).astype(np.int32))

    active_mask = np.ones(nz_x.size, dtype=np.bool)

    for _ in range(max_iter):

        if not np.any(active_mask):
            break

        N_active = N_values[active_mask]
        log_x_active = log_x[active_mask]
        log_error = (2*N_active + 2) * log_x_active - sp.special.gammaln(2*N_active + 3)
        satisfied = log_error < log_epsilon

        active_indices = np.where(active_mask)[0]
        active_mask[active_indices[satisfied]] = False

        N_values[active_mask] += 1
    else:
        msg = f'Warning: N > {max_iter} for x={x}, epsilon={epsilon}'
        LOGGER.warning(GENERATE_TRIG_LUTS_PREFIX.format(msg))
        print(msg)

    return np.max(N_values)


##########################################################
# Alternative functions for different optimisation modes #
##########################################################


def chebyshev_sin(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    return np.astype(np.polynomial.chebyshev.chebinterpolate(np.sin, deg=deg), dtype)


def compact_sinc(x: np.ndarray, dtype: np.dtype) -> np.ndarray[np.floating]:
    x = np.asarray(x, dtype=dtype)
    result = np.zeros_like(x)
    x_nz = x[x != 0]
    if x_nz.size > 0:
        abs_x_nz = np.abs(x_nz)
        lobe_number = np.floor(abs_x_nz)
        lobe_index = abs_x_nz - lobe_number
        envelope = 1.0 / (np.pi * np.abs(x_nz))
        sign = (-1) ** lobe_number
        canonical_values = _canonical_sinc_lobe_lookup(lobe_index)
        result[x != 0] = sign * envelope * canonical_values
    result[x == 0] = 1.0
    return result


def _canonical_sinc_lobe_lookup(lobe_index: np.ndarray) -> np.ndarray[np.floating]:
    """# Summary

    Vectorized canonical lobe lookup function.

    Args:
        lobe_index: numpy array of values in [0, 2) representing position within canonical lobe

    Returns:
        numpy array of canonical lobe values
    """
    # Convert lobe_index from [0, 2) to [0, \u03c0) for sinc calculation
    t = lobe_index * np.pi
    result = np.where(t == 0, 1.0, np.sin(t))
    return result


#######################################
# LUT domain generation & handling    #
#######################################


def generate_sin_cos_domain(phis: Mapping[str, np.ndarray[np.floating]], trig_parser: _TrigArgParser) -> None:
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
    sinusoid_modes = {k: v for k, v in trig_parser.args['table_mode'].items()
                      if k.value in TRIG_DEFS._SINUSOIDS.value}
    for k, table_mode in sinusoid_modes.items():

        bit_v = trig_parser.TRIG_LUTS_BITFIELD.get_member_via_name(k.name).value
        if bit_v ^ bit_v & trig_parser.trig_opts.lut_select:
            continue

        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            f'Generating {k.name} domain...'
        ))

        scale_factor = _calculate_scale_factor(trig_parser.args['table_mode'][k], trig_parser.args['prec_mode'][k])
        sz = trig_parser.n_entries // scale_factor
        if not trig_parser.args['no_quantize']:
            sz = quantize(sz, dtype=trig_parser.bw_type_int)

        match table_mode:
            case TRIG_OPT_MODE.MAX:
                LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
                    f'Max mode detected. Skipping {k.name} domain generation'
                ))
                continue
            case TRIG_OPT_MODE.HIGH:
                stop = np.pi / 2
            case TRIG_OPT_MODE.MED:
                raise NotImplementedError(f'Half table not yet supported for {k.name}')
            case TRIG_OPT_MODE.LOW:
                stop = np.pi * 2
                phis[k] = np.linspace(0, stop, sz)
                continue
            case _:
                assert_never(table_mode)

        # https://zipcpu.com/dsp/2017/08/26/quarterwave.html
        # Minimize harmonic distortion
        def domain_fn(sz: np.uint, scale_factor: np.uint) -> np.ndarray[np.floating]:
            n_luts = scale_factor * sz
            return np.astype((2 * np.pi * (np.arange(0, sz) + 0.5) / n_luts),
                             trig_parser.args['bw'])

        domain = domain_fn(sz, scale_factor)
        phis[k] = (domain, functools.partial(domain_fn, sz=sz*4, scale_factor=1))


def generate_tan_domain(phis: Mapping[str, np.ndarray[np.floating]], trig_parser: _TrigArgParser) -> None:
    """
    tan(-x) = -tan(x)
    => x |-> [0, pi/2)

    tan(x) = 1 / tan(0.5 * pi - x)
    I.e. if pi/4 <= x < pi/2
    let u = 0.5 * pi - x => u |-> (0, pi/4]
    => we can recover the interval x in [pi/4, pi/2) by:
    1 / tan(0.5 * pi - u)

    => x |-> [0, pi/4]
    """

    LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            f'Generating {TRIG_DEFS.TAN.name} domain...'
    ))

    table_mode = trig_parser.args['table_mode'][TRIG_DEFS.TAN]
    match table_mode:
        case TRIG_OPT_MODE.MAX:
            raise NotImplementedError(f'Max mode not yet supported for {TRIG_DEFS.TAN.name}')
        case TRIG_OPT_MODE.HIGH:
            k = trig_parser.args['tan_k']
            start = 0
            stop = np.pi / 4
            sz = np.uint(tan_k_N_pi4(k))
        case TRIG_OPT_MODE.MED:
            raise NotImplementedError(f'Half table not yet supported for {TRIG_DEFS.TAN.name}')
        case TRIG_OPT_MODE.LOW:
            sz = trig_parser.n_entries
            # Avoid pi/2 exactly=> 0.5 * pi - step_size = 0.5 * pi - (np.pi/4) / sz
            stop = (np.pi * (sz - 1)) / (2 * sz)
            start = -stop
        case _:
            assert_never(table_mode)

    if not trig_parser.args['no_quantize']:
        sz = quantize(sz, dtype=trig_parser.bw_type_int)

    phis[TRIG_DEFS.TAN] = (np.linspace(start, stop, sz, dtype=trig_parser.args['bw']),
                           functools.partial(np.linspace, start, stop, sz, dtype=trig_parser.args['bw'])
                          )


def generate_asin_acos_domain(xs: Mapping[str, np.ndarray[np.floating]], trig_parser: _TrigArgParser) -> None:
    """
    arcsin(-x) = -arcsin(x)
    => x |-> [0, 1]
    if x > sqrt(2) / 2
    => arcsin(x) = pi/2 - arcsin(sqrt(1 - x^2))
    => x |-> [0, sqrt(2) / 2]
    """
    arc_sinusoids = {k: v for k, v in trig_parser.args['table_mode'].items()
                     if k.value in TRIG_DEFS._ARC_SINUSOIDS.value}
    for k, table_mode in arc_sinusoids.items():

        bit_v = trig_parser.TRIG_LUTS_BITFIELD.get_member_via_name(k.name).value
        if bit_v ^ bit_v & trig_parser.trig_opts.lut_select:
            continue

        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            f'Generating {k.name} domain...'
        ))

        scale_factor = _calculate_scale_factor(trig_parser.args['table_mode'][k],
                                                              trig_parser.args['prec_mode'][k])
        sz = trig_parser.n_entries // scale_factor

        if not trig_parser.args['no_quantize']:
            sz = quantize(sz, dtype=trig_parser.bw_type_int)

        match table_mode:
            case TRIG_OPT_MODE.MAX:
                raise NotImplementedError(f'Max mode not yet supported for {k.name}')
            case TRIG_OPT_MODE.HIGH:
                """
                Per. https://github.com/topologicalhurt/Thesis/discussions/46
                The index recovery method is non-linearly distributed over the LUT.
                If the args are linearly spaced, it will introduce quantization error (I.e. major discontinuities)
                due to the relative sparsity or density of the lookup method.
                """
                inv_sqrt2 = 1.0 / np.sqrt(2.0)
                qwave_domain = np.linspace(0.0, inv_sqrt2, sz, dtype=trig_parser.args['bw'])
                domain_fn = lambda: np.linspace(-1.0, 1.0, sz*4, dtype=trig_parser.args['bw']) # noqa: E731

                xs[k] = (qwave_domain, domain_fn)

                continue
            case TRIG_OPT_MODE.MED:
                raise NotImplementedError(f'Half table not yet supported for {k.name}')
            case TRIG_OPT_MODE.LOW:
                start = -1
                stop = 1
            case _:
                assert_never(table_mode)

        xs[k] = (np.linspace(start, stop, sz, dtype=trig_parser.args['bw']),
                 functools.partial(np.linspace, start, stop=scale_factor*stop, sz=scale_factor*sz, dtype=trig_parser.args['bw'])
                )


def generate_atan_domain(xs: Mapping[str, np.ndarray[np.floating]], trig_parser: _TrigArgParser) -> None:
    """
    Firstly, the function is odd atan(-x) = -atan(x)
    => x |-> [0, inf)
    """

    LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
        f'Generating {TRIG_DEFS.ATAN.name} domain...'
    ))

    table_mode = trig_parser.args['table_mode'][TRIG_DEFS.ATAN]
    k = trig_parser.args['atan_k']

    # Rather confusingly, now we check the error against an 'error, error' tolerance
    N = newton_raphson_atan_N(k)
    err = 0.5 * np.log(N**2 + 1) / N
    err_threshold = TRIG_ATAN_OPTS.ERR_THRESHOLD.value * k
    if N is None or k > k + err_threshold or k < k - err_threshold:
        msg = ('---Building atan LUT---'
            f'\n\tCouldn\'t find an optimal table size N based on precision threshold {k}'
            ' Try using a bigger value.'
            f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
            )
        LOGGER.warning(GENERATE_TRIG_LUTS_PREFIX.format(msg))
        print(msg)
        return

    match table_mode:
        case TRIG_OPT_MODE.MAX:
            raise NotImplementedError(f'Max mode not yet supported for {TRIG_DEFS.ATAN.name}')
        case TRIG_OPT_MODE.HIGH:
            start = 0
            stop = np.int32(np.ceil(N))
            sz = stop
        case TRIG_OPT_MODE.MED:
            raise NotImplementedError(f'Half table not yet supported for {TRIG_DEFS.ATAN.name}')
        case TRIG_OPT_MODE.LOW:
            start = -N
            stop = N
            sz = trig_parser.n_entries
        case _:
            assert_never(table_mode)

    if not trig_parser.args['no_quantize']:
        sz = quantize(sz, dtype=trig_parser.bw_type_int)

    msg = ('---Building atan LUT---'
        f'\n\tFound optimal value for N {N}'
        f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
        f'\n\tSaved {trig_parser.bw_sz_bytes * (stop - sz)} many bytes'
        )
    LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(msg))
    print(msg)

    xs[TRIG_DEFS.ATAN] = (np.linspace(start, stop, sz, dtype=trig_parser.args['bw']),
                          functools.partial(np.linspace, start, stop, sz, dtype=trig_parser.args['bw'])
                         )


def generate_sinc_domain(xs: Mapping[str, np.ndarray[np.floating]], trig_parser: _TrigArgParser) -> None:
    """The envelope of the sinc function is 1 / (pi * x).
    We want to find the point x where the function has attenuated to at least k.
    1 / (pi * x) = k  => x = 1 / (pi * k)
    """

    LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
        f'Generating {TRIG_DEFS.SINC.name} domain...'
    ))

    table_mode = trig_parser.args['table_mode'][TRIG_DEFS.SINC]
    k = trig_parser.args['sinc_k']
    x_max = 1 / (np.pi * k)

    match table_mode:
        case TRIG_OPT_MODE.MAX:
            raise NotImplementedError(f'Max mode not yet supported for {TRIG_DEFS.SINC.name}')
        case TRIG_OPT_MODE.LOW:
            # Full table, store for x in [-x_max, x_max]
            sz = trig_parser.n_entries
            start = -x_max
            stop = x_max
        case TRIG_OPT_MODE.MED | TRIG_OPT_MODE.HIGH:
            # Half-symmetry, store for x >= 0
            sz = np.uint(np.ceil(TRIG_SINC_OPTS.SAMPLES_IN_MAIN_LOBE.value * x_max))
            start = 0
            stop = x_max
        case TRIG_OPT_MODE.MAX:
            raise NotImplementedError('There is currently no support for SINC max opt mode')
        case _:
            assert_never(table_mode)

    # Here, the heuristic to estimate N depends upon the input domain, x
    prev_sz = sz
    N = sinc_k_N(np.linspace(start, stop, sz, dtype=trig_parser.args['bw']), k)
    sz = N

    if not trig_parser.args['no_quantize']:
        sz = quantize(sz, dtype=trig_parser.bw_type_int)

    msg = ('---Building sinc LUT---'
        f'\n\tFound optimal value for N {N}'
        f'\n\tSaved {np.floor(prev_sz - N * trig_parser.bw_sz_bytes)} many bytes'
        )
    LOGGER.info(msg)
    print(msg)

    xs[TRIG_DEFS.SINC] = (np.linspace(start, stop, sz, dtype=trig_parser.args['bw']),
                          functools.partial(np.linspace, start, stop, sz, dtype=trig_parser.args['bw'])
                         )


###############
# Auxiliary   #
###############


def _generate_luts(trig_parser: _TrigArgParser, phis: Mapping[str, np.ndarray], xs: Mapping[str, np.ndarray]) -> Sequence[LUT]:
    lut_select = trig_parser.trig_opts.lut_select
    luts_to_w = []
    cmd_line_args = ' '.join(sys.argv[2:])
    for m, bit_v in zip(TRIG_DEFS.get_members(), trig_parser.TRIG_LUTS_BITFIELD.__members__.values()):
        if lut_select & bit_v.value:
            match m:
                case TRIG_DEFS.SIN | TRIG_DEFS.COS | TRIG_DEFS.TAN:
                    domains = phis
                case TRIG_DEFS.ASIN | TRIG_DEFS.ACOS | TRIG_DEFS.ATAN | TRIG_DEFS.SINC:
                    domains = xs
                case _:
                    assert_never(m)

            domain, domain_fn = domains[m]

            # fn_nominal is potentially different to fn_actual I.e. compact_sinc should be measured against sinc
            fn_nominal = _get_fn_from_optmode(m, trig_parser=trig_parser)
            fn_actual = TRIG_FN_DEFS.get_member_via_name(m.name).value[1]

            log_msg = []
            if m in domains:
                table = fn_nominal(domain)
                log_msg.append(f'\n\tDomain (first 10 values) {log_wrapper.fill(str(list(domain[:10])))}'
                               f'\n\tDomain (last 10 values) {log_wrapper.fill(str(list(domain[-10:])))}'
                               )
            else:
                table = fn_nominal()                            # Methods that don't need a domain I.e. Chebyshev

            lut_sz = trig_parser.bw_sz_bytes * table.size
            log_msg.append(f'\n\tGenerating {m.name} LUT...'
                           f'\n\tSize (bytes): {lut_sz}, Size (kB) {lut_sz / 1000:0.3f}'
                           f'\n\tTable mode: {trig_parser.args['table_mode'][m].name}'
                           f'\n\tLUT (first 10 values) {log_wrapper.fill(str(list(table[:10])))}'
                           f'\n\tLUT (last 10 values) {log_wrapper.fill(str(list(table[-10:])))}'
                           )
            log_msg = ''.join(reversed(log_msg))
            LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(log_msg))

            # The factor that indicates mix of precision and optimisation
            scale_factor = _calculate_scale_factor(trig_parser.args['table_mode'][m], trig_parser.args['prec_mode'][m])
            fn=fn_nominal.func if isinstance(fn_nominal, functools.partial) else fn_nominal
            lut = LUT(table=table,
                      domain=domain,
                      domain_fn=domain_fn,
                      type=LUT_TYPE.TRIG,
                      q_format=trig_parser.args['q'],
                      endianness=BYTEORDER.BIG,
                      bit_width=trig_parser.bw_sz,
                      table_sz=(lut_sz / 1000),
                      lop=trig_parser.args['prec_mode'][m],
                      table_mode=trig_parser.args['table_mode'][m],
                      scale_factor=scale_factor,
                      fn=fn,
                      cmd=underline_matches(cmd_line_args, f'--{m.name.lower()}', match_all=True)
                    )

            acc_metrics = LutAccMetrics(lut)
            luts_to_w.append(lut)

            acc_report = None
            if m in domains:
                test_axis: np.ndarray[np.floating | np.integer] = domain_fn()
                quant_acc_report = acc_metrics.assess_quantization_error(fn=fn_actual,
                                                                         axis=test_axis,
                                                                         oversample_factor=trig_parser.args['osf']
                                                                         )
                thd_acc_report = acc_metrics.assess_thd()

                acc_report = LUT_ACC_REPORT(quant_acc_report=quant_acc_report,
                                            thd_acc_report=thd_acc_report
                                           )

            print(acc_report)
            LOGGER.info(str(acc_report))

    return luts_to_w


def _write_out_luts(luts: Sequence[LUT], trig_parser: _TrigArgParser) -> None:
    if not trig_parser.args['nw']:
        hexManager = TrigLutManager(trig_parser.args['dir'])
        for lut in luts:

            LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
                f'Attempting to write out .hex file for {lut.fn.__name__}'
            ))

            fn = (f'{lut.fn.__name__}_{lut.bit_width}'
                f'_{lut.table_mode.name.lower()}_{lut.lop.name.lower()}'
                )
            hexManager.write_lut_to_hex(fn, lut, ow=True, target_order=BYTEORDER.BIG)

            LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
                f'.hex file was successfully written for {lut.fn.__name__}'
            ))
    else:
        LOGGER.info(GENERATE_TRIG_LUTS_PREFIX.format(
            '--nw (no write) option specified. Not writing out any .hex files'
        ))


def _calculate_scale_factor(table_mode: TRIG_OPT_MODE, table_prec: TRIG_PRECISION):
    """
    Calculate the 'scale' factor for a LUT I.e. the ratio between optimisation:precision
    """
    return max(table_mode.value * (TRIG_PRECISION.HIGHP.value - table_prec.value), 1)


def _get_fn_from_optmode(m: TRIG_DEFS, trig_parser: _TrigArgParser) -> Callable[[np.ndarray], np.ndarray[np.floating]]:
    """
    Return a different function based on the opt mode
    """
    opt_mode = trig_parser.args['table_mode'][m]
    match m:
        case TRIG_DEFS.SIN:
            if opt_mode == TRIG_OPT_MODE.MAX:
                LOGGER.info('Using chebyshev polynomial for sin')

                N = chebyshev_sin_N_k(trig_parser.args['k'])
                return functools.partial(chebyshev_sin, deg=N, dtype=trig_parser.args['bw'])
        case TRIG_DEFS.SINC:
            if opt_mode == TRIG_OPT_MODE.HIGH:
                LOGGER.info('Using compact sinc function for sinc')

                # Store canonical lobe only, use envelope estimation method after zero crossing
                return functools.partial(compact_sinc, dtype=trig_parser.args['bw'])

    # Default behaviour: return the function itself
    return TRIG_FN_DEFS.get_member_via_name(m.name).value[1]


if __name__ == '__main__':
    main()
