"""Allocator.Core package

Python-facing wrappers for the native c implementation of various core algorithms.
"""

from Allocator.Core.libs.poly.polywrap import (
    poly_sin_deg7,
    poly_sin_deg9,
    poly_sqrtx1_deg3,
    poly_cos_deg6,
    poly_cos_deg12,
)

__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
    'poly_cos_deg12',
]
