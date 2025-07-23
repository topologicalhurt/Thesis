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

import numpy as np

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from Allocator.Interpreter.extendedenum import ExtendedEnum
from Allocator.Interpreter.helpers import sort_relative_to, underline_matches, underline_first_non_captured_group


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
        return [getattr(cls.get_member_via_name(name).value, generation.name) for name in group_names]

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
