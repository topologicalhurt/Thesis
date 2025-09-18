import numpy as np

from collections.abc import Callable


def _to_unit_interval(x: np.ndarray, a: float, b: float) -> np.ndarray:
    mid = (a + b) / 2.0
    rad = (b - a) / 2.0 if b != a else 1.0
    return (x - mid) / rad


def _from_unit_interval(t: np.ndarray, a: float, b: float) -> np.ndarray:
    mid = (a + b) / 2.0
    rad = (b - a) / 2.0
    return mid + rad * t


def _remez_cheb(
    f: Callable[[np.ndarray], np.ndarray],
    degree: int,
    a: float,
    b: float,
    iters: int = 15,
    grid: int = 32769,
    stagnation_tol: float = 1e-12,
) -> np.ndarray:
    """
    Near-minimax Chebyshev-series coefficients on t∈[-1,1] for f over x∈[a,b].
    """
    m = degree + 2
    tg = np.cos(np.pi * np.arange(grid) / (grid - 1))            # Chebyshev extrema on [-1,1]
    xg = _from_unit_interval(tg, a, b)
    fg = f(xg)

    # Initial support: exactly m Chebyshev extrema points
    t_support = np.cos(np.pi * np.arange(m) / (m - 1))
    prev_E = None

    for _ in range(iters):
        V = np.polynomial.chebyshev.chebvander(t_support, degree)                         # shape (m, degree+1)
        alt = ((-1.0) ** np.arange(len(t_support))).reshape(-1, 1)
        A = np.hstack([V, alt])                                   # unknowns: c[0..n], E
        rhs = f(_from_unit_interval(t_support, a, b))
        sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        c = sol[:-1]
        E = sol[-1]

        # Error on dense grid
        e = np.polynomial.chebyshev.Chebyshev(c)(tg) - fg
        abs_e = np.abs(e)
        order = np.argsort(abs_e)[::-1]

        # Select m points with attempted alternation, pad by magnitude if needed
        sel = []
        used = set()
        if order.size:
            first = order[0]
            sel.append(first); used.add(first)
            last_sign = np.sign(e[first]) or 1.0
            for idx in order[1:]:
                if idx in used:
                    continue
                sgn = np.sign(e[idx]) or 1.0
                if sgn * last_sign < 0:
                    sel.append(idx); used.add(idx)
                    last_sign = sgn
                    if len(sel) == m: break
            if len(sel) < m:
                for idx in order:
                    if idx in used: continue
                    sel.append(idx); used.add(idx)
                    if len(sel) == m: break

        # Safety pad
        if len(sel) < m:
            for idx in range(grid):
                if idx in used: continue
                sel.append(idx)
                if len(sel) == m: break

        sel = np.array(sorted(sel))[:m]
        t_support_new = tg[sel]

        # Stagnation
        if prev_E is not None and abs(E - prev_E) <= stagnation_tol * (1.0 + abs(prev_E)):
            t_support = t_support_new
            break
        prev_E = E
        t_support = t_support_new

    return c


def remez_monomial(
    f: Callable[[np.ndarray], np.ndarray],
    degree: int,
    a: float,
    b: float,
    iters: int = 15,
    grid: int = 32769,
) -> np.ndarray:
    """
    Near-minimax polynomial (float) in monomial basis on x∈[a,b].
    """
    c_cheb = _remez_cheb(f, degree, a, b, iters=iters, grid=grid)
    # p_t(t) in Chebyshev basis over [-1,1]
    p_t = np.polynomial.chebyshev.Chebyshev(c_cheb, domain=[-1.0, 1.0])
    # Convert to power basis over x∈[a,b]
    p_x: np.polynomial.Polynomial = p_t.convert(kind=np.polynomial.Polynomial, domain=[a, b])
    return np.array(p_x.coef, dtype=float)  # low->high


def sup_norm(
    f: Callable[[np.ndarray], np.ndarray],
    poly_coeffs: np.ndarray,
    a: float,
    b: float,
    grid: int = 65537,
) -> tuple[float, float, float]:
    """
    Return (max_abs_error, x_at_max, sign) on a dense Chebyshev-extrema grid in [a,b].
    """
    tg = np.cos(np.pi * np.arange(grid) / (grid - 1))
    xg = _from_unit_interval(tg, a, b)
    fg = f(xg)
    pg = np.polyval(poly_coeffs[::-1], xg)  # np.polyval expects high->low
    err = fg - pg
    idx = int(np.argmax(np.abs(err)))
    return float(abs(err[idx])), float(xg[idx]), float(np.sign(err[idx]) or 1.0)
