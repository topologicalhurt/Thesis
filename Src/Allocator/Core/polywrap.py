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
_lib.poly_sin_deg7.argtypes = [c_float]
_lib.poly_sin_deg7.restype = c_double

_lib.poly_sin_deg9.argtypes = [c_float]
_lib.poly_sin_deg9.restype = c_double

_lib.poly_sqrtx1_deg3.argtypes = [c_float]
_lib.poly_sqrtx1_deg3.restype = c_double

_lib.poly_cos_deg6.argtypes = [c_float]
_lib.poly_cos_deg6.restype = c_double


def poly_sin_deg7(x: float) -> float:
    return float(_lib.poly_sin_deg7(c_float(x)))


def poly_sin_deg9(x: float) -> float:
    return float(_lib.poly_sin_deg9(c_float(x)))


def poly_sqrtx1_deg3(x: float) -> float:
    return float(_lib.poly_sqrtx1_deg3(c_float(x)))


def poly_cos_deg6(x: float) -> float:
    return float(_lib.poly_cos_deg6(c_float(x)))


__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
]
