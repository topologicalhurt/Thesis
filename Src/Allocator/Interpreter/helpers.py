"""
Common helper / utility functions
"""


import regex as re
import xxhash
import importlib

from collections.abc import Iterable, Hashable, Sequence


def combined_fast_stable_hash(data: Iterable[Hashable]) -> int:
    hasher = xxhash.xxh64()
    for val in data:
        hasher.update(val)
    return hasher.intdigest()


dataclasses = importlib.import_module('.dataclasses', package='Allocator.Interpreter')
ExtendedEnum = dataclasses.ExtendedEnum


def fast_stable_hash(data: Hashable) -> int:
    return xxhash.xxh64(data).intdigest()


def pairwise(t: Iterable) -> zip:
    it = iter(t)
    return zip(it,it)


def underline_match(text: str, to_match: str, start_index: int = 0, end_index: int | None = None) -> Sequence[str] | None:
    i = text.find(to_match, start_index, end_index)
    if i == -1:
        return
    if i == start_index:
        start_index = 0

    if end_index is None:
        end_index = i + len(to_match)

    underlined = []
    underlined.append(' ' * (i - start_index))
    underlined.append('^' * (end_index - i))
    return end_index, underlined


def underline_matches(text: str, to_match: Iterable | str, start_index: int = 0, end_index: int | None = None,
                      match_all: bool = False, literal: bool = True,) -> str | None:
    """ # Summary

    Generates a string that underlines a regex match or matches in a given text.

   ## Args:
        text: The original string.
        to_match: The object to be indexed that indicates the part of the string to underline.
        match_all: Determines whether to underline every occurance of match rather than the first found.
        literal: Determines whether to match against to_match as a literal or pattern

   ## Returns:
        A string containing the original text and the underline.
        Returns an error message if the match is None.
    """
    underlined = []
    prev_i = start_index
    if match_all:
        # Either match every pattern in to_match if it is a collection object
        # or, if it is a singular string, match that against the entire text.
        if isinstance(to_match, str):
            to_match = re.escape(to_match) if literal else to_match
        else:
            to_match = '|'.join(re.escape(m) if literal else m for m in to_match)

        for m in re.finditer(to_match, text, pos=start_index, endpos=end_index):
            if m is None:
                return None
            i = m.end(0)
            _, txt = underline_match(text, m.group(0), prev_i)
            prev_i = i
            underlined.extend(txt)

        return f'{text}\n{"".join(underlined)}'

    if not isinstance(to_match, str):
        underlined = []
        for m in to_match:
            i, txt = underline_match(text, m, prev_i)
            underlined.extend(txt)
            prev_i = i
        return f'{text}\n{"".join(underlined)}'

    _, txt = underline_match(text, to_match, start_index, end_index)
    underlined.extend(txt)
    return f'{text}\n{"".join(underlined)}'


def tri_sign_2d(a: tuple, b: tuple, c: tuple) -> float:
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])
