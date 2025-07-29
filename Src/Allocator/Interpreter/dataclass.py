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
import functools
import numpy as np
import regex as re

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from fxpmath import Fxp

from Allocator.Interpreter.extendedenum import ExtendedEnum
from Allocator.Interpreter.nptypes import INT_STR_NPMAP


@dataclass(frozen=True)
class ProgramMetaInformation:
    DEBUG: bool


class XILINX_GENERATION(ExtendedEnum):
    GEN7 = 7
    ULTRASCALE = 8


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
    ARTIX_ULTRASCALE = 'AU'
    KINTEX_ULTRASCALE = 'KU'
    VIRTEX_ULTRASCALE = 'VU'
    ZYNQ_ULTRASCALE = 'ZU'

    def get_generation(self) -> XILINX_GENERATION:
        if self.value.endswith('U'):
            return XILINX_GENERATION.ULTRASCALE
        return XILINX_GENERATION.GEN7


class XILINX_SPEED_GRADES(ExtendedEnum):
    SLOW = -1
    MED = -2
    MAX = -3
    LOW_P = '-L2'


class XILINX_APU_RPU_IDENTIFIERS(ExtendedEnum):
    DUAL_APU_RPU = 'C'
    QUAD_APU_RPU = 'E'

    def has_gpu_support(self) -> bool:
        return self.value == 'E'


class XILINX_ENGINE_TYPE(ExtendedEnum):
    GENERAL = 'G'
    VIDEO = 'V'


class XILINX_ULTRASCALE_VALUE_IDENTIFIERS(ExtendedEnum):
    # https://docs.amd.com/v/u/en-US/zynq-ultrascale-plus-product-selection-guide
    ZU_VI1 = 1
    ZU_VI2 = 2
    ZU_VI3 = 3
    ZU_VI3T = '3T'
    ZU_VI4 = 4
    ZU_VI5 = 5
    ZU_VI6 = 6
    ZU_VI7 = 7
    ZU_VI8 = 9
    ZU_VI9 = 11
    ZU_VI10 = 15
    ZU_VI11 = 17
    ZU_VI12 = 19


class XILINX_GEN7_LUT_IDENTIFIERS(ExtendedEnum):
    # https://docs.amd.com/v/u/en-US/7-series-product-selection-guide
    A_LI1 = 12
    A_LI2 = 15
    A_LI3 = 25
    A_LI4 = 35
    A_LI5 = 50
    A_LI6 = 75
    A_LI7 = 100
    A_LI8 = 200

    K_LI1 = 70
    K_LI2 = 160
    K_LI3 = 325
    K_LI4 = 355
    K_LI5 = 410
    K_LI6 = 420
    K_LI7 = 480

    V_LI1 = 330
    V_LI2 = 415
    V_LI3 = 485
    V_LI4 = 550
    V_LI5 = 585
    V_LI6 = 690
    V_LI7 = 980
    V_LI8 = 1140
    V_LI9 = 2000


class XILINX_BRAM_SIZES(Enum):
    GEN7_STANDARD = 36
    GEN7_DUALPORT = 18


class XILINX_SUPPORTED_FAMILIES(Enum):
    GEN7 = XILINX_FAMILY_CLASSES.get_members_from_mask(['ARTIX', 'KINTEX', 'VIRTEX', 'ZYNQ'])
    ULTRASCALE = XILINX_FAMILY_CLASSES.get_members_from_mask(['ZYNQ_ULTRASCALE', 'VIRTEX_ULTRASCALE'])


class XILINX_SUPPORTED_PACKAGES(Enum):
    GEN7 = XILINX_PACKAGE_CLASSES.get_members_from_mask(['QUALITY', 'COMMERCIAL'])
    ULTRASCALE = XILINX_PACKAGE_CLASSES.get_members_from_mask(['COMMERCIAL'])


class XILINX_SUPPORTED_SPEED_GRADES(Enum):
    GEN7 = XILINX_SPEED_GRADES.get_members_from_mask(['MED', 'MAX'])
    ULTRASCALE = XILINX_SPEED_GRADES.get_members_from_mask(['SLOW', 'MED', 'MAX'])


class XILINX_SUPPORTED_APU_RPU(Enum):
    ULTRASCALE = XILINX_APU_RPU_IDENTIFIERS.get_members()


class XILINX_SUPPORTED_ENGINE(Enum):
    ULTRASCALE = XILINX_ENGINE_TYPE.get_members_from_mask(['GENERAL'])


class XILINX_SUPPORTED_LUT_SIZES(Enum):
    GEN7 = 100
    ULTRASCALE = 100

    def is_supported(self, value: int) -> bool:
        return value < self.value


@dataclass(frozen=True)
class XILINX_NAME_SCHEME_STRUCTURE:
    """# Summary

    Dataclass used for for the xilinx name scheme structure
    I.e. https://www.vemeko.com/blog/67169.html
    """
    product_package_class: XILINX_PACKAGE_CLASSES
    product_family_class: XILINX_FAMILY_CLASSES
    product_speed_grade: XILINX_SPEED_GRADES | None
    product_lut_count: XILINX_SUPPORTED_LUT_SIZES | None
    product_apu_rpu_type: XILINX_APU_RPU_IDENTIFIERS | None
    product_engine_type: XILINX_ENGINE_TYPE | None
    product_generation: XILINX_GENERATION

    def _build_valid_regex_for_supported_generation(self, enum_field: str, generation: XILINX_GENERATION, idx: int | None = None) -> str:
        if not hasattr(self, enum_field):
            raise AttributeError(f'The target enum {enum_field} could not be found')

        target_enum = getattr(self, enum_field)
        if not hasattr(target_enum, generation.name):
            raise AttributeError(f'The target enum {target_enum} has no generation field corresponding to {generation.name}')

        target_support = getattr(target_enum, generation.name).value

        values = [member.value for member in target_support]
        if idx:
            values = ExtendedEnum.unpack_nth(values, idx)
        else:
            values = ExtendedEnum.unpack(values)

        # Put single characters in regex character sets I.e. [...] and strings should be joined I.e. separated with '|'
        single_values = [str_v for v in values if (len(str_v := str(v))) == 1]
        multi_values =  [str_v for v in values if (len(str_v := str(v))) > 1]
        return f'[{''.join(single_values)}]' if single_values else '|'.join(multi_values)

    def _build_regex_for_gen7(self) -> str:
            package_regex = self._build_valid_regex_for_supported_generation('product_package_class', XILINX_GENERATION.GEN7, idx=1)
            family_regex = self._build_valid_regex_for_supported_generation('product_family_class', XILINX_GENERATION.GEN7)
            speed_grade_regex = self._build_valid_regex_for_supported_generation('product_speed_grade', XILINX_GENERATION.GEN7)
            return (rf'({package_regex})({XILINX_GENERATION.GEN7.value})({family_regex})'
                    rf'(\d+)({speed_grade_regex})?')

    def _build_regex_for_ultrascale(self) -> str:
            package_regex = self._build_valid_regex_for_supported_generation('product_package_class', XILINX_GENERATION.ULTRASCALE, idx=1)
            family_regex = self._build_valid_regex_for_supported_generation('product_family_class', XILINX_GENERATION.ULTRASCALE)
            apu_rpu_regex = self._build_valid_regex_for_supported_generation('product_apu_rpu_type', XILINX_GENERATION.ULTRASCALE)
            engine_regex = self._build_valid_regex_for_supported_generation('product_engine_type', XILINX_GENERATION.ULTRASCALE)
            return (rf'({package_regex})?({family_regex})(\d+)({apu_rpu_regex})({engine_regex})')

    def get_regex_for_generation(self, generation: XILINX_GENERATION) -> str:
        if generation == XILINX_GENERATION.GEN7:
            return self._build_regex_for_gen7()
        elif generation == XILINX_GENERATION.ULTRASCALE:
            return self._build_regex_for_ultrascale()
        raise NotImplementedError(f'There is no support for the generation {generation.value} line of devices')


consts = importlib.import_module('.consts', package='Allocator.Interpreter')
META_INFO = consts.META_INFO


class BYTEORDER(Enum):
    LITTLE=0
    BIG=1
    NATIVE=2


class FILTERTYPE(Enum):
    """# Summary

    Enum storing common filter shapes
    """
    LOWPASS=1
    HIGHPASS=2
    BANDPASS=3
    BANDSTOP=4


class FREQ(Enum):
    """# Summary

    Enum used for referring to 'frequency' granularities (I.e. Hz, KHz, MHz etc.)
    """
    HZ=1
    KHZ=HZ*1000
    MHZ=KHZ*1000
    GHZ=MHZ*1000


@dataclass
class QFormat:
    """# Summary

    Dataclass used to contain a floating number & it's QFormat representation as an unsigned integer
    """
    format: str

    def __post_init__(self):
        self._parse_q_format()

    def __str__(self):
        return self.format

    def _parse_q_format(self) -> None:
        groups = re.findall(r'^([Uu])?Q(\d+)\.(\d+)$', self.format)
        groups = groups if groups is None else groups[0]
        if groups is None or (l_groups := len(groups) < 2) or l_groups > 3:
            raise ValueError(f'Expected <sign?>Q<m>.<n> format but got: {self.format} instead')

        self.signed = l_groups == 2
        _, integer_part, floating_part = groups
        self.integer_part_bw = int(integer_part)
        self.floating_part_bw = int(floating_part)
        self._fxp_parser = functools.partial(Fxp, signed=self.signed, n_word=self.integer_part_bw + self.floating_part_bw,
                                 n_frac=self.floating_part_bw)

    def get_converted(self, val: np.ndarray[np.floating] | np.floating) -> np.uint:
        uint_alias: np.unsignedinteger
        sz = val[0].itemsize * 8 if isinstance(val, np.ndarray) else val.itemsize * 8
        _, uint_alias = INT_STR_NPMAP.get_member_via_name(f'UINT{sz}').value
        return uint_alias(self._fxp_parser(val).val)


@dataclass(frozen=True)
class LUT_ACC_REPORT:
    """# Summary

    Dataclass used for the generated LUT acc report
    """
    avg_acc: np.float32
    min_acc: np.float32
    max_acc: np.float32
    std:     np.float32
    acc_scores: np.ndarray[np.floating]

    def __str__(self) -> str:
        return (f'\n\tAvg. acc score (lower is better): {self.avg_acc:0.5f}'
          f'\n\tMin-acc loss: {self.min_acc:0.5f}'
          f'\n\tMax-acc loss: {self.max_acc:0.5f}'
          f'\n\tStandard deviation: {self.std:0.5f}')


@dataclass(frozen=True)
class LUT:
    """# Summary

    Dataclass used for an arbitrary generated LUT
    """
    table: np.ndarray
    q_format: QFormat
    endianness: BYTEORDER
    bit_width: np.uint
    table_sz: np.uint
    lop: ExtendedEnum
    scale_factor: np.floating
    table_mode: ExtendedEnum
    fn: Callable[..., np.floating]
    acc_report: LUT_ACC_REPORT
    cmd: str | None # Command used to create LUT

    def __str__(self):
        return (f'\n\tFunction: {self.fn.__name__}'
                f'\n\tQ-Format: {self.q_format}'
                f'\n\tEndianness: {self.endianness.name}'
                f'\n\tBit-width: {self.bit_width}'
                f'\n\tTable-size: {self.table_sz}'
                f'\n\tTable mode: {self.table_mode}'
                f'\n\tLevel of precision (LOP): {self.lop}'
                f'\n\tScale factor: {self.scale_factor}'
               )
