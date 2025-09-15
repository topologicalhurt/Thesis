"""
------------------------------------------------------------------------
Filename: 	signal_reconstructor.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the None module
None
LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

import numpy as np

# from Allocator.Interpreter.helpers import find_nearest
from Allocator.Interpreter.main.dataclass import TABLE_MODE


def reconstruct_sin_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number]:
    half_wave = np.concatenate([qwave, np.flip(qwave)])
    return np.concatenate([half_wave, -half_wave])


def reconstruct_cos_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number]:
        half_wave = np.concatenate([qwave, -np.flip(qwave)])
        return np.concatenate([half_wave, np.flip(half_wave)])


def reconstruct_arcsin_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number] | np.number:
    """
    Reconstruct arcsin(x) over x in [-1, 1] from a quarter-wave LUT f(t)
    storing arcsin(t) for t in [0, 1/√2].

    Identity used (half-angle, mapped to stored domain):
        arcsin(x) = sign(x) * 2 * arcsin( sqrt((1 - sqrt(1 - x^2)) / 2) )
    The inner argument always lies in [0, 1/√2], so only direct LUT access
    is needed (with linear interpolation over the stored domain).
    """
    n_points = qwave.size * 4
    x = np.linspace(-1.0, 1.0, n_points)

    # t(x) = sqrt((1 - sqrt(1 - x^2)) / 2) ∈ [0, 1/sqrt(2)] for all x∈[-1,1]
    one_minus_x2 = 1.0 - np.clip(x * x, 0.0, 1.0)
    inner = np.sqrt(one_minus_x2)
    t = np.sqrt((1.0 - inner) * 0.5)

    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    lut_domain = np.linspace(0.0, inv_sqrt2, qwave.size)
    arcsin_half = np.interp(t, lut_domain, qwave)

    return np.sign(x) * 2.0 * arcsin_half


def reconstruct_arccos_hwave(hwave: np.ndarray[np.number]) -> np.ndarray[np.number] | np.number:
    """Reconstruct arccos(x) for x∈[-1,1] from a *half-wave* LUT.

    Assumptions:
    - ``hwave`` stores either arccos(x) or arccos(x)/2 sampled uniformly for x in [0, 1].
    - Uniform spacing, nearest-neighbor addressing (FPGA-style integer index rounding).
    - No interpolation; quantization error is intentional for distortion analysis.

    Method:
    For x >= 0:  arccos(x)  = LUT(x)
    For x < 0:   arccos(x)  = π - arccos(|x|)
    """
    n = hwave.size
    if n == 0:
        return np.array([], dtype=hwave.dtype)

    n_points = n * 2
    x = np.linspace(-1.0, 1.0, n_points, dtype=hwave.dtype)
    absx = np.abs(x)

    # Nearest-neighbor index mapping into [0,1] domain.
    u = absx * (n - 1)
    idx = np.rint(u).astype(int, copy=False)
    vals = hwave[idx]

    # Reflect for negative x using arccos(-x) = π - arccos(x).
    neg_mask = x < 0
    if np.any(neg_mask):
        vals[neg_mask] = np.pi - vals[neg_mask]

    return vals


def reconstruct_arccos_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number] | np.number:
    """Reconstruct arccos(x) for x∈[-1,1] from a quarter-wave LUT storing
    arccos(t) for t∈[0,1/√2] (uniform). Identity used (mirrors arcsin structure):

        Let a = sqrt((1 + x)/2) ∈ [0,1]. Define b = sqrt((1 - a)/2).
        Then arccos(x) = 2 * arccos(b) with b ∈ [0,1/√2].

    Derivation: set θ = arccos(x). Half-angle gives cos(θ/2)=sqrt((1+x)/2)=a.
    Also cos(θ) = 1 - 2 sin^2(θ/2) => sin(θ/2)=sqrt((1 - cos(θ))/2)=sqrt((1 - x)/2).
    We need expression producing argument constrained to [0,1/√2]; using nested
    half-angle again on cos(θ/2)=a: cos(θ/4)=sqrt((1 + a)/2), sin(θ/4)=sqrt((1 - a)/2).
    Choosing b = sin(θ/4) ensures b ∈ [0, 1/√2] and θ = 4 * arcsin(b) = 2 * (2 * arcsin(b)).
    Since table stores arccos, we use arcsin relation arcsin(b) = π/2 - arccos(b):
        θ = 4*(π/2 - arccos(b)) = 2π - 4*arccos(b).
    For numerical stability and consistency we implement θ = 2π - 4*arccos(b).
    """
    n = qwave.size
    if n == 0:
        return np.array([], dtype=qwave.dtype)

    n_points = n * 4
    x = np.linspace(-1.0, 1.0, n_points, dtype=qwave.dtype)

    a = np.sqrt(np.clip(1.0 + x, 0.0, 2.0) * 0.5)  # in [0,1]
    b = np.sqrt((1.0 - a) * 0.5)  # in [0,1/√2]

    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    lut_domain = np.linspace(0.0, inv_sqrt2, n)

    vals_half = np.interp(b, lut_domain, qwave)

    # θ = 2π - 4 * arccos(b)
    vals = 2.0 * np.pi - 4.0 * vals_half
    return vals


def get_reconstructed_from_lut(table: np.ndarray[np.floating | np.integer],
                               table_mode: TABLE_MODE, signal_name: str) -> np.ndarray[np.floating] | np.float32:
    table_mode = table_mode.value

    if table.size <= 1:
        return np.float32(0)

    if table_mode == 0 or table_mode == 3:
        return table

    if table_mode == 1:
        hwave = table

        if signal_name == 'arccos':
            return reconstruct_arccos_hwave(hwave=hwave)

    elif table_mode == 2:
        qwave = table

        if signal_name == 'sin':
            return reconstruct_sin_qwave(qwave=qwave)

        if signal_name == 'cos':
            return reconstruct_cos_qwave(qwave=qwave)

        if signal_name == 'arcsin':
            return reconstruct_arcsin_qwave(qwave=qwave)

        if signal_name == 'arccos':
            return reconstruct_arccos_qwave(qwave=qwave)

    raise NotImplementedError(f'No reconstruction method exists for {signal_name} yet in table mode {table_mode}')
