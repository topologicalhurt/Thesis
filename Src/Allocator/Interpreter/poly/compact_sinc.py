"""
------------------------------------------------------------------------
Filename: 	compact_sinc.py

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


def compact_sinc(x: np.ndarray, dtype: np.dtype) -> np.ndarray[np.floating]:
    x = np.asarray(x, dtype=dtype)
    result = np.zeros_like(x)
    x_nz = x[x != 0]
    if x_nz.size > 0:
        abs_x_nz = np.abs(x_nz)
        lobe_number = np.floor(abs_x_nz)
        lobe_index = abs_x_nz - lobe_number
        envelope = 1.0 / (np.pi * np.abs(x_nz))
        sign = (-1) ** lobe_number
        canonical_values = _canonical_sinc_lobe_lookup(lobe_index)
        result[x != 0] = sign * envelope * canonical_values
    result[x == 0] = 1.0
    return result


def _canonical_sinc_lobe_lookup(lobe_index: np.ndarray) -> np.ndarray[np.floating]:
    """# Summary

    Vectorized canonical lobe lookup function.

    Args:
        lobe_index: numpy array of values in [0, 2) representing position within canonical lobe

    Returns:
        numpy array of canonical lobe values
    """
    # Convert lobe_index from [0, 2) to [0, \u03c0) for sinc calculation
    t = lobe_index * np.pi
    result = np.where(t == 0, 1.0, np.sin(t))
    return result
