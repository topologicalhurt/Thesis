"""
------------------------------------------------------------------------
Filename: 	dataclass.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Contains all common dataclasses, enums & schemas

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


from __future__ import absolute_import

import importlib
import itertools
import numpy as np

from dataclasses import dataclass
from enum import Enum, EnumMeta
from collections.abc import Callable, Iterable, Mapping, Sequence, Set
from typing import Any


class _ExtendedEnumMeta(EnumMeta):
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


class ExtendedEnum(Enum, metaclass=_ExtendedEnumMeta):
    """# Summary

    Base class providing extended (common utility functions) feature set to Enum
    """

    @classmethod
    def fields(cls) -> Iterable:
        """# Summary

        Return field values via iterator
        """
        return [c.name.upper() for c in cls if not c.name.startswith('_')]

    @classmethod
    def values(cls) -> Iterable:
        """# Summary

        Returns the values via iterator
        """
        vals = [c.value for c in cls]
        nested_vals = [v for v in vals if isinstance(v, Sequence)]
        unnested_vals = [v for v in vals if not isinstance(v, Sequence)]
        flat_vals = itertools.chain.from_iterable(nested_vals) # Values may be tuples, return reduced list
        unnested_vals.extend(list(flat_vals))
        return unnested_vals

    @classmethod
    def get_members(cls) -> Iterable:
        """# Summary

        Returns the enum member fields via iterator
        """
        fields = cls.fields()
        members = []
        for k, v in cls.__members__.items(): # safe from mix-in's as intersection applies to cls.fields() (already filtered)
            if k in fields:
                members.append(v)
        return members

    @classmethod
    def get_member_via_name_from_value(cls, value: int) -> Enum:
        """ # Summary
        Finds the name of an enum member from its integer value
        (reverse of get_value_from_name)

       ## Args:
            value: The integer value to look up

       ## Returns:
            The field corresponding to the matching enum member
        """
        for member in cls:
            if isinstance(member.value, Sequence):
                if value in member.value:
                    return member
            else:
                if value == member.value:
                    return member
        raise ValueError(f'"{value}" is not a valid value in {cls.__name__}')

    @classmethod
    def get_member_via_value_from_name(cls, name: str) -> Enum:
        """ # Summary
        Finds the value of an enum member from its string value / field name
        (reverse of get_name_from_value)

       ## Args:
            value: The string name to look up

       ## Returns:
            The integer value of the matching enum member
        """
        for member in cls:
            if member.name.upper() == name.upper():
                return member
        raise ValueError(f'"{name}" is not a valid field name in {cls.__name__}')


helpers = importlib.import_module('.helpers', package='Allocator.Interpreter')
combined_fast_stable_hash = helpers.combined_fast_stable_hash
machine_has_extended_float_support = helpers.machine_has_extended_float_support
machine_has_quad_float_support = helpers.machine_has_quad_float_support


class BYTEORDER(Enum):
    LITTLE=0
    BIG=1
    NATIVE=2


class FILTERTYPE(Enum):
    """# Summary

    Enum storing common filter shapes
    """
    LOWPASS=0x1
    HIGHPASS=0x2
    BANDPASS=0x3
    BANDSTOP=0x4


class _BitFieldEnumMeta(EnumMeta):
    """# Summary

    Metaclass for creating Enum types where member values are generated by
    left-shifting an initial integer value by the member's order index.
    """

    @classmethod
    def _get_allowed_names(mcs, allowed_spec: Iterable) -> Set:
        """ # Summary

        Format the allowed spec into a set

        ## Args:
            mcs: _description_ Aliases __new__
            allowed_spec: _description_ The whitelisted attribute names to format

        ## Returns:
            _Set_: _description_ The set wrapped version of allowed_spec
        """
        if allowed_spec is None:
            return None
        if isinstance(allowed_spec, Mapping):
            return set(allowed_spec.keys())
        if isinstance(allowed_spec, Iterable):
            return set(allowed_spec)

    @classmethod
    def _process_member_defs(mcs, allowed_names, clsdict, in_first_msb = True, **kwargs):
        """# Summary

        Iterate through keyword arguments provided at class definition, preserving their order (Python 3.7+).
        Store the attributes as part of the enums class dictionary.

        ## Args:
            mcs (_type_): _description_ Aliases __new__
            allowed_names (_type_): _description_ The whitelisted attribute names
            clsdict (_type_): _description_ Aliases __new__ (enum's class dict)
            in_first_msb (bool, optional): _description_ determines if the first bit is the MSB. Defaults to True.
        """
        for k in kwargs:
            k = str.upper(k)
            if k not in allowed_names:
                raise NameError(
                    f'Member name "{k}" is not allowed for class "{mcs.__name__}". '
                    f'Permitted members are: {sorted(list(allowed_names))}.'
                )

        kwargs_items = kwargs.items()
        kwargs_len = len(kwargs_items) - 1
        for i, (member_name, initial_value) in enumerate(kwargs_items):
            if not isinstance(initial_value, int):
                raise TypeError(
                    f'Value for enum member "{member_name}" must be an integer '
                    f'for bitwise shift, got {type(initial_value).__name__}.'
                )

            if member_name in clsdict:
                raise NameError(
                    f'Enum member name "{member_name}" from keyword arguments '
                    f'conflicts with an item ("{clsdict[member_name]}") already defined in the class body.'
                )

            if in_first_msb:
                final_value = initial_value << (kwargs_len - i)
            else:
                final_value = initial_value << i

            clsdict[member_name] = final_value

    def __new__(mcs, name, bases, clsdict, **kwargs):
        """ ## Summary

        Overrides __new__ class from the enum metaclass. Allows for an enum
        inheriting from BitFieldEnumMeta to concretize it's attributes in
        the class definition, instead of at instantiation in the constructor
        (ala __call__.)
        """
        if kwargs is None:
            raise TypeError(f'class {mcs.__name__} must provide accepted fields')

        allowed_spec = clsdict.get('ALLOWED', None)
        allowed_names = mcs._get_allowed_names(allowed_spec)
        mcs._process_member_defs(
            allowed_names,
            clsdict,
            **kwargs
        )
        return super().__new__(mcs, name, bases, clsdict, **kwargs)


    def __call__(cls, *args, **kwargs):
        """ # Summary

        Overrides the __call__ method of the Enum parent class. I.e. the metaclasses
        enum factory. Names the returned class based on a hash of the key attributes.

        ## Returns:
            _Enum_: _description_ An enum class instance
        """
        if not args and kwargs:
            dynamic_members = {}
            allowed_spec = getattr(cls, 'ALLOWED', None)
            allowed_names = cls._get_allowed_names(allowed_spec.value)
            cls._process_member_defs(
                allowed_names,
                dynamic_members,
                **kwargs
            )

            # Enum factory based on hash of attributes (kwargs)
            # Should be good enough to not create conflicting alias within namespace
            member_items_for_hash = [key.encode('utf-8') for key in kwargs]
            hsh = hex(combined_fast_stable_hash(member_items_for_hash))
            dynamic_name = f'{cls.__name__}_{hsh}'

            return Enum(dynamic_name, dynamic_members)

        if args and not kwargs:
            return super(_BitFieldEnumMeta, cls).__call__(*args)
        if not args and not kwargs:
            return super(_BitFieldEnumMeta, cls).__call__()

        raise TypeError(
            f'{cls.__name__}() called with mixed positional arguments and keyword arguments. '
                'Use keyword arguments only for dynamic enum creation, or positional arguments '
                'only for member lookup.'
        )


class BITFIELD(Enum, metaclass=_BitFieldEnumMeta):
    """# Summary

    Base class for Enums where members are defined via keyword arguments
    to the class definition. The value of each member is the
    provided integer value, LEFT-shifted by its order (index).

    ## Example:
        class MyFlags(OrderedShiftedEnum, F1=1, F2=1, F3=1):
            pass

        MyFlags.F1.value will be 1 (1 << 0)

        MyFlags.F2.value will be 2 (1 << 1)

        MyFlags.F3.value will be 4 (1 << 2)
    """


class FLOAT_STR_NPMAP(ExtendedEnum):
    """# Summary

    An enum map that relates floats aliased by name / str (E.g. 'FLOAT')
    to their numpy types
    """
    # Half precision
    FLOAT16 = 16, np.float16
    HALF = 16, np.float16

    # Single precision
    FLOAT = 32, np.float32
    FLOAT32 = 32, np.float32
    SINGLE = 32, np.float32

    # Double precision
    DOUBLE = 64, np.float64
    FLOAT64 = 64, np.float64

    # Extended precision (80-bit on x86, platform dependent)
    if machine_has_extended_float_support():
        LONGDOUBLE = np.finfo(np.longdouble).bits, np.longdouble
        EXTENDED = np.finfo(np.longdouble).bits, np.longdouble

    # Quad precision (128-bit, not available on all platforms)
    if machine_has_quad_float_support():
        FLOAT128 = 128, np.float128
        QUAD = 128, np.float128


class INT_STR_NPMAP(ExtendedEnum):
    """# Summary

    An enum map that relates ints aliased by name / str (E.g. 'INT')
    to their numpy types
    """
    INT8 = 8, np.int8
    INT16 = 16, np.int16
    INT = 32, np.int32
    INT32 = 32, np.int32
    INT64 = 64, np.int64
    UINT8 = 8, np.uint8
    UINT16 = 16, np.uint16
    UINT = 32, np.uint32
    UINT32 = 32, np.uint32
    UINT64 = 64, np.uint64


class FREQ(Enum):
    """# Summary

    Enum used for referring to 'frequency' granularities (I.e. Hz, KHz, MHz etc.)
    """
    HZ=1
    KHZ=HZ*1000
    MHZ=KHZ*1000
    GHZ=MHZ*1000


@dataclass(frozen=True)
class LUT_ACC_REPORT:
    """# Summary

    Dataclass used for the generated LUT acc report
    """
    avg_acc: float
    min_acc: float
    max_acc: float
    acc_scores: np.array

    def __str__(self) -> str:
        return (f'\n\tAvg. acc score (lower is better): {self.avg_acc}'
          f'\n\tMin-acc loss: {self.min_acc}'
          f'\n\tMax-acc loss: {self.max_acc}')


@dataclass(frozen=True)
class LUT:
    """# Summary

    Dataclass used for an arbitrary generated LUT
    """
    lut: np.array
    endianness: BYTEORDER
    bit_width: int
    table_sz: int
    lop: ExtendedEnum
    scale_factor: float
    table_mode: ExtendedEnum
    fn: Callable[..., np.float64]
    acc_report: LUT_ACC_REPORT
    cmd: str | None # Command used to create LUT
