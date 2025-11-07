"""
Dyadic Polynomial Approximation via Bounded Minimax Truncation (BMT).

This module implements polynomial approximation with dyadic rational coefficients
(numbers of the form p/2^k where p is an integer and k is a nonnegative integer).
Dyadic rationals have exact binary representation, making them ideal for FPGA
fixed-point arithmetic.

The core algorithm combines:
1. Remez exchange for continuous minimax polynomial seeding
2. Integer polytope formulation of dyadic coefficient constraints
3. Binary search over error tolerance with lattice point enumeration

Theoretical foundation:
- Dyadic linear programming framework: Abdi et al. (2024), "Dyadic linear
  programming and extensions", https://www.andrew.cmu.edu/user/gc0v/webpub/main.pdf
- Remez exchange algorithm: Parks & McClellan (1972)
- Discrete coefficient filter design: Lim & Parker (1983), Kodek (1980)

References:
    Abdi, A., Cornuéjols, G., Guenin, B., & Tunçel, L. (2024). Dyadic linear
    programming and extensions. Mathematical Programming.
"""

from __future__ import annotations

import math
import numpy as np

from dataclasses import dataclass
from collections.abc import Callable, Iterable, Sequence

from numpy.polynomial.chebyshev import Chebyshev
from numpy.polynomial.polynomial import Polynomial

from Allocator.Interpreter.main.consts import LOGGER, DYADIC_POLY_PREFIX
from Allocator.Interpreter.math.math_utils import ceil_div
from Allocator.Interpreter.poly.remez_cheb import remez_monomial, sup_norm


@dataclass(frozen=True, slots=True)
class DyadicPoly:
    numerators: np.ndarray[np.integer]
    m_bits: np.ndarray[np.uint8]
    a: float
    b: float

    def coeffs_float(self) -> np.ndarray:
        return self.numerators.astype(float) / (2.0 ** self.m_bits.astype(float))

    def eval(self, x: np.ndarray) -> np.ndarray:
        return np.polyval(self.coeffs_float()[::-1], x)

    def degree(self) -> int:
        return len(self.numerators) - 1


@dataclass(frozen=True, slots=True)
class BMTResult:
    dyadic: DyadicPoly
    coeffs_float: np.ndarray
    K: float
    candidates_scanned: int


@dataclass(frozen=True, slots=True)
class IntPolytope:
    A: list[list[int]]
    L: list[int]
    U: list[int]

    def rows(self) -> int:
        return len(self.L)

    def cols(self) -> int:
        return len(self.A[0]) if self.A else 0


def build_polytope_int(
    f: Callable[[np.ndarray], np.ndarray],
    a: float,
    b: float,
    n: int,
    m_bits: Sequence[int],
    K: float,
    nodes_power_of_two: int = 10,
    rational_bits: int = 32,
) -> tuple[IntPolytope, int]:
    S = rational_bits
    twoS = 1 << S
    A_num = int(np.floor(a * twoS))
    B_num = int(np.ceil(b * twoS))
    d = 1 << nodes_power_of_two
    Sx = S + nodes_power_of_two

    x_float = (A_num * d + np.arange(d + 1) * (B_num - A_num)) / (d * float(twoS))
    fx = f(x_float)

    max_exp = max(Sx * j + int(m_bits[j]) for j in range(n + 1))
    E = max(max_exp, S)

    x_num = (A_num * d + np.arange(d + 1, dtype=object) * (B_num - A_num)).astype(object)

    A_rows: list[list[int]] = []
    L_vec: list[int] = []
    U_vec: list[int] = []

    for i in range(d + 1):
        xi_num = int(x_num[i])
        row: list[int] = []
        pow_cache = 1
        for j in range(n + 1):
            shift = E - (Sx * j + int(m_bits[j]))
            if shift < 0:
                raise ValueError('Negative shift; increase rational_bits or adjust settings.')
            aij = pow_cache << shift
            row.append(int(aij))
            if j < n:
                pow_cache = pow_cache * xi_num
        A_rows.append(row)

        lo = int(np.floor((fx[i] - K) * (1 << E)))
        hi = int(np.ceil((fx[i] + K) * (1 << E)))
        L_vec.append(lo)
        U_vec.append(hi)

    maxA = max((max(abs(v) for v in row) if row else 0) for row in A_rows) if A_rows else 0
    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"polytope: rows={len(L_vec)}, cols={n+1}, E={E}, nodes_pow2={nodes_power_of_two}, max|A_ij|={maxA}"
    ))

    return IntPolytope(A=A_rows, L=L_vec, U=U_vec), E


def _row_bounds_partial_int(
    poly: IntPolytope,
    assigned: dict,
    ranges: list[tuple[int, int]],
) -> tuple[list[int], list[int]]:
    rows, cols = poly.rows(), poly.cols()
    Lres = poly.L.copy()
    Ures = poly.U.copy()

    for j, zj in assigned.items():
        for i in range(rows):
            c = poly.A[i][j] * zj
            Lres[i] -= c
            Ures[i] -= c

    for j in range(cols):
        if j in assigned:
            continue
        zlo, zhi = ranges[j]
        if zlo == zhi:
            for i in range(rows):
                c = poly.A[i][j] * zlo
                Lres[i] -= c
                Ures[i] -= c
        else:
            for i in range(rows):
                aij = poly.A[i][j]
                if aij >= 0:
                    Lres[i] -= aij * zhi
                    Ures[i] -= aij * zlo
                else:
                    Lres[i] -= aij * zlo
                    Ures[i] -= aij * zhi
    return Lres, Ures


def _tighten_range_for_var_int(
    poly: IntPolytope,
    assigned: dict,
    ranges: list[tuple[int, int]],
    jvar: int,
) -> tuple[int, int]:
    rows, cols = poly.rows(), poly.cols()
    Lres = poly.L.copy()
    Ures = poly.U.copy()

    for j, zj in assigned.items():
        for i in range(rows):
            c = poly.A[i][j] * zj
            Lres[i] -= c
            Ures[i] -= c

    for j in range(cols):
        if j in assigned or j == jvar:
            continue
        zlo, zhi = ranges[j]
        for i in range(rows):
            aij = poly.A[i][j]
            if aij >= 0:
                Lres[i] -= aij * zhi
                Ures[i] -= aij * zlo
            else:
                Lres[i] -= aij * zlo
                Ures[i] -= aij * zhi

    zlo, zhi = ranges[jvar]
    for i in range(rows):
        aij = poly.A[i][jvar]
        if aij == 0:
            continue
        if aij > 0:
            low = ceil_div(Lres[i], aij)
            high = Ures[i] // aij
        else:
            low = ceil_div(Ures[i], aij)
            high = Lres[i] // aij
        if low > zlo:
            zlo = int(low)
        if high < zhi:
            zhi = int(high)
        if zlo > zhi:
            break
    return zlo, zhi


def enumerate_polytope_integer_points_int(
    poly: IntPolytope,
    z0: Sequence[int],
    initial_radius: int,
    max_nodes: int,
    var_order: list[int] | None = None,
    frozen: list[bool] | None = None,
    stop_after: int | None = None,
) -> Iterable[np.ndarray]:
    if max_nodes <= 0:
        return

    nvars = poly.cols()

    ranges: list[tuple[int, int]] = []
    for j in range(nvars):
        R = 0 if (frozen is not None and frozen[j]) else initial_radius
        ranges.append((int(z0[j]) - R, int(z0[j]) + R))

    # Fixed-point tightening of all variable ranges before search
    changed = True
    iters = 0
    while changed and iters < 3 * max(1, nvars):
        changed = False
        iters += 1
        for j in range(nvars):
            lo_old, hi_old = ranges[j]
            lo_new, hi_new = _tighten_range_for_var_int(poly, {}, ranges, j)
            if lo_new > lo_old or hi_new < hi_old:
                ranges[j] = (max(lo_old, lo_new), min(hi_old, hi_new))
                changed = True
            if ranges[j][0] > ranges[j][1]:
                LOGGER.info(DYADIC_POLY_PREFIX.format(
                    f"enumerate: infeasible after initial tighten on var {j}, aborting"
                ))
                return

    # Order variables by current feasible width (narrower first) to prune faster
    widths = [ranges[j][1] - ranges[j][0] for j in range(nvars)]
    order_by_width = sorted(range(nvars), key=lambda j: widths[j])
    var_order = order_by_width if var_order is None else var_order

    visited = 0
    expanded = 0
    pruned_empty = 0

    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"enumerate: nvars={nvars}, initial_radius={initial_radius}, max_nodes={max_nodes}, "
        f"iters_tighten={iters}, widths={widths}, order={var_order}"
    ))

    # Try z0 first if feasible
    def _feasible_with(assigned: dict) -> bool:
        Lres, Ures = _row_bounds_partial_int(poly, assigned, ranges)
        for i in range(poly.rows()):
            if not (Lres[i] <= 0 <= Ures[i]):
                return False
        return True

    yielded = 0
    if _feasible_with({j: int(z0[j]) for j in range(nvars)}):
        visited += 1
        yielded += 1
        yield np.array([int(z0[j]) for j in range(nvars)], dtype=int)
        if visited >= max_nodes or (stop_after is not None and yielded >= stop_after):
            LOGGER.info(DYADIC_POLY_PREFIX.format(
                f"enumerate done: visited={visited}, expanded={expanded}, pruned_empty={pruned_empty}"
            ))
            return

    def dfs(level: int, assigned: dict, ranges_cur: list[tuple[int, int]]):
        nonlocal visited, expanded, pruned_empty, yielded
        if expanded >= max_nodes:
            return
        if stop_after is not None and yielded >= stop_after:
            return

        expanded += 1

        if level == nvars:
            visited += 1
            yielded += 1
            yield np.array([assigned[j] for j in range(nvars)], dtype=int)
            return

        j = var_order[level]
        lo, hi = _tighten_range_for_var_int(poly, assigned, ranges_cur, j)
        if lo > hi:
            pruned_empty += 1
            return

        center = int(z0[j])
        maxspan = max(center - lo, hi - center)

        for d in range(0, maxspan + 1):
            cand_list = [center] if d == 0 else [center - d, center + d]
            for cand in cand_list:
                if cand < lo or cand > hi:
                    continue
                assigned_next = dict(assigned)
                assigned_next[j] = cand
                Lres, Ures = _row_bounds_partial_int(poly, assigned_next, ranges_cur)
                feasible = True
                for i in range(poly.rows()):
                    if not (Lres[i] <= 0 <= Ures[i]):
                        feasible = False
                        break
                if feasible:
                    ranges_next = list(ranges_cur)
                    ranges_next[j] = (cand, cand)
                    yield from dfs(level + 1, assigned_next, ranges_next)
                    if expanded >= max_nodes or (stop_after is not None and yielded >= stop_after):
                        return

    for z in dfs(0, {}, ranges):
        yield z

    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"enumerate done: visited={visited}, expanded={expanded}, pruned_empty={pruned_empty}"
    ))


def _power_t_to_power_x(c_t: np.ndarray, a: float, b: float) -> np.ndarray:
    n = len(c_t) - 1
    mid = (a + b) / 2.0
    rad = (b - a) / 2.0 if b != a else 1.0
    out = np.zeros(n + 1, dtype=float)
    inv_rad = 1.0 / rad
    for j in range(n + 1):
        v = c_t[j]
        if v == 0.0:
            continue
        scale = v * (inv_rad ** j)
        for k in range(j + 1):
            out[k] += scale * math.comb(j, k) * ((-mid) ** (j - k))
    return out


def _greedy_local_descent(
    f: Callable[[np.ndarray], np.ndarray],
    z: np.ndarray,
    m_bits: np.ndarray,
    a: float,
    b: float,
    grid: int,
    frozen: list[bool],
    max_passes: int = 2,
) -> tuple[np.ndarray, float]:
    q = z.astype(float) / (2.0 ** m_bits)
    bestK, _, _ = sup_norm(f, q, a, b, grid=grid)

    for _ in range(max_passes):
        improved = False
        for j in range(len(z)):
            if frozen[j]:
                continue
            base = z[j]
            best_local = base
            best_local_K = bestK
            for step in (-1, 1):
                cand = base + step
                z_temp = z.copy()
                z_temp[j] = cand
                q = z_temp.astype(float) / (2.0 ** m_bits)
                Kc, _, _ = sup_norm(f, q, a, b, grid=grid)
                if Kc < best_local_K:
                    best_local_K = Kc
                    best_local = cand
            z[j] = best_local
            if best_local_K < bestK:
                bestK = best_local_K
                improved = True
        if not improved:
            break

    return z, bestK


def _seed_power_x_via_tremez(
    f: Callable[[np.ndarray], np.ndarray],
    degree: int,
    a: float,
    b: float,
    iters: int,
    grid: int,
) -> np.ndarray:
    mid = (a + b) / 2.0
    rad = (b - a) / 2.0 if b != a else 1.0

    def f_t(t: np.ndarray) -> np.ndarray:
        return f(mid + rad * t)

    seed_t = remez_monomial(f_t, degree=degree, a=-1.0, b=1.0, iters=iters, grid=32769)
    s1 = np.array(seed_t, dtype=float)
    s2 = s1[::-1]

    p1 = _power_t_to_power_x(s1, a, b)
    p2 = _power_t_to_power_x(s2, a, b)

    K1, _, _ = sup_norm(f, p1, a, b, grid=grid)
    K2, _, _ = sup_norm(f, p2, a, b, grid=grid)

    LOGGER.info(DYADIC_POLY_PREFIX.format(f"seed via t->x candidates: K_as_is={K1}, K_reversed={K2}"))

    if np.isfinite(K1) and (K1 <= K2 or not np.isfinite(K2)):
        chosen = p1
        Kc = K1
    else:
        chosen = p2
        Kc = K2

    if not np.isfinite(Kc) or Kc > 1e-2:
        xs = np.linspace(a, b, 2049)
        ys = f(xs)
        cheb = Chebyshev.fit(xs, ys, deg=degree, domain=[a, b]).convert(kind=Polynomial, domain=[a, b])
        pf = np.array(cheb.coef, dtype=float)
        Kf, _, _ = sup_norm(f, pf, a, b, grid=grid)
        LOGGER.info(DYADIC_POLY_PREFIX.format(f"seed fallback cheb_fit: K={Kf}"))
        if np.isfinite(Kf) and Kf < Kc:
            chosen = pf
            Kc = Kf

    a0 = chosen[0] if len(chosen) > 0 else 0.0
    a1 = chosen[1] if len(chosen) > 1 else 0.0
    LOGGER.info(DYADIC_POLY_PREFIX.format(f"seed via t->x chosen: K={Kc}, a0={a0}, a1={a1}"))
    return chosen


def _parity_freeze_mask(
    f: Callable[[np.ndarray], np.ndarray],
    a: float,
    b: float,
    degree: int,
) -> list[bool]:
    mask = [False] * (degree + 1)
    if not (abs(a + b) < 1e-15):
        LOGGER.info(DYADIC_POLY_PREFIX.format('parity freeze: non-symmetric interval; no parity constraints'))
        return mask

    xs = np.linspace(0.0, (b - a) / 2.0, 257)
    odd_err = 0.0
    even_err = 0.0
    denom = 1e-12
    for x in xs:
        fx = f(np.array([x]))[0]
        fmx = f(np.array([-x]))[0]
        odd_err = max(odd_err, abs(fx + fmx))
        even_err = max(even_err, abs(fx - fmx))
        denom = max(denom, abs(fx), abs(fmx))

    is_odd = (odd_err / denom) < 1e-8
    is_even = (even_err / denom) < 1e-8

    if is_odd:
        for j in range(0, degree + 1, 2):
            mask[j] = True
    elif is_even:
        for j in range(1, degree + 1, 2):
            mask[j] = True

    LOGGER.info(DYADIC_POLY_PREFIX.format(f"parity freeze: is_odd={is_odd}, is_even={is_even}, mask={mask}"))
    return mask


def bmt_truncated_minimax(
    f: Callable[[np.ndarray], np.ndarray],
    degree: int,
    a: float,
    b: float,
    m_bits: Sequence[int],
    nodes_pow2: int = 10,
    rational_bits: int = 32,
    initial_radius: int = 64,
    max_nodes: int = 1_000_000,
    remez_iters: int = 12,
    grid_sup: int = 65537,
    refine_binary_search: int = 18,
    per_k_cap: int = 2048,   # max candidates to test per bisection iteration
) -> BMTResult:
    n = degree
    m_bits = np.asarray(m_bits, dtype=int)

    p_float = _seed_power_x_via_tremez(f, degree=n, a=a, b=b, iters=remez_iters, grid=grid_sup)
    LB, _, _ = sup_norm(f, p_float, a, b, grid=grid_sup)
    z0 = np.rint(p_float * (2.0 ** m_bits)).astype(int)
    frozen = _parity_freeze_mask(f, a, b, n)
    for j in range(n + 1):
        if frozen[j]:
            z0[j] = 0

    z0, UB = _greedy_local_descent(f, z0.copy(), m_bits, a, b, grid_sup, frozen, max_passes=2)

    q0 = z0.astype(float) / (2.0 ** m_bits)
    UB2, _, _ = sup_norm(f, q0, a, b, grid=grid_sup)
    UB = min(UB, UB2)
    if UB < LB:
        UB = LB

    best_z = z0.copy()
    best_K = UB
    scanned = 0

    lo, hi = LB, UB
    for it in range(refine_binary_search):
        if scanned >= max_nodes:
            break

        K = (lo + hi) / 2.0

        poly, _ = build_polytope_int(
            f=f, a=a, b=b, n=n, m_bits=m_bits, K=K,
            nodes_power_of_two=nodes_pow2, rational_bits=rational_bits
        )

        improved = False
        found = False
        limit_this_round = min(per_k_cap, max_nodes - scanned)

        for z in enumerate_polytope_integer_points_int(
            poly=poly,
            z0=best_z.tolist(),              # center around current best, not just initial
            initial_radius=initial_radius,
            max_nodes=limit_this_round,
            var_order=None,
            frozen=frozen,
            stop_after=per_k_cap,
        ):
            scanned += 1
            found = True
            q_coeffs = z.astype(float) / (2.0 ** m_bits)
            Kcand, _, _ = sup_norm(f, q_coeffs, a, b, grid=grid_sup)
            if Kcand < best_K:
                best_K = Kcand
                best_z = z.copy()
                improved = True
                hi = min(hi, best_K)

                # If we met the target K, no need to scan more in this round
                if best_K <= K:
                    break

            if scanned >= max_nodes:
                break

        if improved and best_K <= K:
            hi = min(hi, best_K)
        else:
            lo = max(lo, K)

        LOGGER.info(DYADIC_POLY_PREFIX.format(
            f"bsearch it={it}: K_try={K}, improved={improved}, found_any={found}, scanned={scanned}, best_K={best_K}, interval=[{lo},{hi}]"
        ))

    result = BMTResult(
        dyadic=DyadicPoly(numerators=best_z, m_bits=m_bits, a=a, b=b),
        coeffs_float=p_float,
        K=float(best_K),
        candidates_scanned=int(scanned),
    )
    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"done: degree={n}, best_K={result.K}, scanned={result.candidates_scanned}"
    ))
    return result
