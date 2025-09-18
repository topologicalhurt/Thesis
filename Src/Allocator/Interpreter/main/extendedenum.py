"""
------------------------------------------------------------------------
Filename: 	extendedenum.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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

import re
import numpy as np

from enum import Enum, EnumMeta
from collections.abc import Sequence, Iterable
from typing import Any, Mapping

from Allocator.Interpreter.main.common_utils import join_regex, underline_matches, combined_fast_stable_hash, fast_stable_hash


class _ExtendedEnumMeta(EnumMeta):
    """Meta class for ExtendedEnum"""
    def __contains__(self, other: Any) -> bool:
        """ # Summary

        Enables support for open-ended type comparisons in derivative classes
        """
        if isinstance(other, str):
            return other.upper() in self.fields()
        elif isinstance(other, int):
            return other in self.values()
        elif issubclass(other.__class__, self):
            return self(other)
        return False

    def __str__(self):
        return str(list(self))

    def _get_subclasses(self):
        """Returns the subclasses of the current class."""
        return [subclass for subclass in self.__subclasses__() if issubclass(subclass, self)]


class ExtendedEnum(Enum, metaclass=_ExtendedEnumMeta):
    """# Summary

    Base class providing extended (common utility functions) feature set to Enum
    """

    def _as_int(self, val: Any | None = None) -> int | tuple[int]:
        if val is None:
            val = self.value

        if isinstance(val, Enum):
            val = val.value

        # Search in raw (nested) values
        vals_to_search = [member.value for member in self.__class__.__members__.values()]
        if val not in vals_to_search:
            raise AttributeError(f'No value {val} found in {self.__class__.__name__}.{self.name}')

        if isinstance(val, (int, np.integer)):
            return int(val)

        if isinstance(val, (list, tuple)):
            if not all(isinstance(item, (int, np.integer)) for item in val):
                non_digits = join_regex(*[str(item) for item in val if not isinstance(item, (int, np.integer))])
                raise TypeError(f'{self.__class__.__name__}.{self.name} has non-integer value {val!r}; cannot compare to int.'
                                f'\n{underline_matches(str(val), non_digits, match_all=True, literal=False)}')
            return tuple(map(int, val))

        raise TypeError(f'{self.__class__.__name__}.{self.name} has non-integer value {val!r}; cannot compare to int')

    def __hash__(self):
        val = self.value
        if isinstance(val, (int, np.integer)):
            val_int = self._as_int(val)
            val_digestable = val.to_bytes(val_int.bit_length() // 8 + 1, 'big', signed=False)
            return fast_stable_hash(val_digestable)

        if isinstance(val, (Enum , tuple, list)):
            val_tuple_int = self._as_int(val)
            val_tuple_int = (val.to_bytes(val.bit_length() // 8 + 1, 'big', signed=False)
                             for val in val_tuple_int)
            return combined_fast_stable_hash(val_tuple_int)

        raise TypeError(f'{self.__class__.__name__}.{self.name} has non-hashable value {self.value!r}; cannot hash')

    def __int__(self) -> int:
        return self._as_int()

    def __index__(self) -> int:
        return self._as_int()

    def _other_as_int(self, other: Any):
        if isinstance(other, (int, np.integer)):
            return int(other)
        if isinstance(other, Enum):
            ov = other.value
            if isinstance(ov, (int, np.integer)):
                return int(ov)
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        ov = self._other_as_int(other)
        if ov is NotImplemented:
            if isinstance(other, Enum):
                return self.value == other.value
            return False
        return int(self) == ov

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        ov = self._other_as_int(other)
        if ov is NotImplemented:
            return NotImplemented
        return int(self) < ov

    def __le__(self, other: Any) -> bool:
        ov = self._other_as_int(other)
        if ov is NotImplemented:
            return NotImplemented
        return int(self) <= ov

    def __gt__(self, other: Any) -> bool:
        ov = self._other_as_int(other)
        if ov is NotImplemented:
            return NotImplemented
        return int(self) > ov

    def __ge__(self, other: Any) -> bool:
        ov = self._other_as_int(other)
        if ov is NotImplemented:
            return NotImplemented
        return self._as_int() >= ov

    @staticmethod
    def unpack(value: Any) -> Sequence:
        """# Summary

        Recursively flattens nested lists or tuples, treating strings as atomic.
        """
        if isinstance(value, (list, tuple)):
            return [item for sublist in value for item in ExtendedEnum.unpack(sublist)]
        return [value]

    @staticmethod
    def unpack_nth(value: Any, idx: int) -> Sequence:
        """# Summary

        Unpacks the value @ the 'nth' position / index from the tuple, returning the unpacked
        tuple if the index exceeds the number of elements in the tuple
        """
        if isinstance(value, (list, tuple)):
            return [item[idx] if isinstance(item, (list, tuple)) and len(item) > idx else item
                    for item in value]
        return [value]

    @classmethod
    def fields(cls) -> Iterable:
        """# Summary

        Return field values via iterator
        """
        return [c.name.upper() for c in cls if not c.name.startswith('_')]

    @classmethod
    def values(cls) -> Sequence:
        """# Summary

        Returns the flattened values of all enum members.
        """
        return [item for member in cls if not member.name.startswith('_')
                 for item in cls.unpack(member.value)]

    @classmethod
    def values_from_indx(cls, idx: int) -> Sequence:
        """# Summary

        Returns the 'nth / idx-th column' of the enum
        """
        return [item for member in cls if not member.name.startswith('_')
                 for item in cls.unpack_nth(member.value, idx)]

    @classmethod
    def members_from_indx(cls, idx: int) -> Mapping[Enum, Any]:
        """# Summary

        Unpacks and returns the idxth element of every tuple, in a dictionary with the
        member as key. I.e.:

        FIELD1 = (1, 'foo')
        FIELD2 = (2, 'bar') ...

        => {FIELD1: 'foo', FIELD2: 'bar' ...}
        """
        return {member: cls.unpack_nth(member.value, idx)[idx] for member in cls.get_members()
                  if isinstance(member.value, (tuple, list))}

    @classmethod
    def get_members(cls) -> Iterable:
        """# Summary

        Returns the enum member fields via iterator
        """
        return [v for k, v in cls.__members__.items() if k in cls]

    @classmethod
    def get_members_from_pattern(cls, pattern: str | re.Pattern[str]) -> list[tuple] | dict:
        """# Summary

        Returns the members matching a regex pattern.

        Args:
            pattern: The regex pattern to match against enum member names.

        Returns:
            A list of tuples or a dictionary with the first group from each match.
        """
        matches = [match.group(0) for field in cls.fields() if (match := re.match(pattern, field)) is not None]
        if not all([hasattr(cls, match) for match in matches]):
            raise AttributeError(f'Unexpected: one or more of the matches didn\'t exist as an attribute for {cls}')
        return [cls.get_member_via_name(match) for match in matches]

    @classmethod
    def get_members_from_mask(cls, mask: Iterable | None) -> Iterable:
        if mask is not None:
            return [cls.get_member_via_name(v) for v in mask if v in cls]
        return cls.get_members()

    @classmethod
    def get_member_via_value(cls, value: int) -> Enum:
        """ # Summary
        Finds the name of an enum member from its value
        (reverse of get_value_from_name)

       ## Args:
            value: The integer value to look up

       ## Returns:
            The field corresponding to the matching enum member
        """
        for m, v in zip(cls.get_members(), cls.values()):
            if v == value:
                return m
        raise ValueError(f'"{value}" is not a valid value in {cls.__name__}')

    @classmethod
    def get_member_via_name(cls, name: str) -> Enum:
        """ # Summary
        Finds the value of an enum member from its field name
        (reverse of get_name_from_value)

       ## Args:
            value: The string name to look up

       ## Returns:
            The integer value of the matching enum member
        """
        for m, n in zip(cls.get_members(), cls.fields()):
            if n.upper() == name.upper():
                return m
        raise ValueError(f'"{name}" is not a valid field name in {cls.__name__}')

    @classmethod
    def get_subclass_from_name(cls, name: str):
        """Returns the subclass corresponding to the given name."""
        subclasses = [subclass for subclass in cls._get_subclasses() if name in subclass]
        if not subclasses:
            return None

        if len(subclasses) > 1:
            to_match = join_regex(subclasses, non_capture=False)
            raise ValueError(f'Ambiguous {cls.__name__} subclass name: {name}.'
                             f' Ensure that the following have unique (non-conflicting) values:'
                             f'\n{underline_matches(str(subclasses), to_match, match_all=True, literal=False)}')
