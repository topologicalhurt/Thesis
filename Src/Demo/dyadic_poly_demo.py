#!/usr/bin/env python3

import numpy as np

from collections.abc import Sequence

from Allocator.Interpreter.main.consts import DYADIC_POLY_PREFIX, LOGGER
from Allocator.Interpreter.poly.dyadic_poly import BMTResult, DyadicPoly, bmt_truncated_minimax
from Allocator.Interpreter.poly.polynomial_cse_iccad import optimize_polynomial_iccad
from Allocator.Interpreter.poly.prim_poly import PrimPolyQ, PrimPolyQ, PrimitiveDyadicPoly


def _quadrant_reduce_to_pm_quarter_pi(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    hpi = np.pi / 2.0
    k = np.rint(x / hpi).astype(int)
    r = x - k * hpi
    return k, r


def _eval_full_cos_from_pair(dy_cos: DyadicPoly, dy_sin: DyadicPoly, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    k, r = _quadrant_reduce_to_pm_quarter_pi(x)
    km = np.mod(k, 4)

    out = np.empty_like(x, dtype=float)
    m0 = (km == 0)
    m1 = (km == 1)
    m2 = (km == 2)
    m3 = (km == 3)

    if np.any(m0): out[m0] = dy_cos.eval(r[m0])
    if np.any(m1): out[m1] = -dy_sin.eval(r[m1])
    if np.any(m2): out[m2] = -dy_cos.eval(r[m2])
    if np.any(m3): out[m3] =  dy_sin.eval(r[m3])
    return out


def build_quadrature(
    degree: int,
    m_bits: Sequence[int],
    base_a: float = -np.pi/4,
    base_b: float =  np.pi/4,
    **kwargs
) -> tuple[BMTResult, BMTResult]:
    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"quadrant pair build: degree={degree}, bits={list(m_bits)}, base=[{base_a},{base_b}]"
    ))

    res_c = bmt_truncated_minimax(
        f=np.cos, degree=degree, a=base_a, b=base_b, m_bits=m_bits, **kwargs
    )
    res_s = bmt_truncated_minimax(
        f=np.sin, degree=degree, a=base_a, b=base_b, m_bits=m_bits, **kwargs
    )

    return res_c, res_s


def _requantize_numerators(dy: DyadicPoly, kind: str) -> np.ndarray:
    """If t-basis suspected, convert to x-basis (not foolproof)"""
    coeff = dy.coeffs_float().astype(float)
    rad = (dy.b - dy.a) / 2.0
    need_scale = False
    if abs(dy.a + dy.b) < 1e-15:
        if kind == 'cos':
            if len(coeff) >= 3:
                a2 = coeff[2]
                if a2 < 0:
                    s = np.sqrt(max(0.0, -2.0 * a2))
                    if rad > 0 and abs(s - rad) / rad < 0.25:
                        need_scale = True
        elif kind == 'sin':
            if len(coeff) >= 2:
                a1 = coeff[1]
                if rad > 0 and abs(a1 - 1.0) > 0.1 and abs(a1 / rad - 1.0) < 0.25:
                    need_scale = True

    if need_scale:
        scale = np.array([rad**j for j in range(len(coeff))], dtype=float)
        coeff = coeff / scale
    z = np.rint(coeff * (2.0 ** dy.m_bits.astype(float))).astype(int)
    return z


def full_cos_demo_relative_error(
    degree: int = 12,
    m_bits_each: int = 24,
    grid_eval: int = 1_000_000,
) -> None:
    m_bits = [m_bits_each] * (degree + 1)
    res_c, res_s = build_quadrature(
        degree=degree, m_bits=m_bits,
    )

    zc_des = _requantize_numerators(res_c.dyadic, 'cos')
    zs_des = _requantize_numerators(res_s.dyadic, 'sin')

    dy_cos_des = DyadicPoly(numerators=zc_des, m_bits=res_c.dyadic.m_bits, a=res_c.dyadic.a, b=res_c.dyadic.b)
    dy_sin_des = DyadicPoly(numerators=zs_des, m_bits=res_s.dyadic.m_bits, a=res_s.dyadic.a, b=res_s.dyadic.b)

    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"base-interval results: cos K_abs={res_c.K}, sin K_abs={res_s.K}, deg={degree}, bits={m_bits_each}"
    ))

    xs = np.linspace(0.0, 2.0 * np.pi, grid_eval, dtype=float)
    true = np.cos(xs)
    approx = _eval_full_cos_from_pair(dy_cos_des, dy_sin_des, xs)

    thr = 1e-15
    mask = np.abs(true) >= thr
    rel = np.empty_like(true)
    rel[mask] = np.abs(approx[mask] - true[mask]) / np.abs(true[mask])
    rel[~mask] = np.nan
    max_rel = np.nanmax(rel)
    rms_rel = np.sqrt(np.nanmean(rel**2))

    max_abs_at_zeros = np.max(np.abs(approx[~mask] - true[~mask])) if np.any(~mask) else 0.0

    print(f"Degree n = {degree}, fractional bits per coeff = {m_bits_each}")
    print(f"Base interval [-π/4, π/4] absolute sup errors: cos K = {res_c.K:.3e}, sin K = {res_s.K:.3e}")
    print(f"[0, 2π] relative error (excluding zeros): max = {max_rel:.3e}, rms = {rms_rel:.3e}")
    print(f"[0, 2π] absolute error at zeros: max_abs = {max_abs_at_zeros:.3e}")
    print('Cos dyadic numerators for Desmos (asc degree):', dy_cos_des.numerators.tolist())
    print('Sin dyadic numerators for Desmos (asc degree):', dy_sin_des.numerators.tolist())

    # Now let's simplify using the polynomial_icaad technique
    cos_coeffs = dy_cos_des.numerators.astype(np.float64)
    cos_coeffs /= 2.0 ** dy_cos_des.m_bits
    cos_coeffs = np.poly1d(cos_coeffs[::-1])
    code, stats = optimize_polynomial_iccad(cos_coeffs)
    print(code, stats)

    # And let's see how the version optimized for logic does
    prim_cos_dyadic_poly = PrimitiveDyadicPoly(dy_cos_des)
    prim_cos_poly_q = PrimPolyQ(prim_cos_dyadic_poly)
    prim_sin_dyadic_poly = PrimitiveDyadicPoly(dy_sin_des)
    prim_sin_poly_q = PrimPolyQ(prim_sin_dyadic_poly)
    print(prim_cos_poly_q.squarer_form())
    print(prim_sin_poly_q.squarer_form())


if __name__ == '__main__':
    full_cos_demo_relative_error()
