#!/usr/bin/env python3
"""
------------------------------------------------------------------------
Filename: 	polynomial_cse_iccad_demo.py

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

from Allocator.Interpreter.poly.polynomial_cse_iccad import optimize_polynomial_iccad
from Allocator.Core import (
    poly_sin_deg7,
    poly_sin_deg9,
    poly_sqrtx1_deg3,
    poly_cos_deg6,
    poly_cos_deg12,
    poly_dyadic_cos_deg12,
)


if __name__ == '__main__':
    from math import factorial

    # # Example 1: -x^7/7! + x^5/5! - x^3/3! + x. I.e. sin taylor series degree 7
    # p_sin_d7 = np.poly1d([
    #     -1.0/factorial(7), 0.0,
    #      1.0/factorial(5), 0.0,
    #     -1.0/factorial(3), 0.0,
    #      1.0, 0.0
    # ])
    # code, stats = optimize_polynomial_iccad(p_sin_d7)
    # print(code)
    # print(stats)

    # # Example 2: sin taylor series degree 9
    # p_sin_d9 = np.poly1d([
    #     1.0/factorial(9), 0.0,
    #     -1.0/factorial(7), 0.0,
    #      1.0/factorial(5), 0.0,
    #     -1.0/factorial(3), 0.0,
    #      1.0, 0.0
    # ])
    # code2, stats2 = optimize_polynomial_iccad(p_sin_d9)
    # print(code2)
    # print(stats2)

    # # Example 3: sqrt(x + 1) taylor series degree 3
    # p_sqrt_d3 = np.poly1d([
    #     1/16, -1/8, 1/2, 1
    # ])
    # code3, stats3 = optimize_polynomial_iccad(p_sqrt_d3)
    # print(code3)
    # print(stats3)

    # # Example 4: cos(x) taylor series degree 6
    # p_cos_d6 = np.poly1d([
    #     -1.0/factorial(6), 0.0,
    #     1.0/factorial(4), 0.0,
    #      -1.0/2, 0.0,
    #      1.0
    # ])
    # code4, stats4 = optimize_polynomial_iccad(p_cos_d6)
    # print(code4)
    # print(stats4)

    # # Example 5: sqrt(x + 1) taylor series degree 5
    # p_sqrt_d5 = np.poly1d([
    #     7/256, -5/128, 1/16, -1/8, 1/2, 1
    # ])
    # code5, stats5 = optimize_polynomial_iccad(p_sqrt_d5)
    # print(code5)
    # print(stats5)

    # # Example 6: cos(x) taylor series degree 12
    # p_cos_d12 = np.poly1d([
    #     1.0/factorial(12), 0.0,
    #     -1.0/factorial(10), 0.0,
    #      1.0/factorial(8), 0.0,
    #     -1.0/factorial(6), 0.0,
    #      1.0/factorial(4), 0.0,
    #      -1.0/2, 0.0,
    #      1.0
    # ])
    # code6, stats6 = optimize_polynomial_iccad(p_cos_d12)
    # print(code6)
    # print(stats6)

    # # Example 7: cos(x) power series degree 12, using dyadic rationals
    # p_dyadic_cos_d12 = [16777214,0,-8388611,0,699046,0,-23309,0,401,0,-22,0,-345].astype(np.float64)
    # p_dyadic_cos_d12 /= 2**24
    # p_dyadic_cos_d12 = np.poly1d(p_dyadic_cos_d12[::-1])
    # code7, stats7 = optimize_polynomial_iccad(p_dyadic_cos_d12)
    # print(code7, stats7)

    # Verify against ctypes bindings
    print('\n[*] Printing results... [*]')
    print(f'sin_deg7: {poly_sin_deg7(np.pi / 4)}')
    print(f'sin_deg9: {poly_sin_deg9(np.pi / 4)}')
    print(f'sqrtx1_deg3: {poly_sqrtx1_deg3(-0.5)}')
    print(f'cos_deg6: {poly_cos_deg6(np.pi / 4)}')
    print(f'cos_deg12: {poly_cos_deg12(np.pi / 4)}')
    print(f'dyadic_poly_deg12: {poly_dyadic_cos_deg12(np.pi / 4)}')
