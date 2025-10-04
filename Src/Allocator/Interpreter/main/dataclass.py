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

import enum
import functools
import re
import scipy as sp
import numpy as np

from collections.abc import Callable, Sequence
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from enum import Enum
from fxpmath import Fxp

from Allocator.Interpreter.main.extendedenum import ExtendedEnum
from Allocator.Interpreter.main.common_utils import combined_fast_stable_hash, fast_stable_hash
from Allocator.Interpreter.math.nptypes import INT_STR_NPMAP
from Allocator.Interpreter.poly.compact_sinc import compact_sinc
from Allocator.Interpreter.poly.chebyshev_trig import chebyshev_arccos, chebyshev_arcsin, chebyshev_arctan, chebyshev_cos, chebyshev_sin, chebyshev_tan


@dataclass(frozen=True, slots=True)
class PROGRAM_META_INFO:
    DEBUG: bool
    GIT_ROOT: Path


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


class XILINX_BRAM_SIZES(ExtendedEnum):
    GEN7_STANDARD = 1, 36, 36*1000
    GEN7_DUALPORT = 2, 18, 36*1000

    ULTRASCALE_STANDARD = 3, 36, 36*1000
    ULTRASCALE_DUALPORT = 4, 18, 18*1000


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


@dataclass(frozen=True, slots=True)
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


class BYTEORDER(ExtendedEnum):
    LITTLE=0
    BIG=1
    NATIVE=2


class FILTER_TYPE(Enum):
    """# Summary

    Enum storing common filter shapes
    """
    LOWPASS=1
    HIGHPASS=2
    BANDPASS=3
    BANDSTOP=4


class SIG_WINDOW_TYPE(Enum):
    FLATTOP=sp.signal.windows.flattop
    BLACKMANHARRIS=sp.signal.windows.blackmanharris
    KAISER=enum.nonmember(functools.partial(sp.signal.windows.kaiser, beta=8.6))


class FREQ(Enum):
    """# Summary

    Enum used for referring to 'frequency' granularities (I.e. Hz, KHz, MHz etc.)
    """
    HZ=1
    KHZ=HZ*1000
    MHZ=KHZ*1000
    GHZ=MHZ*1000


class LUT_TYPE(Enum):
    TRIG=1
    DSD=2
    OTHER=3


class SIGNAL_TYPE(Enum):
    TRIG=1
    OTHER=2

    @classmethod
    def lut_type_to_signal_type(cls, lut_type: LUT_TYPE) -> Enum:
        return cls._member_map_.get(lut_type.name)


class INTERPOLATION_STRATEGY(Enum):
    """# Summary

    Enum storing the different interpolation strategies
    """
    NEAREST = 0x0
    LINEAR = 0x1
    PARABOLIC = 0x2
    CUBIC = 0x3
    LOCAL_REFINE = 0xf0


@dataclass(frozen=True, slots=True, kw_only=True)
class SIGNAL_METRIC:
    signal: np.ndarray[np.float64 | np.integer]
    signal_type: SIGNAL_TYPE
    signal_name: str | None


class TRIG_DEFS(ExtendedEnum):
    """# Summary

    Enum storing the supported trig LUTS
    """
    SIN = 0x00
    COS = 0x01
    TAN = 0x02
    ASIN = 0x03
    ACOS = 0x04
    ATAN = 0x05
    SINC = 0x06
    CHEBYSHEV_SIN = 0x10
    CHEBYSHEV_COS = 0x11
    CHEBYSHEV_TAN = 0x12
    CHEBYSHEV_ARCSIN = 0x13
    CHEBYSHEV_ARCCOS = 0x14
    CHEBYSHEV_ARCTAN = 0x15
    COMPACT_SINC = 0x16

    _SINUSOIDS = (SIN, COS)
    _ARC_SINUSOIDS = (ASIN, ACOS)
    _AUX = (SINC,)


class LUT_FN_DEFS(ExtendedEnum):
    """# Summary

    Abstract class storing the LUT function definitions
    """


class TRIG_FN_DEFS(LUT_FN_DEFS):
    """# Summary

    Enum storing the trig names & their corresponding functions

    COL1: enum value / key
    COL2: the function to use on LUT
    COL3: the reference function
    """
    SIN = TRIG_DEFS.SIN, np.sin, np.sin
    COS = TRIG_DEFS.COS, np.cos, np.cos
    TAN = TRIG_DEFS.TAN, np.tan, np.tan
    ASIN = TRIG_DEFS.ASIN, np.arcsin, np.arcsin
    ACOS = TRIG_DEFS.ACOS, np.arccos, np.arccos
    ATAN = TRIG_DEFS.ATAN, np.arctan, np.arctan
    SINC = TRIG_DEFS.SINC, np.sinc, np.sinc
    CHEBYSHEV_SIN = TRIG_DEFS.CHEBYSHEV_SIN, chebyshev_sin, np.sin
    CHEBYSHEV_COS = TRIG_DEFS.CHEBYSHEV_COS, chebyshev_cos, np.cos
    CHEBYSHEV_TAN = TRIG_DEFS.CHEBYSHEV_TAN, chebyshev_tan, np.tan
    CHEBYSHEV_ARCSIN = TRIG_DEFS.CHEBYSHEV_ARCSIN, chebyshev_arcsin, np.arcsin
    CHEBYSHEV_ARCCOS = TRIG_DEFS.CHEBYSHEV_ARCCOS, chebyshev_arccos, np.arccos
    CHEBYSHEV_ARCTAN = TRIG_DEFS.CHEBYSHEV_ARCTAN, chebyshev_arctan, np.arctan
    COMPACT_SINC = TRIG_DEFS.COMPACT_SINC, compact_sinc, np.sinc

    @staticmethod
    def format_fn_name_ref(name: str) -> str:
        """Formats name to the reference function in TRIG_DEFS"""
        return name.upper().replace('ARC', 'A').replace('CHEBYSHEV_', '').replace('COMPACT_', '')

    @classmethod
    def get_fn_ref_from_name(cls, name: str) -> TRIG_DEFS:
        """Get the reference function (in TRIG_DEFS) from the given name

        I.e. CHEBYSHEV_SIN -> TRIG_DEFS.SIN
             COMPACT_SINC -> TRIG_DEFS.SINC
             SIN -> TRIG_DEFS.SIN
             SINC -> TRIG_DEFS.SINC
        """
        fn_ref = cls.get_fn_ref(name)
        fn_ref_name = cls.format_fn_name_ref(fn_ref.__name__)
        return TRIG_DEFS.get_member_via_name(fn_ref_name)

    @classmethod
    def get_fn_ref(cls, name: str) -> LUT_FN_DEFS:
        return cls.get_member_via_name(name).value[2]


class TABLE_MODE(ExtendedEnum):
    """# Summary

    Abstract parent of classes defining LUT 'fold' mode
    I.e. a periodic function (E.g. sinusoids)
    OR a function having an entire domain that can be reconstructed from a
    subset of it's domain (E.g. arctan)
    """


class TRIG_OPT_MODE(TABLE_MODE):
    """# Summary

    Enum corresponding to how the trig LUT is 'folded' E.G. refer to the basic sin case
    for an example.
    (Using higher modes will, ostensibly, take more effort to recover the data.)

    Note: there are no real advantages to not using 2 = high mode for
    most functions.

    = 0 (lowest mode - full table / complete period)

    = 1 (medium mode - half table / half period)

    = 2 (high mode - quarter table / quarter period)

    = 3 (max mode - polynomial reconstruction if supported)
    """
    LOW = 0
    MED = 1
    HIGH = 2
    MAX = 3


class PREC_MODE(ExtendedEnum):
    """# Summary

    Abstract class defining the precision modes for LUTs
    """


class TRIG_PRECISION(PREC_MODE):
    """# Summary

    Enum corresponding to how trig LUT is sized

    = 0 (lowest mode - normal precision)

    = 1 (medium mode - double precision)

    = 2 (high mode - full precision)
    """
    LOWP = 0
    MEDP = 1
    HIGHP = 2


@dataclass(slots=True)
class QFormat:
    """# Summary

    Dataclass used to contain a floating number & it's QFormat representation as an unsigned integer
    """
    format: str
    integer_part_bw: int = field(init=False)
    floating_part_bw: int = field(init=False)
    signed: bool = field(init=False)
    _fxp_parser: Callable[[np.ndarray[np.float64]], Fxp] = field(init=False, repr=False)

    def __post_init__(self):
        self._parse_q_format()

    def __hash__(self):
        return fast_stable_hash(self.format)

    def __str__(self):
        return self.format

    def _parse_q_format(self) -> None:
        groups = re.findall(r'^([Uu])?Q(\d+)\.(\d+)$', self.format)
        groups = groups[0] if groups is not None else None
        if groups is None or (l_groups := len(groups) < 2) or l_groups > 3:
            raise ValueError(f'Expected <sign?>Q<m>.<n> format but got: {self.format} instead')

        self.signed = l_groups == 2
        _, integer_part, floating_part = groups
        self.integer_part_bw = int(integer_part)
        self.floating_part_bw = int(floating_part)
        self._fxp_parser = functools.partial(Fxp, signed=self.signed, n_word=self.integer_part_bw + self.floating_part_bw,
                                 n_frac=self.floating_part_bw)

    def get_converted(self, val: np.ndarray[np.float64] | np.float64) -> np.uint:
        val = np.asarray(val, dtype=np.float64)
        if val.size == 0:
            raise ValueError('Cannot convert empty value to QFormat representation')

        sz = val.itemsize * 8 if not isinstance(val, np.ndarray) else val[0].itemsize * 8
        uint_alias: np.unsignedinteger
        _, uint_alias = INT_STR_NPMAP.get_member_via_name(f'UINT{sz}').value
        return uint_alias(self._fxp_parser(val).val)

    def get_float_representation(self, val: np.ndarray[np.uint] | np.uint) -> np.float64:
        return val / 2 ** self.floating_part_bw


@dataclass(frozen=True, slots=True)
class LUT_QUANT_ACC_REPORT:
    """# Summary

    Dataclass used as part of the LUT acc report. Stores the quantization error per.
    `assess_lut_quantization_error` under `lut_acc_metrics`
    """
    avg_acc: np.float32
    min_acc: np.float32
    max_acc: np.float32
    std:     np.float32
    acc_scores: np.ndarray[np.float64]

    def __str__(self):
        return (f'---LUT QUANTIZATION ERROR ACC REPORT---'
          f'\n\n\tAvg. acc score (lower is better): {self.avg_acc:0.5f}'
          f'\n\tMin-acc loss: {self.min_acc:0.5f}'
          f'\n\tMax-acc loss: {self.max_acc:0.5f}'
          f'\n\tStandard deviation: {self.std:0.5f}')


@dataclass(frozen=True, slots=True)
class LUT_THD_ACC_REPORT:
    """# Summary

    Dataclass used as part of the LUT acc report. Stores the total harmonic distortion (THD) error per.
    `assess_lut_thd` under `lut_acc_metrics`
    """
    thd_dB: np.float32
    thd_scalar: np.float32
    test_type: str = field(default='THD')

    def __str__(self):
        header = f'---LUT {self.test_type} ACC REPORT---'
        if self.test_type == 'THD':
            body = (f'\n\n\tTHD dB: {self.thd_dB:0.5f}'
                    f'\n\tTHD (%) {self.thd_scalar:.2%}'
                    f'\n\tTHD scalar: {self.thd_scalar:0.5f}')
        elif self.test_type == 'K_CUT_DIST':
            body = (f'\n\n\tK-cut distortion dB: {self.thd_dB:0.5f}'
                    f'\n\tK-cut (%): {self.thd_scalar:.2%}'
                    f'\n\tK-cut distortion scalar: {self.thd_scalar:0.5f}')

        elif self.test_type == 'CHEB_MODEL':
            body = (f'\n\n\tChebyshev residual/model dB: {self.thd_dB:0.5f}'
                    f'\n\tChebyshev (%): {self.thd_scalar:.2%}'
                    f'\n\tChebyshev residual/model scalar: {self.thd_scalar:0.5f}')
        elif self.test_type == 'RESIDUAL_RMS':
            body = (f'\n\n\tResidual RMS ratio dB: {self.thd_dB:0.5f}'
                    f'\n\tResidual RMS ratio (%): {self.thd_scalar:.2%}'
                    f'\n\tResidual RMS ratio scalar: {self.thd_scalar:0.5f}')
        else:
            body = (f'\n\n\tMetric dB: {self.thd_dB:0.5f}'
                    f'\n\tMetric (%): {self.thd_scalar:.2%}'
                    f'\n\tMetric scalar: {self.thd_scalar:0.5f}')
        return header + body


@dataclass(slots=True)
class LUT_ACC_REPORT:
    """# Summary

    Dataclass used to store *all* types of lut acc report.
    """
    quant_acc_report: LUT_QUANT_ACC_REPORT
    thd_acc_report: LUT_THD_ACC_REPORT | None
    f_name: InitVar[str]
    _f_name: str = field(init=False, repr=False)

    def __post_init__(self, f_name: str):
        self._f_name = f_name.upper()

    @property
    def f_name(self):
        return self._f_name

    def __str__(self):
        result = [f'[*]---LUT ACC REPORTS FOR {self.f_name}---[*]']
        result.append(str(self.quant_acc_report))

        if self.thd_acc_report is not None:
            result.append(str(self.thd_acc_report))

        return '\t\n'.join(result)


@dataclass(frozen=True, slots=True)
class KaiserParameters:
    """# Summary

    Dataclass storing Kaiser window parameters BEFORE it is designed
    """
    beta: np.float32
    window_length: np.int16
    transition_width_rad: np.float64
    transition_width_norm: np.float64
    transition_width_hz: np.int32 | None
    sample_rate: np.int32
    estimated_attenuation: np.float32


@dataclass(frozen=True, slots=True)
class KaiserSchematic:
    """# Summary

    Dataclass storing the Kaiser window AFTER it is designed
    """
    coeffs: np.ndarray[np.floating]
    cutoff_norm: float | Sequence[np.floating]
    filter_type: FILTER_TYPE
    measured_stopband_attenuation: np.float32
    target_stopband_attenuation: np.float32
    frequency_response: Sequence[np.ndarray[np.floating], np.ndarray[np.floating]]
    parameters: KaiserParameters


@dataclass(slots=True, kw_only=True)
class LUT:
    """# Summary

    Dataclass used for an arbitrary generated LUT
    """
    table: np.ndarray[np.integer | np.floating]
    domain: np.ndarray[np.integer | np.floating]
    domain_fn: Callable[..., np.ndarray[np.integer | np.floating]]
    type: LUT_TYPE
    q_format: QFormat
    endianness: BYTEORDER
    bit_width: np.uint32
    table_sz: np.uint32
    lop: ExtendedEnum
    scale_factor: np.float64
    table_mode: ExtendedEnum
    cmd: str | None                                                                  # Command used to create LUT
    fn: Callable[..., np.floating]                                                   # Nominal function
    fn_ref: Callable[..., np.floating] | None = field(default=None)                  # Reference function
    _acc_report: LUT_ACC_REPORT | None = field(default=None, init=False)

    def __post_init__(self):
        self.fn_ref = self.fn if self.fn_ref is None else self.fn_ref

    def __hash__(self):
        q_hsh = hash(self.q_format)
        q_hsh_digestable: bytes = q_hsh.to_bytes(length=q_hsh.bit_length() // 8 + 1, byteorder='big')
        bit_width_digestable: bytes = self.bit_width.to_bytes(length=self.bit_width.bit_length() // 8 + 1,
                                                              byteorder='big')

        return combined_fast_stable_hash((self.fn.__name__, q_hsh_digestable,
                                          self.endianness.name, bit_width_digestable))

    @property
    def acc_report(self) -> LUT_ACC_REPORT:
        return self._acc_report

    def update_acc_report(self, report: LUT_ACC_REPORT) -> None:
        self._acc_report = report   # Avoid acc_report.setter standard, prefer invocation of method

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
