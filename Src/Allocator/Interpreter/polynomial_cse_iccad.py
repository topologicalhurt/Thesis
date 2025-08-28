"""
Polynomial optimization utilities with a matrix-based representation (ICCAD 2004 compatible)
plus practical univariate evaluators (Horner/Estrin).
"""
from __future__ import annotations
from operator import itemgetter

import numpy as np
import re

from dataclasses import dataclass
from collections.abc import Sequence, Set

from Allocator.Interpreter.helpers import join_regex


@dataclass(frozen=True)
class MatrixRow:
    """A single product term (cube): sign * Π variables[i]^exponents[i]."""
    sign: int
    exponents: list[int]
    term_id: int | None = None

    def copy(self) -> 'MatrixRow':
        return MatrixRow(self.sign, self.exponents.copy(), self.term_id)


class PolynomialMatrix:
    """Matrix representation of an SOP polynomial.

    - variables: ordered list of literal names (e.g., ['x', 'S3', 'S5']).
    - rows: cubes with non-negative integer exponents and a sign.
    """
    def __init__(self, variables: list[str]):
        self.variables = variables
        self.rows: list[MatrixRow] = []
        self.var_index = {v: i for i, v in enumerate(variables)}

    def add_term(self, sign: int, exponents: dict[str, int], term_id: int | None = None):
        exp_list = [0] * len(self.variables)
        for var, exp in exponents.items():
            idx = self.var_index.get(var)
            if idx is not None:
                exp_list[idx] = int(exp)
        self.rows.append(MatrixRow(1 if sign >= 0 else -1, exp_list, term_id))

    def copy(self) -> 'PolynomialMatrix':
        m = PolynomialMatrix(self.variables.copy())
        m.rows = [r.copy() for r in self.rows]
        return m

    def __str__(self) -> str:
        parts: list[str] = []
        for r in self.rows:
            factors: list[str] = []
            for i, e in enumerate(r.exponents):
                if e > 0:
                    v = self.variables[i]
                    factors.append(v if e == 1 else f"{v}^{e}")
            term = '*'.join(factors) if factors else '1'
            if r.sign < 0:
                term = f"-{term}"
            elif parts:
                term = f"+{term}"
            parts.append(term)
        return ' '.join(parts) if parts else '0'


class ICCADOptimizer:
    def __init__(self):
        self.coefficient_map: dict[str, float] = {}

    # Kernel extraction (concise, functional)
    def find_kernels(self, expressions: list[PolynomialMatrix], literals: list[str]) -> list[tuple[PolynomialMatrix, PolynomialMatrix]]:
        """Extract kernels and co-kernels for each expression (Figure 3, high level)."""
        out: list[tuple[PolynomialMatrix, PolynomialMatrix]] = []
        for expr in expressions:
            one = PolynomialMatrix(expr.variables)
            one.add_term(1, {})
            out.append((expr.copy(), one))
            empty = PolynomialMatrix(expr.variables)
            out.extend(self._kernels(0, expr, empty, literals))
        return out

    def _kernels(self, i: int, P: PolynomialMatrix, d: PolynomialMatrix, literals: list[str]) -> list[tuple[PolynomialMatrix, PolynomialMatrix]]:
        """Recursive kernel extraction per Figure 3 (simplified, polynomial domain)."""
        D: list[tuple[PolynomialMatrix, PolynomialMatrix]] = []
        for j in range(i, len(literals)):
            lit = literals[j]
            if lit not in P.var_index:
                continue
            idx = P.var_index[lit]
            count = sum(1 for r in P.rows if r.exponents[idx] > 0)
            if count <= 1:
                continue
            Ft = self._divide_literal(P, lit)
            if not Ft.rows:
                continue
            C = self._largest_common_cube(Ft)
            if not self._check_literal_ordering(C, j, literals, P.variables):
                continue
            F1 = self._divide_by_cube(Ft, C)
            Lj = PolynomialMatrix(P.variables)
            Lj.add_term(1, {lit: 1})
            D1 = self._merge_cubes(d, C, Lj)
            if len(F1.rows) >= 2:
                D.append((F1, D1))
                D.extend(self._kernels(j, F1, D1, literals))
        return D

    def _divide_literal(self, P: PolynomialMatrix, literal: str) -> PolynomialMatrix:
        """Divide P by literal (reduce literal exponent by 1 in rows containing it)."""
        idx = P.var_index.get(literal)
        if idx is None:
            return PolynomialMatrix(P.variables)
        Q = PolynomialMatrix(P.variables)
        for r in P.rows:
            if r.exponents[idx] > 0:
                nr = r.copy()
                nr.exponents[idx] -= 1
                Q.rows.append(nr)
        return Q

    def _divide_by_cube(self, P: PolynomialMatrix, C: PolynomialMatrix) -> PolynomialMatrix:
        """Divide P by cube C (vector subtraction of exponents for rows containing C)."""
        if not C.rows:
            return P.copy()
        d = C.rows[0].exponents
        Q = PolynomialMatrix(P.variables)
        for r in P.rows:
            if all(r.exponents[i] >= d[i] for i in range(len(d))):
                nr = r.copy()
                for i in range(len(d)):
                    nr.exponents[i] -= d[i]
                Q.rows.append(nr)
        return Q

    def _largest_common_cube(self, P: PolynomialMatrix) -> PolynomialMatrix:
        """Greatest common cube (component-wise min exponents across rows)."""
        if not P.rows:
            return PolynomialMatrix(P.variables)
        common = P.rows[0].exponents.copy()
        for r in P.rows[1:]:
            for i in range(len(common)):
                common[i] = min(common[i], r.exponents[i])
        C = PolynomialMatrix(P.variables)
        exp = {P.variables[i]: e for i, e in enumerate(common) if e > 0}
        if exp:
            C.add_term(1, exp)
        return C

    def _merge_cubes(self, C1: PolynomialMatrix, C2: PolynomialMatrix, C3: PolynomialMatrix) -> PolynomialMatrix:
        """Add exponents of three cubes component-wise (empty cube treated as zeros)."""
        n = len(C1.variables)
        e1 = C1.rows[0].exponents if C1.rows else [0] * n
        e2 = C2.rows[0].exponents if C2.rows else [0] * n
        e3 = C3.rows[0].exponents if C3.rows else [0] * n
        merged = [e1[i] + e2[i] + e3[i] for i in range(n)]
        M = PolynomialMatrix(C1.variables)
        exp = {C1.variables[i]: v for i, v in enumerate(merged) if v > 0}
        if exp:
            M.add_term(1, exp)
        return M

    def _check_literal_ordering(self, C: PolynomialMatrix, j: int, literals: list[str], variables: list[str]) -> bool:
        """Check (Lk ∈ C) ⇒ (k < j) under the provided literals ordering."""
        if not C.rows:
            return True
        for i, e in enumerate(C.rows[0].exponents):
            if e > 0:
                v = variables[i]
                if v in literals and literals.index(v) >= j:
                    return False
        return True

    def form_kernel_cube_matrix(self, pairs: list[tuple[PolynomialMatrix, PolynomialMatrix]]) -> dict[str, list[int]]:
        """Construct a simple KCM: map cube-string -> set of pair indices where it appears."""
        kcm: dict[str, list[int]] = {}
        all_cubes: Set[str] = set()

        # collect cube keys
        for kernel, _ in pairs:
            for row in kernel.rows:
                key = str(row)
                all_cubes.add(key)

        # fill presence by pair index
        for idx, (kernel, _) in enumerate(pairs):
            for row in kernel.rows:
                key = str(row)
                if key in all_cubes:
                    kcm.setdefault(key, []).append(idx)
        return kcm

    # Simple rectangle finder/selector (not used by univariate codegen)
    def _find_favorable_rectangles(self, kcm: dict[str, list[int]]) -> list[tuple[Set[int], Set[str]]]:
        """Heuristic rectangle candidates: pairwise or single-column with multiple rows."""
        rects: list[tuple[Set[int], Set[str]]] = []
        keys = list(kcm.keys())

        # pairwise columns
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                inter = set(kcm.get(a, [])) & set(kcm.get(b, []))
                if inter:
                    rects.append((inter, {a, b}))

        # single-column rectangles with multiple rows
        for k, rows in kcm.items():
            if len(rows) >= 2:
                rects.append((set(rows), {k}))
        return rects

    def _select_best_rectangle(self, rects: list[tuple[Set[int], Set[str]]]) -> tuple[Set[int], Set[str]] | None:
        """Pick rectangle maximizing (R-1)*(C-1) as a simple value proxy."""
        if not rects:
            return None
        return max(rects, key=lambda rc: (len(rc[0]) - 1) * (len(rc[1]) - 1))

    def _rectangle_to_expression(self, rect: tuple[Set[int], Set[str]], pairs: list[tuple[PolynomialMatrix, PolynomialMatrix]]) -> PolynomialMatrix:
        """Convert a rectangle back to an expression (subset of kernel rows)."""
        rows, cubes = rect
        if not rows:
            return PolynomialMatrix(pairs[0][0].variables) if pairs else PolynomialMatrix([])
        any_idx = next(iter(rows))
        kernel, _ = pairs[any_idx]
        out = PolynomialMatrix(kernel.variables)
        cube_strs = set(cubes)
        for r in kernel.rows:
            if str(r) in cube_strs:
                out.rows.append(r.copy())
        return out

    def _rewrite_with_cse(self, exprs: list[PolynomialMatrix], cse_expr: PolynomialMatrix, cse_var: str) -> list[PolynomialMatrix]:
        """Rewrite expressions by factoring out a cube and introducing cse_var.

        Strategy (conservative):
        - Determine a factor cube C from cse_expr: if single-row use it; else use
          the largest common cube. If none, no changes.
        - For each expression, append literal cse_var and set exponent to 1 in any
          row divisible by C while subtracting C's exponents from that row.
        """
        if not cse_expr.rows:
            return exprs
        if len(cse_expr.rows) == 1:
            C_vec = cse_expr.rows[0].exponents
            C_vars = cse_expr.variables
        else:
            C = self._largest_common_cube(cse_expr)
            if not C.rows:
                return exprs
            C_vec = C.rows[0].exponents
            C_vars = cse_expr.variables

        cube_map: dict[str, int] = {C_vars[i]: e for i, e in enumerate(C_vec) if e > 0}
        if not cube_map:
            return exprs

        for P in exprs:
            if cse_var not in P.var_index:
                P.variables.append(cse_var)
                P.var_index = {v: i for i, v in enumerate(P.variables)}
                for r in P.rows:
                    r.exponents.append(0)

        for P in exprs:
            C_aligned = [cube_map.get(v, 0) for v in P.variables]
            c_idx = P.var_index[cse_var]
            for k, r in enumerate(P.rows):
                if all(r.exponents[i] >= C_aligned[i] for i in range(len(P.variables))):
                    new_exp = r.exponents.copy()
                    for i in range(len(P.variables)):
                        new_exp[i] -= C_aligned[i]
                    new_exp[c_idx] += 1
                    P.rows[k] = MatrixRow(r.sign, new_exp, r.term_id)
        return exprs

    def polynomial_to_matrix(self, poly: np.poly1d, var_name: str = 'x') -> PolynomialMatrix:
        """Convert a 1D numpy polynomial to a PolynomialMatrix using literal var_name."""
        coeffs = poly.coefficients
        deg = len(coeffs) - 1
        variables = [var_name]
        M = PolynomialMatrix(variables)
        for i, c in enumerate(coeffs):
            if c == 0:
                continue
            power = deg - i
            exp: dict[str, int] = {}
            if power > 0:
                exp[var_name] = power
            M.add_term(1 if c > 0 else -1, exp, term_id=i)
        return M

    def optimize_polynomial_univariate(self, coeffs: Sequence[float], var_name: str = 'x', scheme: str = 'paper') -> tuple[list[str], dict[str, float]]:
        """Generate straight-line evaluation code.

        scheme:
          - 'paper' (default): ICCAD-style factoring used in the paper: set z=x*x and
            evaluate even/odd polynomials via Horner in z, combine as y = E + x*O.
            Emits temporaries d1, d2, ... and coefficient symbols S{power}.
          - 'horner' | 'estrin' to force a classic scheme
          - 'auto' to pick the lower-multiplication plan among Horner/Estrin/even-odd
        """
        coeffs = [float(c) for c in coeffs]
        s = scheme.lower()
        lines: list[str]
        if s in ('paper', 'iccad', 'kcm'):
            lines = self._iccad_paper_code(coeffs, var_name)
        elif s == 'horner':
            lines = self._horner_code(coeffs, var_name)
        elif s == 'estrin':
            lines = self._estrin_code(coeffs, var_name)
        else:
            # auto: evaluate Horner, Estrin, and even/odd factoring (Horner in z=x^2)
            h = self._horner_code(coeffs, var_name)
            e = self._estrin_code(coeffs, var_name)
            f = self._even_odd_factored_code(coeffs, var_name)
            def muls(lines: list[str]) -> int:
                return sum(ln.count('*') for ln in lines)
            lines = min([h, e, f], key=muls)

        # Final pass simplification
        lines = self.simplify_body(lines)
        return lines, {}

    def _iccad_paper_code(self, coeffs: Sequence[float], x: str) -> list[str]:
        """Emit ICCAD paper-style factoring with explicit temporaries.

        Preferred shape (matching the paper's sin(x) example when applicable):
          d4 = x*x
          d2 = S5 - S7*d4
          d1 = d2*d4 - S3
          d3 = d1*d4 + S1
          y = x*d3

        In general, we implement P(x) = E(z) + x*O(z) with z=x^2 but for the
        odd-only, alternating-sign case (like sine), we use the exact ordering
        and naming shown above. S{p} names refer to magnitudes |coef(x^p)|.
        """
        n = len(coeffs)
        deg = n - 1

        # Map powers to coefficients (signed)
        pow_to_coef: dict[int, float] = {deg - i: float(coeffs[i]) for i in range(n) if coeffs[i] != 0.0}

        odd_powers = sorted([p for p in pow_to_coef if p % 2 == 1], reverse=True)
        even_powers = sorted([p for p in pow_to_coef if p % 2 == 0], reverse=True)

        # TODO:
        # (I) generalize to any even / odd series
        # (II) identify nested even / odd series

        # Generic ICCAD-style: z = x*x; Horner in z for odd/even parts; combine
        lines: list[str] = []
        lines.append(f"d1 = {x}*{x}")
        next_d = 2

        odd_out: str | None = None
        if odd_powers:
            # Start with highest odd power
            p0 = odd_powers[0]
            lead_sign = '-' if pow_to_coef[p0] < 0 else ''
            lines.append(f"d{next_d} = {lead_sign}S{p0}")
            cur = f"d{next_d}"
            next_d += 1
            for p in odd_powers[1:]:
                # Use sign of actual coefficient when printing +/-
                sign = '+' if pow_to_coef[p] >= 0 else '-'
                lines.append(f"d{next_d} = {cur}*d1 {sign} S{p}")
                cur = f"d{next_d}"
                next_d += 1
            odd_out = cur

        even_out: str | None = None
        if even_powers:
            p0 = even_powers[0]
            lead_sign = '-' if pow_to_coef[p0] < 0 else ''
            lines.append(f"d{next_d} = {lead_sign}S{p0}")
            cur = f"d{next_d}"
            next_d += 1
            for p in even_powers[1:]:
                sign = '+' if pow_to_coef[p] >= 0 else '-'
                lines.append(f"d{next_d} = {cur}*d1 {sign} S{p}")
                cur = f"d{next_d}"
                next_d += 1
            even_out = cur

        # Combine
        if odd_out and even_out:
            lines.append(f"y = {even_out} + {x}*{odd_out}")
        elif odd_out:
            lines.append(f"y = {x}*{odd_out}")
        elif even_out:
            lines.append(f"y = {even_out}")
        else:
            lines.append('y = 0.0')
        return lines

    def _even_odd_factored_code(self, coeffs: Sequence[float], x: str) -> list[str]:
        """P(x) = E(z) + x*O(z) with z = x^2; evaluate E and O via Horner in z.
        Uses original coefficient indices c1..cN mapped by power parity.
        """
        n = len(coeffs)
        deg = n - 1

        # Build descending-power index list for even and odd powers
        even_idx = [i for i in range(n) if (deg - i) % 2 == 0 and coeffs[i] != 0.0]
        odd_idx  = [i for i in range(n) if (deg - i) % 2 == 1 and coeffs[i] != 0.0]

        lines: list[str] = []
        # z = x^2 if needed
        if even_idx or odd_idx:
            lines.append(f"z = {x}*{x}")

        def horner_in_z(idx_list: list[int]) -> str | None:
            if not idx_list:
                return None

            """Each step corresponds to multiplying by z then adding next coefficient
            Maintain descending power in z: idx_list already in ascending i; we need them in order of decreasing z power
            z-power for coeff index i is (deg - i)//2"""
            idx_list_sorted = sorted(idx_list, key=lambda i: (deg - i)//2)

            # Initialize with first (lowest-degree) in z to allow forward Horner build
            init = idx_list_sorted[0]
            var = f"t{init+1}"
            lines.append(f"{var} = c{init+1}")
            for i in idx_list_sorted[1:]:
                lines.append(f"{var} = {var}*z + c{i+1}")
            return var

        ev_var = horner_in_z(even_idx)
        od_var = horner_in_z(odd_idx)

        if ev_var and od_var:
            lines.append(f"y = {ev_var} + {x}*{od_var}")
        elif ev_var:
            lines.append(f"y = {ev_var}")
        elif od_var:
            lines.append(f"y = {x}*{od_var}")
        else:
            lines.append('y = 0.0')
        return lines

    def _horner_code(self, coeffs: Sequence[float], x: str) -> list[str]:
        """Emit Horner-form code using coefficient symbols c1..cN (descending input)."""
        # Descending power order: coeffs[0] for x^n ... coeffs[-1] for x^0
        n = len(coeffs)
        lines: list[str] = []
        start = next((i for i, c in enumerate(coeffs) if c != 0.0), None)
        if start is None:
            return ['y = 0.0']
        lines.append(f"y = c{start+1}")
        for i in range(start + 1, n):
            if coeffs[i] == 0.0:
                lines.append(f"y = y*{x}")
            else:
                lines.append(f"y = y*{x} + c{i+1}")
        return lines

    def _estrin_code(self, coeffs: Sequence[float], x: str) -> list[str]:
        """Emit Estrin expression using c1..cN and precomputed x^k via squaring/multiply."""

        # Build using coefficient variables c{i}. Handle powers via binary decomposition.
        n = len(coeffs)
        asc_indices = list(range(n - 1, -1, -1))  # indices for x^0 .. x^n mapping to original coeffs
        lines: list[str] = [f"x1 = {x}", 'x2 = x1*x1']
        pow_vars = {1: 'x1', 2: 'x2'}

        def pow_var(p: int) -> str:
            if p in pow_vars:
                return pow_vars[p]
            k = 1
            while (k << 1) <= p:
                k <<= 1
            if k not in pow_vars:
                base = pow_var(k >> 1)
                lines.append(f"x{k} = {base}*{base}")
                pow_vars[k] = f"x{k}"
            if p == k:
                return pow_vars[k]
            rem = p - k
            vr = pow_var(rem)
            lines.append(f"x{p} = {pow_vars[k]}*{vr}")
            pow_vars[p] = f"x{p}"
            return pow_vars[p]

        def estrin_block(idx_list: Sequence[int], base_pow: int = 1) -> str:
            m = len(idx_list)
            if m == 0:
                return '0.0'
            if m == 1:
                i0 = idx_list[0]
                return '0.0' if coeffs[i0] == 0.0 else f"c{i0+1}"
            ev = idx_list[0::2]
            od = idx_list[1::2]
            ev_expr = estrin_block(ev, base_pow * 2)
            od_expr = estrin_block(od, base_pow * 2)
            if od_expr == '0.0':
                return ev_expr
            if ev_expr == '0.0':
                return f"{pow_var(base_pow)}*({od_expr})"
            return f"({ev_expr}) + {pow_var(base_pow)}*({od_expr})"

        expr = estrin_block(asc_indices)
        lines.append(f"y = {expr}")
        return lines

    def simplify_body(self, body_lines: list[str]) -> list[str]:
        """Light simplifier: drop only trivial alias lines like 'd2 = c7' or 'd3 = S5'."""
        trivial_pat = re.compile(r'^\s*(d\d+)\s*=\s*(-)?(?:c(\d+)|S(\d+))\s*$')

        simplified: list[str] = []
        removed: list[str] = []
        for ln in body_lines:
            if (match := trivial_pat.match(ln)):
                # tuple -> (variable_to_replace, sign, index)
                removed.append((match.group(1), match.group(2),
                                match.group(3) or match.group(4)))

                continue    # Skip trivial alias
            simplified.append(ln)

        def repl_redundant_subexpr(m: re.Match) -> str:
            # Replace with S{power} notation (defer substitution)
            sign, idx = replacement_map[m.group(0)]
            return f'{sign}S{idx}'

        var_to_replace = list(map(itemgetter(0), removed))
        signs = list(map(itemgetter(1), removed))
        replacement_indices = list(map(itemgetter(2), removed))
        replacement_map = {var: ('' if sign is None else sign, idx) for var, sign, idx
                           in zip(var_to_replace, signs, replacement_indices)}
        to_remove = join_regex(*var_to_replace)

        for i, ln in enumerate(simplified):
            lhs, rhs = re.split(r'\s*=\s*', ln)

            # Apply simplifications to RHS of expression
            rhs = re.sub(to_remove, repl_redundant_subexpr, rhs)

            simplified[i] = f'{lhs} = {rhs}'

        return simplified

    def generate_code(self, body_lines: list[str], n_coefs: int,
                      assign_coefs: bool = False,
                      coef_style: str = 'c_index') -> str:
        """Wrap body_lines into a callable function, defining coefficient aliases.

        coef_style:
          - 'c_index': defines c1..cN in descending-power index order (default)
          - 'S_power': defines S{power} symbols mapped to the coefficient of x^{power}
        """
        deg = n_coefs - 1
        lines = [f"def optimized_polynomial_deg{deg}(x: np.floating, coefs: np.ndarray[np.floating | np.integer]) -> np.floating:"]
        lines.append('coefs = np.abs(coefs)')

        if assign_coefs:
            if coef_style == 's_power':
                for i in range(n_coefs):
                    p = deg - i
                    lines.append(f"S{p} = coefs[{i}]")
            else:
                for i in range(n_coefs):
                    lines.append(f"c{i+1} = coefs[{i}]")

            lines.append('')
        else:
            # Inline replace tokens with coefs[...] using correct 0-based index
            text = '\n'.join(body_lines)

            if coef_style == 's_power':
                def repl_c(m: re.Match) -> str:
                    idx = int(m.group(1)) - 1
                    return f"coefs[{idx}]"

                text = re.sub(r'\bc(\d+)\b', repl_c, text)
            else:
                # Replace S{p} with coefs[deg - p]
                def repl_s(m: re.Match) -> str:
                    p = int(m.group(1))
                    i = deg - p
                    return f"coefs[{i}]"

                text = re.sub(r'\bS(\d+)\b', repl_s, text)

            body_lines = text.split('\n')

        lines.extend(body_lines)
        lines.append('return y')
        return '\n    '.join(lines)


def optimize_polynomial_iccad(poly: np.poly1d, var_name: str = 'x', scheme: str = 'paper') -> tuple[str, dict]:
    """Public API: generate Python code for a univariate polynomial using a scheme."""
    opt = ICCADOptimizer()
    code_lines, _ = opt.optimize_polynomial_univariate(poly.coefficients.tolist(), var_name=var_name, scheme=scheme)
    n = len(poly.coefficients.tolist())
    # coef_style = "s_power" if scheme.lower() in ("paper", "iccad", "kcm") else "c_index"
    code = opt.generate_code(code_lines, n_coefs=n)
    stats = {'degree': len(poly.coefficients) - 1, 'scheme': scheme, 'ops_lines': len(code_lines)}
    return code, stats
