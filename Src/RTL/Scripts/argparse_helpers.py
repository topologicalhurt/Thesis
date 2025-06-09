import os
import math
import collections
import argparse as ap
import regex as re

from pathlib import Path
from typing import assert_never
from enum import Enum


from Allocator.Interpreter.dataclass import ExtendedEnum
from Allocator.Interpreter.helpers import underline_matches
from Allocator.Interpreter.exceptions import PosIntParseException, ExpectedIntParseException


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


def str2posint(value: str) -> int:
    if value.startswith('-'):
        raise PosIntParseException('Value must be a positive integer')
    if not value.isdigit():
        raise ExpectedIntParseException('Value must be an integer (only digits allowed)')
    return int(value)


def str2float(value: str) -> float:
    matched = re.fullmatch(r'(\d+(?:\.\d+)?)', value)
    if matched is None:
        raise ap.ArgumentTypeError(f'Couldn\'t parse float from {value}')
    return float(matched.group(0))


def str2enumval(value: str, target_enum: ExtendedEnum) -> Enum:
    try:
        posint = str2posint(value)
    except PosIntParseException:
        raise ap.ArgumentTypeError(f'Value must be a positive integer in the provided range of the enum:'
                f' {target_enum.__name__}: {target_enum.fields()} |-> {target_enum.values()}'
                f' (got {value} instead)'
                )
    except ExpectedIntParseException:
        # Indicates we got a string (I.e. field |-> value)
        if value not in target_enum:
            raise ap.ArgumentTypeError('Value must be one of the provided field names:'
                                        f' {target_enum.fields()} (got {value} instead)'
                                        )
        return target_enum.get_value_from_name(value)

    try:
        # Indicates we got an integer (I.e. value |-> field)
        return target_enum.get_name_from_value(posint)
    except ValueError:
        raise ap.ArgumentTypeError(f'Value must be in the provided range of the enum {target_enum.__name__}:'
                                    f' {target_enum.fields()} |-> {target_enum.values()}'
                                    f' (got {value} instead)'
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
        raise ap.ArgumentTypeError('Boolean value expected.')


def str2path(val: str) -> Path:
    if not os.path.isfile(val) and not os.path.isdir(val):
        raise ap.ArgumentTypeError(f'Given path {val} does not exist')
    return Path(val)


def bools2bitstr(*args: bool, in_first_msb = True) -> int:
    result = 0
    if in_first_msb:
        args = reversed(args)
    for i, a in enumerate(args):
        result |= int(a) << i
    return result
