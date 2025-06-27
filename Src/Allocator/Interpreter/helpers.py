"""
------------------------------------------------------------------------
Filename: 	helpers.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Common helper / utility functions

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""


import itertools
import xxhash
import importlib
import regex as re
import numpy as np

from collections.abc import Callable, Iterable, Hashable, Sequence


def combined_fast_stable_hash(data: Iterable[Hashable]) -> int:
    hasher = xxhash.xxh64()
    for val in data:
        hasher.update(val)
    return hasher.intdigest()


def machine_has_quad_float_support() -> bool:
    try:
        # Try to access the float128 type.
        return hasattr(np, 'float128')
    except (TypeError, AttributeError):
        print('Warning: 128-bit float (float128) is not supported on this platform. Skipping.')
        return False


def machine_has_extended_float_support() -> bool:
    """Check if the machine supports 80-bit extended precision floats (longdouble on x86)."""
    try:
        # Check if longdouble is actually extended precision (80-bit) vs just double (64-bit)
        return hasattr(np, 'longdouble') and np.finfo(np.longdouble).bits > 64
    except (TypeError, AttributeError):
        return False


dataclasses = importlib.import_module('.dataclass', package='Allocator.Interpreter')
ExtendedEnum = dataclasses.ExtendedEnum


def fast_stable_hash(data: Hashable) -> int:
    return xxhash.xxh64(data).intdigest()


def pairwise(t: Iterable) -> zip:
    it = iter(t)
    return zip(it,it)


def underline_match(text: str, to_match: str,
                     start_index: int = 0, end_index: int | None = None) -> Sequence[str] | None:
    """# Summary

    Underlines a single match. Parameters alias underline_matches (see: underline_matches)
    """
    i = text.find(to_match, start_index, end_index)
    if i == -1:
        return

    if end_index is None:
        end_index = i + len(to_match)

    underlined = []
    underlined.append(' ' * (i - start_index))
    underlined.append('^' * (end_index - i))
    return end_index, underlined


def underline_matches(text: str, to_match: Iterable | str | Callable[[str], bool],
                      start_index: int = 0, end_index: int | None = None,
                      match_all: bool = False, literal: bool = True) -> str | None:
    """ # Summary

    Generates a string that underlines a regex match or matches in a given text.

   ## Args:
        text: The original string.
        to_match: The object or object(s) to be indexed that indicates the part of the string to underline.\
        May also be a predicate / condition matched against the string per char
        start_index: The beginning of the string to search in
        end_index: The end ofthe string to search in
        match_all: Determines whether to underline every occurance of match rather than the first found.
        literal: Determines whether to match against to_match as a literal or pattern

   ## Returns:
        A string containing the original text and the underline.
        Returns an error message if the match is None.
    """
    predicate_match = False
    if isinstance(to_match, Callable):
        to_match = list(set(char for char in text if to_match(char)))
        predicate_match = True

    underlined = []
    prev_i = start_index
    if match_all or predicate_match:
        # Either match every pattern in to_match if it is a collection object
        # or, if it is a singular string, match that against the entire text.
        if isinstance(to_match, str):
            to_match = re.escape(to_match) if literal else to_match
        else:
            to_match = '|'.join(re.escape(m) if literal else m for m in to_match)

        for m in re.finditer(to_match, text, pos=start_index, endpos=end_index):
            if m is None:
                return None
            i, txt = underline_match(text, m.group(0), prev_i)
            underlined.extend(txt)
            prev_i = i

        return f'{text}\n{"".join(underlined)}'

    if not isinstance(to_match, str):
        underlined = []
        for m in to_match:
            if (match := underline_match(text, m, prev_i)) is None:
                continue
            i, txt = match
            underlined.extend(txt)
            prev_i = i
        return f'{text}\n{"".join(underlined)}'

    _, txt = underline_match(text, to_match, start_index, end_index)
    underlined.extend(txt)
    return f'{text}\n{"".join(underlined)}'


def pad_lists_to_same_length(list1: list, list2: list) -> tuple[list, list]:
    """# Summary

    Pad the shorter list by extending it with its last element to match the longer list's length.

    ## Args:
        list1: First list
        list2: Second list

    ## Returns:
        tuple[list, list]: A tuple of (padded_list1, padded_list2) where both lists have the same length
    """
    if not list1 or not list2:
        raise ValueError('Provided lists must be non-empty')

    len1, len2 = len(list1), len(list2)

    if len1 == len2:
        return list1, list2

    # Determine which list is shorter and pad it
    if len1 < len2:
        # Pad list1 to match list2's length
        padded_list1 = list1 + list(itertools.repeat(list1[-1], len2 - len1))
        return padded_list1, list2
    else:
        # Pad list2 to match list1's length
        padded_list2 = list2 + list(itertools.repeat(list2[-1], len1 - len2))
        return list1, padded_list2


def tri_sign_2d(a: tuple, b: tuple, c: tuple) -> float:
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])
