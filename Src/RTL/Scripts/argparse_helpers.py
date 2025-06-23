import os
import math
import collections
import argparse as ap
import numpy as np
import regex as re

from pathlib import Path
from typing import assert_never
from enum import Enum

from Allocator.Interpreter.dataclass import ExtendedEnum, FREQ, INT_STR_NPMAP, FLOAT_STR_NPMAP
from Allocator.Interpreter.helpers import underline_matches
from Allocator.Interpreter.exceptions import ExpectedFloatParseException, ExpectedPosFloatParseException, ExpectedPosIntParseException,\
ExpectedIntParseException


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
        raise ExpectedIntParseException('val must be an integer (only digits allowed)')
    return int(val)


def str2posint(val: str) -> int:
    if val.startswith('-'):
        raise ExpectedPosIntParseException('val must be a positive integer')
    return str2int(val)


def str2negint(val: str) -> int:
    if not val.startswith('-'):
        raise ExpectedPosIntParseException('val must be a negative integer')
    return str2int(val)


def str2float(val: str) -> float:
    matched = re.fullmatch(r'(\d+(?:\.\d+)?)', val)
    if matched is None:
        raise ExpectedFloatParseException(f'Couldn\'t parse float from {val}')
    return float(matched.group(0))


def str2posfloat(val: str) -> float:
    if val.startswith('-'):
        raise ExpectedPosFloatParseException('val must be a positive floating point number')
    return str2float(val)


def str2negfloat(val: str) -> float:
    if not val.startswith('-'):
        raise ExpectedPosFloatParseException('val must be a negative floating point number')
    return str2float(val)


def str2float_with_atmost_n_floating_digits(val: str, n: int) -> float:
    if n == 0:
        return str2int(val) # if n == 0 return the value as an integer
    if n < 1:
        raise ValueError('n must be at-least 1 (I.e. match at-least 1 many floating point digits)')

    matched = re.fullmatch(rf'(\d+(?:\.\d+{{1,{n}}})?)', val)
    if matched is None:
        raise ExpectedFloatParseException(f'Expected a float with at-least n ({n}) many floating point places but got {val}')
    return float(matched.group(0))


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
        return target_enum.get_member_via_val_from_name(val)

    try:
        # Indicates we got an integer (I.e. val |-> field)
        return target_enum.get_member_via_name_from_val(posint)
    except ValueError:
        raise ap.ArgumentTypeError(f'val must be in the provided range of the enum {target_enum.__name__}:'
                                    f' {target_enum.fields()} |-> {target_enum.vals()}'
                                    f' (got {val} instead)'
                                    )

def eval_arithmetic_str_unsafe(val: str) -> float:
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
        else:
            assert_never(k)

        if not valid_counts:
            raise ap.ArgumentTypeError(f'Count, {v}, of operation {k} is too large.'
                                       f' Try simplifying your expression: \n{underline_matches(v, k, match_all=True)}'
                                       )

    val = val.replace('^', '**')

    allowed_globals = {
        '__builtins__': {},
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'pow': pow,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'pi': math.pi,
        'e': math.e,
    }

    return float(eval(val, allowed_globals, {})) # noqa: F401


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
    if not os.path.isfile(val) and not os.path.isdir(val):
        raise ap.ArgumentTypeError(f'Given path {val} does not exist')
    return Path(val)


def str2freq(val: str | float, granularity: FREQ = FREQ.KHZ) -> int:
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


def str2bitwidth(v: str | int, is_int: bool = False) -> tuple[int, float]:
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
            return type_mapping.get_member_via_value_from_name(v).value
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
    return type_mapping.get_member_via_name_from_value(v).value


def bools2bitstr(*args: bool, in_first_msb = True) -> int:
    result = 0
    if in_first_msb:
        args = reversed(args)
    for i, a in enumerate(args):
        result |= int(a) << i
    return result
