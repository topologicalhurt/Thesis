"""Allocator.Core package

Python-facing wrappers for the native polynomial evaluators live in polywrap.
Import functions directly from this package for convenience.
"""

from .polywrap import (
    poly_sin_deg7,
    poly_sin_deg9,
    poly_sqrtx1_deg3,
    poly_cos_deg6,
)

__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
]
