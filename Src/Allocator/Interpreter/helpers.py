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


import functools
import itertools
import xxhash
import regex as re
import numpy as np

from typing import Any

from collections.abc import Callable, Iterable, Hashable, Mapping, Sequence


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


def quantize(x: np.floating, dtype: np.uint) -> np.uint:
    return 1 << dtype(np.ceil(np.log2(x)))


def largest_dtype_of_kind(kind: np.dtype) -> np.dtype:
    """# Summary

    Get the largest avaliable bit-size for a numpy dtype
    """
    # Filter np.sctypeDict to find all concrete types that are subclasses of `kind`.
    candidate_types = []
    for type_class in set(np.sctypeDict.values()):
        if isinstance(type_class, type) and issubclass(type_class, kind):
            try:
                # Check if it's a concrete type by trying to instantiate its dtype.
                # Abstract types will raise a TypeError.
                if np.dtype(type_class).itemsize:
                    candidate_types.append(type_class)
            except TypeError:
                continue

    if not candidate_types:
        raise ValueError(f'Could not find any concrete numpy dtypes for kind {kind}')

    return max(candidate_types, key=lambda x: np.dtype(x).itemsize)


def find_nearest(array: np.ndarray[np.number], values: np.ndarray[np.number]) -> np.ndarray[np.number]:
    """
    For each value in `values`, find the nearest value in `array`.
    """
    array = np.asarray(array)
    values = np.asarray(values)
    diff = np.abs(array[:, np.newaxis] - values)
    indices = diff.argmin(axis=0)
    return array[indices]


def sort_relative_to(to_sort: Iterable[Any], mask: Mapping[Any, int]) -> Iterable[Any]:
    """# Summary

    Sorts an iterable `to_sort` based on the integer values in a `mask` mapping.
    Items in `to_sort` that are present in the `mask` are sorted first, according to the mask's values.
    Items not in the `mask` are sorted after all masked items, maintaining their natural relative order.
    If two items have the same rank in the mask, their natural order is used as a tie-breaker.

    ## Args:
        to_sort (Iterable[Any]): The iterable to be sorted. Can contain duplicates.
        mask (Mapping[Any, int]): A mapping from values in `to_sort` to integer sort keys.

    ## Returns:
        Iterable[Any]: A new list containing the items from `to_sort` sorted according to the rules.

    ## Examples:
        >>> X = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
        >>> mask = {"a": 0, "d": 0, "h": 0, "b": 1, "c": 1, "e": 1, "i": 1, "f": 2, "g": 2}
        >>> sort_relative_to(X, mask)
        ['a', 'd', 'h', 'b', 'c', 'e', 'i', 'f', 'g']

        >>> X = ["a", "b", "c", "d", "e", "f"]
        >>> mask = {"a": 1, "c": 0}
        >>> sort_relative_to(X, mask)
        ['c', 'a', 'b', 'd', 'e', 'f']

        >>> X = ["a", "a", "a", "b", "c"]
        >>> mask = {'a': 0, 'c': 1, 'b': 2}
        >>> sort_relative_to(X, mask)
        ['a', 'a', 'a', 'c', 'b']
    """
    return sorted(to_sort, key=lambda item: (mask.get(item, float('inf')), item))


def rename_keys(d: dict, rename_map: dict) -> None:
    if set(rename_map.keys()).issubset(d.keys()):
        for k, v in rename_map.items():
            val = d.pop(k)
            d[v] = val


def join_regex(*regex: str, non_capture: bool = True, or_join: bool = True) -> str:
    def _increment_match(match, i: int):
        return f'\\{int(match.group(0)[1:]) + i}'

    wrapped_patterns = []
    i = 0
    for pattern in regex:
        if re.search(r'\\\d+', pattern):
            wrapped_patterns.append(re.sub(r'\\\d+',
                                    functools.partial(_increment_match, i=i), pattern)
                                   )
            i += 1
            continue
        wrapped_patterns.append(pattern)

    wrapped_patterns = [f'(?:{pattern})' if non_capture else f'({pattern})' for pattern in wrapped_patterns]
    if or_join:
        return '|'.join(wrapped_patterns)
    return ''.join(wrapped_patterns)


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
            if (match := underline_match(text, m.group(0), prev_i)) is None:
                continue
            i, txt = match
            underlined.extend(txt)
            prev_i = i

    elif not isinstance(to_match, str):
        for m in to_match:
            if (match := underline_match(text, m, prev_i)) is None:
                continue
            i, txt = match
            underlined.extend(txt)
            prev_i = i
    else:
        if (match := underline_match(text, to_match, start_index, end_index)) is None:
            # TODO: fix so match greedily first, then replace start_index with where match fails
            underlined.append(' ' * start_index)
            underlined.append('^')
        else:
            _, txt = match
            underlined.extend(txt)

    return f'{text}\n{''.join(underlined)}'


def underline_first_non_captured_group(groups: re.Pattern | str, string: str) -> str | Sequence[str]:
    """# Summary

    Returns the first group that couldn't be captured in the list of groups,
    all of the matched groups O.T.W
    """
    groups = re.findall(r'\([^()]+\)[+?*]?', groups)                                    # First of all, extract the groups into a list
    matches = []
    j = 0                                                                               # Tracks last matches' end position
    for i, group in enumerate(groups):
        if not (match := re.match(join_regex(*groups[:i+1], or_join=False), string, partial=True)) or match.partial:
            print(groups[:i+1])
            return f'\n{underline_matches(string, group, start_index=j, literal=False)}'
        matches.append(match.group(i+1))
        j = match.end()
    return matches


def greater_than_n_regex(n: int) -> str:
    """# Summary

    Returns the regex for >= n
    """
    result = [r'\d*']
    i = 0   # Value will be log10(n) after loop
    while n:
        d, r = divmod(n, 10)
        result.append(rf'[{r}-9]')
        n = d
        i += 1
    result = reversed(result)
    return join_regex(fr'[1-9]\d{{{i},}}', ''.join(result))


def pairwise(t: Iterable) -> zip:
    it = iter(t)
    return zip(it,it)


def fast_stable_hash(data: Hashable) -> int:
    return xxhash.xxh64(data).intdigest()


def pad_lists_to_same_length(list1: list, list2: list, value: Any = None,
                             repeat_last: bool = False) -> tuple[list, list]:
    """# Summary

    Pad the shorter list by extending it with its last element to match the longer list's length.

    ## Args:
        list1: First list
        list2: Second list
        value: Value to repeat
        repeat_last: When set to true value is disregarded and the last element is extended

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
        if repeat_last:
            padded_list1 = list1 + list(itertools.repeat(list1[-1], len2 - len1))
        else:
            padded_list1 = list1 + [value] * (len2 - len1)
        return padded_list1, list2
    else:
        # Pad list2 to match list1's length
        if repeat_last:
            padded_list2 = list2 + list(itertools.repeat(list2[-1], len1 - len2))
        else:
            padded_list2 = list2 + [value] * (len1 - len2)
        return list1, padded_list2


def reverse_bits(n: np.uint) -> int:
    result = 0
    for _ in range(n.bit_length()):
        result <<= 1
        result |= n & 1
        n >>= 1
    return result


def tri_sign_2d(a: tuple, b: tuple, c: tuple) -> float:
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])
