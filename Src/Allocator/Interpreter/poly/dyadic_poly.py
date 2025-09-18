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


@dataclass
class DyadicPoly:
    numerators: np.ndarray
    m_bits: np.ndarray
    a: float
    b: float

    def coeffs_float(self) -> np.ndarray:
        return self.numerators.astype(float) / (2.0 ** self.m_bits.astype(float))

    def eval(self, x: np.ndarray) -> np.ndarray:
        return np.polyval(self.coeffs_float()[::-1], x)

    def degree(self) -> int:
        return len(self.numerators) - 1


@dataclass
class BMTResult:
    dyadic: DyadicPoly
    coeffs_float: np.ndarray
    K: float
    candidates_scanned: int


@dataclass
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


def _variable_order_int(poly: IntPolytope) -> list[int]:
    rows, cols = poly.rows(), poly.cols()
    scores = []
    for j in range(cols):
        s = 0
        for i in range(rows):
            s += abs(poly.A[i][j])
        scores.append((s, j))
    scores.sort(reverse=True)
    order = [j for _, j in scores]
    LOGGER.info(DYADIC_POLY_PREFIX.format(f"var order: {order}"))
    return order


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
) -> Iterable[np.ndarray]:
    nvars = poly.cols()
    if var_order is None:
        var_order = _variable_order_int(poly)

    ranges: list[tuple[int, int]] = []
    for j in range(nvars):
        R = initial_radius
        ranges.append((int(z0[j]) - R, int(z0[j]) + R))

    visited = 0
    expanded = 0
    pruned_empty = 0

    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"enumerate: nvars={nvars}, initial_radius={initial_radius}, max_nodes={max_nodes}"
    ))

    def dfs(level: int, assigned: dict, ranges_cur: list[tuple[int, int]]):
        nonlocal visited, expanded, pruned_empty
        if expanded >= max_nodes:
            return
        expanded += 1

        if level == nvars:
            visited += 1
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
                    if expanded >= max_nodes or visited >= max_nodes:
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
        # ((x - mid)/rad)^j = (1/rad^j) * sum_{k=0}^j C(j,k) * x^k * (-mid)^{j-k}
        for k in range(j + 1):
            out[k] += scale * math.comb(j, k) * ((-mid) ** (j - k))
    return out


def _candidate_polys_from_seed(seed: np.ndarray, a: float, b: float) -> list[tuple[str, np.ndarray]]:
    cand: list[tuple[str, np.ndarray]] = []
    s_asc = np.array(seed, dtype=float)
    s_desc = s_asc[::-1]
    cand.append(('seed_power_x_asc', s_asc))
    cand.append(('seed_power_x_desc', s_desc))
    # Try interpreting seed as Chebyshev in t, convert to Polynomial in x
    cand.append((
        'cheb_to_power_x_from_asc',
        np.array(Chebyshev(s_asc, domain=[-1.0, 1.0]).convert(kind=Polynomial, domain=[a, b]).coef, dtype=float)
    ))
    cand.append((
        'cheb_to_power_x_from_desc',
        np.array(Chebyshev(s_desc, domain=[-1.0, 1.0]).convert(kind=Polynomial, domain=[a, b]).coef, dtype=float)
    ))
    # Try interpreting seed as power in t, expand to power in x
    cand.append(('power_t_to_power_x_from_asc', _power_t_to_power_x(s_asc, a, b)))
    cand.append(('power_t_to_power_x_from_desc', _power_t_to_power_x(s_desc, a, b)))
    return cand


def _normalize_seed_power_basis(
    f: Callable[[np.ndarray], np.ndarray],
    seed: np.ndarray,
    a: float,
    b: float,
    grid: int,
) -> tuple[np.ndarray, str]:
    LOGGER.info(DYADIC_POLY_PREFIX.format(f"seed raw first coeffs (up to 5): {np.array(seed, dtype=float)[:5].tolist()}"))

    cands = _candidate_polys_from_seed(seed, a, b)
    best = None
    best_tag = ''
    best_K = float('inf')
    for tag, coeffs in cands:
        K, _, _ = sup_norm(f, coeffs, a, b, grid=grid)
        LOGGER.info(DYADIC_POLY_PREFIX.format(f"candidate {tag}: K={K}"))
        if K < best_K:
            best_K = K
            best = coeffs
            best_tag = tag

    # Derivative sanity check at interval mid
    mid = (a + b) / 2.0
    h = 1e-6 * max(1.0, abs(b - a))
    df_mid = (f(np.array([mid + h]))[0] - f(np.array([mid - h]))[0]) / (2 * h)
    a1 = 0.0
    if best is not None and len(best) >= 2:
        # p'(x) = sum_{k>=1} k * a_k * x^{k-1}
        a1 = 0.0
        xpow = 1.0  # mid^{0}
        for k in range(1, len(best)):
            a1 += k * best[k] * xpow
            xpow *= mid
    LOGGER.info(DYADIC_POLY_PREFIX.format(f"normalize picked={best_tag}, K={best_K}, slope_check: poly'({mid})~{a1}, f'({mid})~{df_mid}"))

    return (best if best is not None else np.array(seed, dtype=float)), best_tag


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
) -> BMTResult:
    n = degree
    m_bits = np.asarray(m_bits, dtype=int)
    assert len(m_bits) == n + 1

    seed = remez_monomial(f, degree=n, a=a, b=b, iters=remez_iters, grid=32769)
    p_float, picked = _normalize_seed_power_basis(f, seed, a, b, grid=grid_sup)

    LB, _, _ = sup_norm(f, p_float, a, b, grid=grid_sup)

    z0 = np.rint(p_float * (2.0 ** m_bits)).astype(int)
    q0 = z0.astype(float) / (2.0 ** m_bits)
    UB, _, _ = sup_norm(f, q0, a, b, grid=grid_sup)
    if UB < LB:
        UB = LB

    LOGGER.info(DYADIC_POLY_PREFIX.format(
        f"search init: degree={n}, LB={LB}, UB={UB}, picked_seed='{picked}', nodes_pow2={nodes_pow2}, initial_radius={initial_radius}, max_nodes={max_nodes}"
    ))

    best_z = z0.copy()
    best_K = UB
    scanned = 0

    lo, hi = LB, UB
    for it in range(refine_binary_search):
        K = (lo + hi) / 2.0

        poly, _ = build_polytope_int(
            f=f, a=a, b=b, n=n, m_bits=m_bits, K=K,
            nodes_power_of_two=nodes_pow2, rational_bits=rational_bits
        )

        improved = False
        found = False
        for z in enumerate_polytope_integer_points_int(
            poly=poly,
            z0=z0.tolist(),
            initial_radius=initial_radius,
            max_nodes=max_nodes - scanned,
            var_order=None,
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
            if scanned >= max_nodes:
                break

        if improved and best_K <= K:
            hi = min(hi, best_K)
        else:
            lo = max(lo, K)

        LOGGER.info(DYADIC_POLY_PREFIX.format(
            f"bsearch it={it}: K_try={K}, improved={improved}, found_any={found}, scanned={scanned}, best_K={best_K}, interval=[{lo},{hi}]"
        ))

        if scanned >= max_nodes:
            break

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
