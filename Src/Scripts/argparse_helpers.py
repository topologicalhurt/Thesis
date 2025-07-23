"""
------------------------------------------------------------------------
Filename: 	argparse_helpers.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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


import ast
import operator
import collections
import itertools
import argparse as ap
import numpy as np
import regex as re

from collections.abc import Mapping
from pathlib import Path
from typing import Any, assert_never
from enum import Enum

from Allocator.Interpreter.nptypes import INT_STR_NPMAP, FLOAT_STR_NPMAP
from Allocator.Interpreter.dataclass import ExtendedEnum, FREQ
from Allocator.Interpreter.helpers import underline_matches

from Scripts.exceptions import ExpectedFloatParseException, ExpectedPosFloatParseException, ExpectedPosIntParseException, ExpectedIntParseException
from Scripts.consts import META_INFO, SRC_DIR
from Scripts.decorators import warning


_, FLOAT32 = FLOAT_STR_NPMAP.FLOAT32.value


def get_action_from_parser_by_name(parser: ap.ArgumentParser, arg_name: str) -> ap.Action | None:
    """# Summary

    ## Args:
        parser (ap.ArgumentParser): the argument parser to fetch arg_name from
        arg_name (str): the argument name to fetch from parser

    ## Returns:
        ap.Action | None: the action if found, else none
    """
    return next((action for action in parser._actions
                 if action.dest == arg_name), None)


def str2int(val: str) -> int:
    if not val.isdigit():
        raise ExpectedIntParseException(f'Couldn\'t parse integer from {val}')
    return int(val)


def str2posint(val: str) -> int:
    if val.startswith('-'):
        raise ExpectedPosIntParseException(f'Couldn\'t parse positive integer from {val}')
    return str2int(val)


def str2negint(val: str) -> int:
    if not val.startswith('-'):
        raise ExpectedPosIntParseException(f'Couldn\'t parse negative integer from {val}')
    return str2int(val)


def str2float(val: str) -> np.floating:
    matched = re.fullmatch(r'(\d+(?:\.\d+)?)', val)
    if matched is None:
        raise ExpectedFloatParseException(f'Couldn\'t parse float from {val}')
    return FLOAT32(matched.group(0))


def str2posfloat(val: str) -> np.floating:
    if val.startswith('-'):
        raise ExpectedPosFloatParseException(f'Couldn\'t parse positive float from {val}')
    return str2float(val)


def str2negfloat(val: str) -> np.floating:
    if not val.startswith('-'):
        raise ExpectedPosFloatParseException(f'Couldn\'t parse negative float from {val}')
    return str2float(val)


def str2float_with_atmost_n_floating_digits(val: str, n: int) -> np.floating:
    if n == 0:
        return str2int(val) # if n == 0 return the value as an integer
    if n < 1:
        raise ValueError('n must be at-least 1 (I.e. match at-least 1 many floating point digits)')

    matched = re.fullmatch(rf'(\d+(?:\.\d+{{1,{n}}})?)', val)
    if matched is None:
        raise ExpectedFloatParseException(f'Expected a float with at-least n ({n}) many decimal point places but got {val}')
    return FLOAT32(matched.group(0))


def str2num(val: str) -> np.floating | int:
    if val.find('.'):
        return str2float(val)
    return str2int(val)


def str2posnum(val: str) -> np.floating | int:
    if val.find('.'):
        return str2posfloat(val)
    return str2posint(val)


def str2negnum(val: str) -> np.floating | int:
    if val.find('.'):
        return str2negfloat(val)
    return str2negint(val)


def num_in_range(val: np.floating | int, r: range,
                lower_inclusive: bool = True,
                upper_inclusive: bool = True) -> np.floating | int:
    if (lower_inclusive and val < r.start) or (upper_inclusive and val > r.stop) or\
        (not lower_inclusive and val <= r.start) or (not lower_inclusive and val >= r.stop):
        lower_symb = '[' if lower_inclusive else '('
        upper_symb = ']' if upper_inclusive else ')'
        if isinstance(val, FLOAT32):
            raise ap.ArgumentTypeError(f'Expected a float in the range: {lower_symb}{r.start}, {r.stop}{upper_symb}'
                                        f' but got {val}'
                                        )
        if isinstance(val, int):
            raise ap.ArgumentTypeError(f'Expected an integer in the range: {lower_symb}{r.start}, {r.stop}{upper_symb}'
                            f' but got {val}'
                            )
        assert_never(f'Value should be an integer or float but got {val} instead')
    return val


def str2int_in_range(val: str, r: range,
                    lower_inclusive: bool = True,
                    upper_inclusive: bool = True) -> np.floating:
    val = str2int(val)
    return num_in_range(val, r, lower_inclusive=lower_inclusive, upper_inclusive=upper_inclusive)


def str2float_in_range(val: str, r: range,
                    lower_inclusive: bool = True,
                    upper_inclusive: bool = True) -> np.floating:
    val = str2float(val)
    return num_in_range(val, r, lower_inclusive=lower_inclusive, upper_inclusive=upper_inclusive)


def str2enumval(val: str, target_enum: ExtendedEnum) -> Enum:
    try:
        posint = str2posint(val)
    except ExpectedPosIntParseException:
        raise ap.ArgumentTypeError(f'val must be a positive integer in the provided range of the enum:'
                f' {target_enum.__name__}: {target_enum.fields()} |-> {target_enum.vals()}'
                f' (got {val} instead)'
                )
    except ExpectedIntParseException:
        # Indicates we got a string (I.e. field |-> val)
        if val not in target_enum:
            raise ap.ArgumentTypeError('val must be one of the provided field names:'
                                        f' {target_enum.fields()} (got {val} instead)'
                                        )
        return target_enum.get_member_via_name(val)

    try:
        # Indicates we got an integer (I.e. val |-> field)
        return target_enum.get_member_via_value(posint)
    except ValueError:
        raise ap.ArgumentTypeError(f'val must be in the provided range of the enum {target_enum.__name__}:'
                                    f' {target_enum.fields()} |-> {target_enum.vals()}'
                                    f' (got {val} instead)'
                                    )


@warning('Function {f_name} can evaluate potentially unsafe arithmetic expressions. Enable with caution.')
def eval_arithmetic_str_safe(val: str) -> np.floating:
    """ # Summary

    Evaluates a string expression allowing only basic arithmetic operations
    and functions from the math module.

    ## WARNING!
    No guarantee's about safety as this hasn't been formally verified yet

    ## Args:
        expression_string: The string to evaluate.

    ## Returns:
        The result of the evaluation.
    """
    # Check only arithmetic options will be evaluated
    if not re.fullmatch(r'[\d\s\+\-\*\/\(\)\.\%\^]+', val):
        raise ap.ArgumentTypeError('Expression must only contain digits & arithmetic symbols')

    # Avoid division by zero
    for match in re.finditer(r'\(?.*\)?\/(\d+)', val):
        if int(match.group(1)) == 0:
            raise ap.ArgumentTypeError(f'Division by zero in expression: \n{underline_matches(val, match.group(1))}')

    # Check operations are between all adjacent numbers
    digits_no_op = re.findall(r'\d+(?=\s+\d+)', val)
    if any(digits_no_op):
        raise ap.ArgumentTypeError(f'Digits must have operations in-between themselves in expression:'
                                   f'\n{underline_matches(val, digits_no_op, match_all=True)}'
                                   )

    # Avoid resource starving by checking excessively large numbers
    large_digits = re.findall(r'\d{10,}', val)
    if any(large_digits):
        raise ap.ArgumentTypeError(f'No digit must exceed >= 10 places long in expression:'
                                   f'\n{underline_matches(val, large_digits, match_all=True)}'
                                   )

    # Avoid resource starving by checking for large powers
    large_powers = re.findall(r'(?:\*\*|\^)\s*(\d{2,})', val)
    if any(large_powers):
        raise ap.ArgumentTypeError(f'No digit can be raised to a power >= 2 places long in expression:'
                                   f'\n{underline_matches(val, large_powers, match_all=True)}'
                                   )

    # Avoid resource starving by checking operation counts
    count = collections.Counter(val)
    valid_counts = True
    for k, v in count.items():

        if not k.strip() or k.isdigit():
            continue

        if k in ('*', '/', '%'):
            valid_counts = v < 10
        elif k in ('**', '^'):
            valid_counts = v < 5
        elif k in ('+', '-'):
            valid_counts = v < 20

        if not valid_counts:
            raise ap.ArgumentTypeError(f'Count, {v}, of operation {k} is too large.'
                                       f' Try simplifying your expression: \n{underline_matches(v, k, match_all=True)}'
                                       )

    val = val.replace('^', '**')

    bin_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.BinOp: ast.BinOp
    }

    un_ops = {
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.UnaryOp: ast.UnaryOp,
    }

    ops = tuple(bin_ops) + tuple(un_ops)
    tree = ast.parse(val, mode='eval')

    # Modified from https://stackoverflow.com/a/68732605
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            return FLOAT32(node.value)
        if isinstance(node, ast.BinOp):
            left = _eval(node.left) if isinstance(node.left, ops) else node.left.value
            if isinstance(node.right, ops):
                right = _eval(node.right)
            else:
                right = node.right.value
            return bin_ops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.operand, ops):
                operand = _eval(node.operand)
            else:
                operand = node.operand.value
            return un_ops[type(node.op)](operand)
        raise SyntaxError(f'Bad syntax, {type(node)}')

    return FLOAT32(_eval(tree))


def str2bool(val: str) -> bool:
    if isinstance(val, bool):
        return val
    val = val.lower()
    if val in ('yes', 'true', 't', 'y', '1'):
        return True
    elif val in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ap.ArgumentTypeError('Boolean val expected')


def str2path(val: str) -> Path:
    path = Path(val)
    if not path.exists():
        raise ap.ArgumentTypeError(f'Given path {val} does not exist')
    return path


def str2path_belongs_in(val: str, ancestor: Path, enforce_exists: bool = True) -> Path:
    fp: Path = Path(val)
    if not fp.is_absolute():
        fp = str2relpath(val, root=ancestor, enforce_exists=enforce_exists)
    try:
        fp.relative_to(ancestor)
    except ValueError:
        raise ap.ArgumentTypeError(f'Given path {val} must be a subpath of {ancestor}')
    return fp


def str2relpath(val: str, root: str = SRC_DIR, enforce_exists: bool = True,
                excluded: set = {'.git', '__pycache__', '.venv', 'node_modules', 'obj_dir', '.cache'}) -> Path:
    # Try direct join from Src if it exists
    project_root = META_INFO.GIT_ROOT
    search_root = project_root / root # Default search root is Src directory
    src_direct_path = search_root / val
    if src_direct_path.exists():
        return src_direct_path

    if not enforce_exists:
        return src_direct_path

    # Search for the file starting from Src directory only
    filename = Path(val).name
    matches = []
    for match in search_root.rglob(filename):
        # Skip if any parent directory is in excluded set
        if not any(parent.name in excluded for parent in match.parents):
            matches.append(match)

    if not matches:
        raise ap.ArgumentTypeError(f'File {val} not found in {search_root}')

    # Sort by depth (shallowest first) and return the first match
    shallowest_match = min(matches, key=lambda p: len(p.relative_to(search_root).parts))
    return shallowest_match


def str2freq(val: str, granularity: FREQ = FREQ.KHZ) -> int:
    try:
        n_accepted_digits = int(np.log10(granularity.value))
        val = str2float_with_atmost_n_floating_digits(val, n_accepted_digits)
    except ExpectedFloatParseException:
        # n_accepted_digits >= 1 as if n_accepted_digits = 0, behaviour is to cast to integer
        err_regex = rf'\d*\.(\d{{0,{n_accepted_digits}}})'
        err_msg = f'{underline_matches(val, err_regex, literal=False)} instead'
        raise ap.ArgumentTypeError('Given value couldn\'t be parsed as an appropriate frequency value.'
                                   f' Expected, with frequency measurement set to: {granularity} at-most'
                                   f' {n_accepted_digits} floating point digit places. But got:'
                                   f' {err_msg}'
                                   )
    return int(val * granularity.value)


def str2bitwidth(v: str, is_int: bool = False) -> tuple[int, np.floating]:
    type_mapping = FLOAT_STR_NPMAP if not is_int else INT_STR_NPMAP
    if isinstance(v, str):
        if v.isdigit():
            # If arg is purely digits attempt to convert to positive integer
            v = str2posint(v)
        else:
            # If the arg is a mix of char & digits
            v = v.upper()
            if v not in type_mapping:
                raise ap.ArgumentTypeError('If value is specified by type alias it must be one'
                                           f' of {type_mapping.fields()} but got {v} instead'
                                          )
            return type_mapping.get_member_via_name(v).value

    v: int
    if v < 16 or v > 128:
        valid_floatw = ' '.join(type_mapping.fields())
        raise ap.ArgumentTypeError('Value must be positive int in range [16, 128]'
                                   f' but got {v} instead. I.e.:'
                                   f'\n{underline_matches(valid_floatw, lambda char: char.isdigit())}'
                                   )
    if v not in type_mapping:
        raise ap.ArgumentTypeError('If value is specified as a digit it must be one'
                                    f' of {[v for v in type_mapping.values() if isinstance(v, int)]} but got {v} instead'
                                    )
    return type_mapping.get_member_via_value(v).value


def get_non_flags(parser: ap.ArgumentParser) -> Mapping[str, Any]:
    non_flags = [action.option_strings for action in parser._actions]
    non_flags = [opt.removeprefix('-').replace('-', '_') for opt in
                 itertools.chain.from_iterable(non_flags)
                 if not opt.startswith('--')]   # Excl. non flags
    non_flags.extend([action.dest for action in parser._get_positional_actions()]) # Excl. positionals
    return non_flags
