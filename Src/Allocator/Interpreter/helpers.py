import argparse as ap
import regex as re
import os
import math
import collections
import xxhash

from pathlib import Path
from typing import assert_never
from collections.abc import Iterable, Hashable


def fast_stable_hash(data: Hashable) -> int:
    return xxhash.xxh64(data).intdigest()


def combined_fast_stable_hash(data: Iterable[Hashable]) -> int:
    hasher = xxhash.xxh64()
    for val in data:
        hasher.update(val)
    return hasher.intdigest()


def underline_match(text: str, to_match: Iterable, match_all: bool = False, literal: bool = True) -> str | None:
    """ # Summary

    Generates a string that underlines a regex match in a given text.

   ## Args:
        text: The original string.
        to_match: The object to be indexed that indicates the part of the string to underline.
        match_all: Determines whether to underline every occurance of match rather than the first found.
        literal: Determines whether to match against to_match as a literal or pattern

   ## Returns:
        A string containing the original text and the underline.
        Returns an error message if the match is None.
    """
    if match_all:
        # Either match every pattern in to_match if it is a collection object
        # or, if it is a singular string, match that against the entire text.
        if isinstance(to_match, str):
            to_match = re.escape(to_match)
        else:
            to_match = '|'.join(re.escape(m) for m in to_match)

        underlined = []
        prev_start = 0
        for m in re.finditer(to_match, text):
            if m is None:
                return None
            start_index = m.start(0)
            end_index = m.end(0)
            underlined.append(' ' * (start_index - prev_start))
            underlined.append('^' * (end_index - start_index))
            prev_start = end_index

        return f'{text}\n{"".join(underlined)}'

    if not isinstance(to_match, str):
        raise TypeError('unless match_all is turned on, match must be a singular string object'
                        ' (not a collection).')

    start_index = text.find(to_match)
    if start_index == -1:
        return None
    end_index = start_index + len(to_match)

    underline = ' ' * start_index
    underline += '^' * (end_index - start_index)
    return f'{text}\n{underline}'


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
            raise ap.ArgumentTypeError(f'Division by zero in expression: \n{underline_match(val, match.group(1))}')

    # Check operations are between all adjacent numbers
    digits_no_op = re.findall(r'\d+(?=\s+\d+)', val)
    if any(digits_no_op):
        raise ap.ArgumentTypeError(f'Digits must have operations in-between themselves in expression:'
                                   f'\n{underline_match(val, digits_no_op, match_all=True)}'
                                   )

    # Avoid resource starving by checking excessively large numbers
    large_digits = re.findall(r'\d{10,}', val)
    if any(large_digits):
        raise ap.ArgumentTypeError(f'No digit must exceed >= 10 places long in expression:'
                                   f'\n{underline_match(val, large_digits, match_all=True)}'
                                   )

    # Avoid resource starving by checking for large powers
    large_powers = re.findall(r'(?:\*\*|\^)\s*(\d{2,})', val)
    if any(large_powers):
        raise ap.ArgumentTypeError(f'No digit can be raised to a power >= 2 places long in expression:'
                                   f'\n{underline_match(val, large_powers, match_all=True)}'
                                   )

    # Avoid resource starving by checking operation counts
    count = collections.Counter(val)
    valid_counts = True
    for k, v in count.items():

        if not k.strip() or k.isdigit():
            continue

        match k:
            case '*' | '/' | '%':
                valid_counts = v < 10
            case '**' | '^':
                valid_counts = v < 5
            case '+' | '-':
                valid_counts = v < 20
            case _:
                assert_never(k)

        if not valid_counts:
            raise ap.ArgumentTypeError(f'Count, {v}, of operation {k} is too large.'
                                       f' Try simplifying your expression: \n{underline_match(v, k, match_all=True)}'
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


def tri_sign_2d(a: tuple, b: tuple, c: tuple) -> float:
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])
