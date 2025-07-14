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
import numpy as np
import regex as re

from dataclasses import dataclass
from enum import Enum, EnumMeta, _EnumDict
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

    def __str__(self):
        return str(list(self))


class ExtendedEnum(Enum, metaclass=_ExtendedEnumMeta):
    """# Summary

    Base class providing extended (common utility functions) feature set to Enum
    """

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
            return [item[idx] if len(item) > idx else item
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
    def get_members(cls) -> Iterable:
        """# Summary

        Returns the enum member fields via iterator
        """
        return [v for k, v in cls.__members__.items() if k in cls.fields()]

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
        return [cls.get_member_via_value_from_name(match) for match in matches]

    @classmethod
    def get_members_from_mask(cls, mask: Iterable | None) -> Iterable:
        if mask is not None:
            return [cls.get_member_via_value_from_name(v) for v in mask if v in cls]
        return cls.get_members()

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


class _BitFieldEnumMeta(EnumMeta):
    """# Summary

    Metaclass for creating Enum types where member values are generated by
    left-shifting an initial integer value by the member's order index.
    """

    def get_bit_str(self) -> int:
        return sum(list(map(lambda c: c.value, self)))

    @classmethod
    def _get_allowed_names(mcs, allowed_spec: Any | None) -> Set:
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
        if isinstance(allowed_spec, Enum):
            return set(allowed_spec.value)
        if isinstance(allowed_spec, Mapping):
            return set(allowed_spec.keys())
        if isinstance(allowed_spec, Iterable):
            return set(allowed_spec)

    @classmethod
    def _process_member_defs(mcs, allowed_names: Iterable[str] | None, offset: Iterable[int] | int,
                             clsdict: Mapping,
                             count: bool = True,
                             in_first_msb: bool = True,
                             **kwargs: Any) -> None:
        """# Summary

        Iterate through keyword arguments provided at class definition, preserving their order (Python 3.7+).
        Store the attributes as part of the enums class dictionary.

        ## Args:
            mcs (_type_): _description_ Aliases __new__
            allowed_names (_type_): _description_ The whitelisted attribute names. If None then
            offset: The amount to begin left shifting at
            clsdict (_type_): _description_ Aliases __new__ (enum's class dict)
            count: determines whether to index or just use raw offset
            in_first_msb (bool, optional): _description_ determines if the first bit is the MSB. Defaults to True.
        """
        if allowed_names is not None:
            for k in kwargs:
                k = str.upper(k)
                if k not in allowed_names:
                    raise NameError(
                        f'Member name "{k}" is not allowed for class "{mcs.__name__}". '
                        f'Permitted members are: {sorted(list(allowed_names))}.'
                    )

        kwargs_items = kwargs.items()
        offset_is_iterable = isinstance(offset, Iterable)
        args_length = len(kwargs) - 1

        i = 0 # Index counting # of args if count is set
        j = 0 # Index counting into offset if offset is an iterable
        for member_name, initial_value in kwargs_items:
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

            if offset_is_iterable:
                leftshift = find_left_shift_from_iterable_offset(offset, j, i, in_first_msb=in_first_msb)
                j += 1
            else:
                leftshift = find_left_shift_from_integer_offset(offset, args_length, i, in_first_msb=in_first_msb)

            if count:
                i += 1

            final_value = initial_value << leftshift
            clsdict[member_name] = final_value

    def __str__(self):
        return str(list(map(lambda c: c.value, self)))

    def __new__(mcs, name, bases, clsdict, **kwargs):
        """ ## Summary

        Overrides __new__ class from the enum metaclass. Allows for an enum
        inheriting from BitFieldEnumMeta to concretize it's attributes in
        the class definition, instead of at instantiation in the constructor
        (ala __call__.)
        """
        allowed_spec = clsdict.get('ALLOWED', None)
        allowed_names = mcs._get_allowed_names(allowed_spec)
        mcs._process_member_defs(
            allowed_names=allowed_names,
            offset=0,
            clsdict=clsdict,
            count=True,
            **kwargs
        )
        return super().__new__(mcs, name, bases, clsdict, **kwargs)

    def __call__(cls, offset: Iterable[int] | int = 0, count: bool = True, *args, **kwargs):
        """ # Summary

        Overrides the __call__ method of the Enum parent class. I.e. the metaclasses
        enum factory. Names the returned class based on a hash of the key attributes.

        ## Returns:
            _Enum_: _description_ An enum class instance
        """
        if not args and kwargs:
            dynamic_members = _EnumDict()
            allowed_spec = getattr(cls, 'ALLOWED', None)
            allowed_names = cls._get_allowed_names(allowed_spec)
            cls._process_member_defs(
                allowed_names=allowed_names,
                offset=offset,
                clsdict=dynamic_members,
                count=count,
                **kwargs
            )

            # Enum factory based on hash of attributes (kwargs)
            # Should be good enough to not create conflicting alias within namespace
            member_items_for_hash = [key.encode('utf-8') for key in kwargs]
            hsh = hex(combined_fast_stable_hash(member_items_for_hash))
            dynamic_name = f'{cls.__name__}_{hsh}'

            new_enum_class = cls.__class__(dynamic_name, (cls,), dynamic_members)
            return new_enum_class

        raise TypeError(
            f'{cls.__name__}() called without keyword arguments. '
                'Use keyword arguments only for dynamic enum creation.'
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
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


helpers = importlib.import_module('.helpers', package='Allocator.Interpreter')
combined_fast_stable_hash = helpers.combined_fast_stable_hash
machine_has_extended_float_support = helpers.machine_has_extended_float_support
machine_has_quad_float_support = helpers.machine_has_quad_float_support
find_left_shift_from_iterable_offset = helpers.find_left_shift_from_iterable_offset
find_left_shift_from_integer_offset = helpers.find_left_shift_from_integer_offset
pairwise = helpers.pairwise
underline_matches = helpers.underline_matches
sort_relative_to = helpers.sort_relative_to
underline_first_non_captured_group = helpers.underline_first_non_captured_group


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


class XILINX_GENERATION(Enum):
    GEN7 = 7


class XILINX_PACKAGE_CLASSES(ExtendedEnum):
    QUALITY = 'Q', 'XQ'
    AUTOMOTIVE = 'A', 'XA'
    COMMERCIAL = 'C', 'XC'
    AEROSPACE = 'R', 'XQR'


class XILINX_FAMILY_CLASSES(ExtendedEnum):
    SPARTAN = 'S'
    ARTIX = 'A'
    KINTEX = 'K'
    VIRTEX = 'V'
    ZYNQ = 'Z'


class XILINX_SPEED_GRADES(ExtendedEnum):
    SLOW = -1
    MED = -2
    MAX = -3
    LOW_P = '-L2'


class XILINX_SUPPORTED_FAMILIES(Enum):
    GEN7 = XILINX_FAMILY_CLASSES.get_members_from_mask(['ARTIX', 'KINTEX', 'VIRTEX', 'ZYNQ'])   # Support all except spartan


class XILINX_SUPPORTED_PACKAGES(Enum):
    GEN7 = XILINX_PACKAGE_CLASSES.get_members_from_mask(['QUALITY', 'COMMERCIAL'])              # Support QML, Auto, Commercial


class XILINX_SUPPORTED_SPEED_GRADES(Enum):
    GEN7 = XILINX_SPEED_GRADES.get_members_from_mask(['MED', 'MAX'])                            # Support -2, -3 speed grades


class XILINX_SUPPORTED_LUT_SIZES(Enum):
    GEN7 = 50


class XILINX_BRAM_SIZES(Enum):
    GEN7_STANDARD = 36
    GEN7_DUALPORT = 18


@dataclass(frozen=True)
class LUT_ACC_REPORT:
    """# Summary

    Dataclass used for the generated LUT acc report
    """
    avg_acc: float
    min_acc: float
    max_acc: float
    acc_scores: np.ndarray

    def __str__(self) -> str:
        return (f'\n\tAvg. acc score (lower is better): {self.avg_acc}'
          f'\n\tMin-acc loss: {self.min_acc}'
          f'\n\tMax-acc loss: {self.max_acc}')


@dataclass(frozen=True)
class LUT:
    """# Summary

    Dataclass used for an arbitrary generated LUT
    """
    lut: np.ndarray
    endianness: BYTEORDER
    bit_width: int
    table_sz: int
    lop: ExtendedEnum
    scale_factor: float
    table_mode: ExtendedEnum
    fn: Callable[..., np.floating]
    acc_report: LUT_ACC_REPORT
    cmd: str | None # Command used to create LUT


@dataclass(frozen=True)
class XILINX_NAME_SCHEME_STRUCTURE:
    """# Summary

    Dataclass used for for the xilinx name scheme structure
    I.e. https://www.vemeko.com/blog/67169.html
    """
    product_package_class: XILINX_PACKAGE_CLASSES
    product_family_class: XILINX_FAMILY_CLASSES
    product_speed_grade: XILINX_SPEED_GRADES
    product_lut_count: XILINX_SUPPORTED_LUT_SIZES
    product_generation: XILINX_GENERATION

    @staticmethod
    def _build_valid_regex_for_supported_generation(e: Enum, generation: XILINX_GENERATION, idx: int | None = None) -> str:
        # Standard for e, the target Enum, is to have declared a variable with GEN<version> scheme
        # I.e. GEN7. Get that attribute.
        if not hasattr(e, generation.name):
            raise AttributeError(f'The target enum {e} has no generation field corresponding to {generation.name}')
        target_support = getattr(e, generation.name).value

        values = [member.value for member in target_support]
        if idx:
            values = ExtendedEnum.unpack_nth(values, idx)
        else:
            values = ExtendedEnum.unpack(values)

        # Put single characters in regex character sets I.e. [...] and strings should be joined I.e. separated with '|'
        single_values = [str_v for v in values if (len(str_v := str(v))) == 1]
        multi_values =  [str_v for v in values if (len(str_v := str(v))) > 1]
        return (f'[{''.join(single_values)}]' if single_values else '') + '|'.join(multi_values)

    def get_regex_for_generation(self, generation: XILINX_GENERATION) -> str:
        if generation == XILINX_GENERATION.GEN7:
            package_regex = XILINX_NAME_SCHEME_STRUCTURE._build_valid_regex_for_supported_generation(self.product_package_class,
                                                                                                    XILINX_GENERATION.GEN7, idx=1)
            family_regex = XILINX_NAME_SCHEME_STRUCTURE._build_valid_regex_for_supported_generation(self.product_family_class,
                                                                                                    XILINX_GENERATION.GEN7)
            speed_grade_regex = XILINX_NAME_SCHEME_STRUCTURE._build_valid_regex_for_supported_generation(self.product_speed_grade,
                                                                                                    XILINX_GENERATION.GEN7)
            return (rf'({package_regex})({generation.value})({family_regex})'
                    rf'(\d+)({speed_grade_regex})?'
                    )
        raise NotImplementedError(f'There is no support for the generation {generation.value} line of devices')


class _XILINX_NAME_SCHEME_META(ExtendedEnum):
    @classmethod
    def _get_product_meta_for_generation(cls, generation: XILINX_GENERATION) -> Sequence[str]:
        # Get all members with GEN<version> as prefix, ensuring they are sorted relative to ['package', 'family', 'speed_grade']
        groups = cls.get_members_from_pattern(rf'({generation.name})_(\w|\d|_)+')
        group_names = sort_relative_to([group.name for group in groups],
                                   {f'{generation.name}_PACKAGES': 0,
                                    f'{generation.name}_FAMILIES': 1,
                                    f'{generation.name}_SPEED_GRADES': 2,
                                    f'{generation.name}_LUT_COUNT': 3
                                   }
                                 )
        return [getattr(cls.get_member_via_value_from_name(name).value, generation.name) for name in group_names]

    @classmethod
    def get_regex_for_generation(cls, generation: XILINX_GENERATION) -> str:
        # Get the regex representation of the naming scheme based on the generation support
        groups = cls._get_product_meta_for_generation(generation)
        structure = XILINX_NAME_SCHEME_STRUCTURE(*groups, product_generation=generation)
        return structure.get_regex_for_generation(generation)

    @classmethod
    def validate_regex_for_generation(cls, string: str, generation: XILINX_GENERATION) -> Sequence[str]:
        # Build regex string from the gathered groups
        groups_regex = cls.get_regex_for_generation(generation)
        matches = underline_first_non_captured_group(groups_regex, string)
        if isinstance(matches, str):
            raise ValueError('Invalid XILINX product name:'
                             f'\n{matches}'
                             )

        min_lut_sz = getattr(XILINX_SUPPORTED_LUT_SIZES, generation.name)
        if int(matches[3]) < min_lut_sz.value:
            raise ValueError(f'Invalid XILINX product name (must provide a lut size >= {min_lut_sz.value}):'
                             f'\n{underline_matches(string, matches[3])}'
                             )

        return matches


class XILINX_NAME_SCHEME(_XILINX_NAME_SCHEME_META):
    GEN7_PACKAGES = XILINX_SUPPORTED_PACKAGES
    GEN7_FAMILIES = XILINX_SUPPORTED_FAMILIES
    GEN7_SPEED_GRADES = XILINX_SUPPORTED_SPEED_GRADES
    GEN7_LUT_COUNT = XILINX_SUPPORTED_LUT_SIZES
