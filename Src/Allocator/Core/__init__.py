"""
------------------------------------------------------------------------
Filename: 	__init__.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Allocator.Core package

Python-facing wrappers for the native c implementation of various core algorithms.

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

from Allocator.Core.bindings.py.polywrap import (
    poly_sin_deg7,
    poly_sin_deg9,
    poly_sqrtx1_deg3,
    poly_cos_deg6,
    poly_cos_deg12,
    poly_dyadic_cos_deg12,
)

__all__ = [
    'poly_sin_deg7',
    'poly_sin_deg9',
    'poly_sqrtx1_deg3',
    'poly_cos_deg6',
    'poly_cos_deg12',
    'poly_dyadic_cos_deg12',
]
