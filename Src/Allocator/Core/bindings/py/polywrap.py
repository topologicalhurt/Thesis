"""
------------------------------------------------------------------------
Filename: 	polywrap.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	ctypes binding for libpoly.

This module loads the sibling shared library 'libpoly.so' built from poly.c
and exposes simple Python-callable functions.

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
from __future__ import annotations

from ctypes import c_float, c_double

from Allocator.Core.libs.loadlib import load_libs


_libs = load_libs(['libpoly.so'])
_lib = _libs[0]

# Define signatures
_FUNC_NAMES = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_cos_deg12',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
    'dyadic_poly_cos_deg12',
]
for _name in _FUNC_NAMES:
    _fn = getattr(_lib, _name)
    _fn.argtypes = [c_float]
    _fn.restype = c_double


def poly_sin_deg7(x: float) -> float:
    return float(_lib.poly_sin_deg7(c_float(x)))


def poly_sin_deg9(x: float) -> float:
    return float(_lib.poly_sin_deg9(c_float(x)))


def poly_sqrtx1_deg3(x: float) -> float:
    return float(_lib.poly_sqrtx1_deg3(c_float(x)))


def poly_cos_deg6(x: float) -> float:
    return float(_lib.poly_cos_deg6(c_float(x)))


def poly_cos_deg12(x: float) -> float:
    return float(_lib.poly_cos_deg12(c_float(x)))


def poly_dyadic_cos_deg12(x: float) -> float:
    return float(_lib.dyadic_poly_cos_deg12(c_float(x)))


__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
    'poly_cos_deg12',
]
