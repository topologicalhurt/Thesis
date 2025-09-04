"""ctypes binding for libpoly.

This module loads the sibling shared library 'libpoly.so' built from poly.c
and exposes simple Python-callable functions.
"""
from __future__ import annotations

from ctypes import c_float, c_double

from Allocator.Core.loadlib import load_libs


_libs = load_libs(['libpoly.so'])
_lib = _libs[0]

# Define signatures
_FUNC_NAMES = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_cos_deg12',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
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


__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
    'poly_cos_deg12',
]
