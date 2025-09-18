#!/usr/bin/env python3
import numpy as np

from Allocator.Interpreter.poly.dyadic_poly import bmt_truncated_minimax


if __name__ == '__main__':
    # Target: sin(x) on [-pi/2, pi/2], degree 9, dyadic m-bits per coefficient
    a, b = -np.pi/2, np.pi/2
    n = 9
    m_bits = [24] * (n + 1)   # e.g. 24 fractional bits each; customize per-degree if desired

    res = bmt_truncated_minimax(
        f=np.sin,
        degree=n,
        a=a,
        b=b,
        m_bits=m_bits,
        nodes_pow2=8,
        rational_bits=28,
        initial_radius=12,
        max_nodes=100_000,
        remez_iters=10,
        grid_sup=16385,
        refine_binary_search=12,
    )

    print('Best dyadic coefficients (float):', res.dyadic.coeffs_float().tolist())
    print('Numerators z:', res.dyadic.numerators.tolist())
    print('m_bits:', res.dyadic.m_bits.tolist())
    print('Degree:', res.dyadic.degree())
    print('Uniform error K:', res.K)
    print('Candidates scanned:', res.candidates_scanned)
