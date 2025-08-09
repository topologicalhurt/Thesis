"""
------------------------------------------------------------------------
Filename: 	dataclass.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""


import datetime as dt
import numpy as np

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from Allocator.Interpreter.dataclass import FILTER_TYPE, TABLE_MODE, ExtendedEnum


@dataclass(frozen=True, slots=True)
class PROGRAM_META_INFO:
    """# Summary

    Dataclass storing static meta program information
    (I.e. time of run, git repo root, author credentials etc.)
    """
    DATE_RUN: dt.datetime
    DEBUG: bool
    GIT_ROOT: Path
    AUTHOR_CREDENTIALS: Sequence[str, str]
    EXCLUDED_DIRS: set


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


@dataclass(frozen=True, slots=True)
class TRIG_OPTS:
    lut_select: np.uint          # *Every* single lut that should be generated
    k_mask_bitfield: np.uint     # A mask which determines which luts need to have k also specified
    k_lut_select: np.uint        # Provided luts which *also* need k to be specified
    k_values_select: np.uint     # Provided k values, *only* those corresponding to luts which need k specified

    def __str__(self):
        return (f'\n\t<lut> selection: {bin(self.lut_select)}, {hex(self.lut_select)}'
                f'\n\t<k-lut mask> bitfield: {bin(self.k_mask_bitfield)}, {hex(self.k_mask_bitfield)}'
                f'\n\t<luts requiring k> selection: {bin(self.k_lut_select)}, {hex(self.k_lut_select)}'
                f'\n\t<k values> selection: {bin(self.k_values_select)}, {hex(self.k_values_select)}'
                )


class TRIG_DEFS(ExtendedEnum):
    """# Summary

    Enum storing the supported trig LUTS
    """
    SIN = 0
    COS = 1
    TAN = 2
    ASIN = 3
    ACOS = 4
    ATAN = 5
    SINC = 6
    _SINUSOIDS = (SIN, COS)
    _ARC_SINUSOIDS = (ASIN, ACOS)
    _AUX = (SINC,)


class TRIG_FN_DEFS(ExtendedEnum):
    """# Summary

    Enum storing the trig names & their corresponding functions
    """
    SIN = 0, np.sin
    COS = 1, np.cos
    TAN = 2, np.tan
    ASIN = 3, np.arcsin
    ACOS = 4, np.arccos
    ATAN = 5, np.arctan
    SINC = 6, np.sinc


class TRIG_MUST_HAVE_KSET(ExtendedEnum):
    """# Summary

    Enum storing the trig names for which k must be set
    """
    TAN = 0
    ATAN = 1
    SINC = 2


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


class TRIG_PRECISION(ExtendedEnum):
    """# Summary

    Enum corresponding to how trig LUT is sized

    = 0 (lowest mode - normal precision)

    = 1 (medium mode - double precision)

    = 2 (high mode - full precision)
    """
    LOWP = 0
    MEDP = 1
    HIGHP = 2


class TRIG_TAN_OPTS(ExtendedEnum):
    """# Summary

    Enum that stores any tan options
    """


class TRIG_ATAN_OPTS(ExtendedEnum):
    """# Summary

    Enum that stores any atan options
    """
    SAMPLES_FOR_LOW_MODE = 1000 # Arbitrarily chosen
    ERR_THRESHOLD = 0.1         # I.e. Must be within 10% of the threshold value


class TRIG_SINC_OPTS(ExtendedEnum):
    """# Summary

    Enum that stores any sinc options
    """
    SAMPLES_IN_MAIN_LOBE = 512  # Arbitrarily chosen
