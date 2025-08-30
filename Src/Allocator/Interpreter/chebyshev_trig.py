"""
------------------------------------------------------------------------
Filename: 	chebyshev_trig.py

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


def chebyshev_sin(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    return np.astype(np.polynomial.chebyshev.chebinterpolate(np.sin, deg=deg), dtype)


def chebyshev_cos(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev cosine function is not implemented yet.')


def chebyshev_tan(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev tangent function is not implemented yet.')


def chebyshev_arcsin(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arcsine function is not implemented yet.')


def chebyshev_arccos(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arccosine function is not implemented yet.')


def chebyshev_arctan(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arctangent function is not implemented yet.')
