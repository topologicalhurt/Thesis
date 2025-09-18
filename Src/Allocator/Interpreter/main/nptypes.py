"""
------------------------------------------------------------------------
Filename: 	nptypes.py

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

import numpy as np

from typing import override
from enum import Enum

from Allocator.Interpreter.main.extendedenum import ExtendedEnum
from Allocator.Interpreter.math.math_utils import largest_dtype_of_kind, machine_has_extended_float_support, machine_has_quad_float_support


class STANDARD_NP_DTYPES(ExtendedEnum):
    """# Summary

    An enum map that stores system specific aliases as known types
    E.G. LARGEST_UINT is the largest available unsigned integer on the system
    """
    LARGEST_UINT = largest_dtype_of_kind(np.uint)
    LARGEST_INT = largest_dtype_of_kind(np.integer)
    LARGEST_FLOAT = largest_dtype_of_kind(np.floating)
    LARGEST_DOUBLE = largest_dtype_of_kind(np.double)
    LARGEST_INT32_VALUE = np.iinfo(np.int32).max
    LARGEST_INT64_VALUE = np.iinfo(np.int64).max


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
    INT32 = 32, np.int32
    INT64 = 64, np.int64
    UINT8 = 8, np.uint8
    UINT16 = 16, np.uint16
    UINT32 = 32, np.uint32
    UINT64 = 64, np.uint64

    @override
    @classmethod
    def get_member_via_name(cls, name: str) -> Enum:
        """Alias default types to types with explicit bit width"""
        if not name[-1].isdigit():
            name += '32'
        return super().get_member_via_name(name)
