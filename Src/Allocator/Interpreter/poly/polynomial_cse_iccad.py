"""
------------------------------------------------------------------------
Filename: 	polynomial_cse_iccad.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Polynomial optimization utilities with a matrix-based representation (ICCAD 2004 compatible)
plus practical univariate evaluators (Horner/Estrin).

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
from __future__ import annotations

import re
import networkx as nx
import numpy as np

from enum import Enum, auto
from functools import cache
from operator import itemgetter
from dataclasses import dataclass
from typing import assert_never
from collections.abc import Sequence, Set

from Allocator.Interpreter.main.extendedenum import ExtendedEnum
from Allocator.Interpreter.main.common_utils import join_regex


# TODO's
# (I): Ensure emitted C code is correct & fully portable to risc-v
# (II): Fix simplification system (use tree / DAG structures instead of string substitutions)
# (III): Implement time dependency graph & use SIMD in emitted code
# (IV): Target conformancy to cython (This is an ideal case for it)


@dataclass(frozen=True, slots=True)
class MatrixRow:
    """A single product term (cube): sign * Π variables[i]^exponents[i]."""
    sign: int
    exponents: list[int]
    term_id: int | None = None

    def copy(self) -> 'MatrixRow':
        return MatrixRow(self.sign, self.exponents.copy(), self.term_id)


class CodeTarget(ExtendedEnum):
    """Code generation targets.

    Members:
    - PYTHON: Emit a Python function using NumPy scalars.
    - C: Emit a static inline C function.
    - SV: Emit SystemVerilog (stub for now).
    """

    PYTHON = 'python'
    C = 'c'
    SV = 'sv'

    @classmethod
    def coerce(cls, target: 'CodeTarget | str') -> 'CodeTarget':
        """Accept Enum or string (case-insensitive) and return a CodeTarget; default PYTHON."""
        if isinstance(target, cls):
            return target
        s = str(target).upper()
        if s in cls:
            return cls.get_member_via_name(s)
        return cls.PYTHON


class EvalScheme(ExtendedEnum):
    """Evaluation schemes for univariate polynomial codegen.

    Members:
    - PAPER: ICCAD-style factoring (default). Uses z = x^2, builds even/odd
        Horner chains in z, and combines as y = E + x*O with S{power} symbols
        for coefficients. Designed to match the paper's form.
    - HORNER: Classic Horner evaluation in x using c1..cN.
    - ESTRIN: Estrin's balanced evaluation using precomputed powers.
    - AUTO: Choose the plan with the fewest multiplications among
        HORNER/ESTRIN/even-odd factoring.
    """

    PAPER = 'paper'
    HORNER = 'horner'
    ESTRIN = 'estrin'
    AUTO = 'auto'

    @classmethod
    def coerce(cls, scheme: 'EvalScheme | str') -> 'EvalScheme':
        """Accept Enum or string (including aliases ICCAD/KCM) and return EvalScheme; default AUTO."""
        if isinstance(scheme, cls):
            return scheme
        s = str(scheme).upper()
        alias = {'ICCAD': 'PAPER', 'KCM': 'PAPER'}
        s = alias.get(s, s)
        if s in cls:
            return cls.get_member_via_name(s)
        return cls.AUTO


class CoefStyle(ExtendedEnum):
    """How coefficients are referenced in generated code.

    Members:
    - C_INDEX: Use c1..cN (descending power order) that map to coefs[0..N-1].
    - S_POWER: Use S{power} symbols (signed), mapped to the coefficient of x^power.
    """

    C_INDEX = 'c_index'
    S_POWER = 's_power'

    @classmethod
    def coerce(cls, style: 'CoefStyle | str') -> 'CoefStyle':
        """Accept Enum or string and return CoefStyle; default C_INDEX."""
        if isinstance(style, cls):
            return style
        s = str(style).upper()
        if s in cls:
            return cls.get_member_via_name(s)
        return cls.C_INDEX


class SIMD(Enum):
    """SIMD targets for optional vectorized emission annotations."""
    NONE = auto()
    AVX = auto()
    AVX2 = auto()
    AVX512 = auto()


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
        self.coefficient_map = {}
        self._simd_gencounter = 0   # Unique counter for SIMD codegen symbols to avoid redeclarations across stages


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

    def optimize_polynomial_univariate(self, coeffs: Sequence[float], var_name: str = 'x', scheme: 'EvalScheme | str' = EvalScheme.PAPER) -> tuple[list[str], dict[str, float]]:
        """Generate straight-line evaluation code.

        scheme:
          - PAPER (default): ICCAD-style factoring used in the paper: set z=x*x and
            evaluate even/odd polynomials via Horner in z, combine as y = E + x*O.
            Emits temporaries d1, d2, ... and coefficient symbols S{power}.
          - HORNER | ESTRIN to force a classic scheme
          - AUTO to pick the lower-multiplication plan among Horner/Estrin/even-odd
        """
        coeffs = [float(c) for c in coeffs]
        s = EvalScheme.coerce(scheme)
        lines: list[str]
        if s is EvalScheme.PAPER:
            lines = self._iccad_paper_code(coeffs, var_name)
        elif s is EvalScheme.HORNER:
            lines = self._horner_code(coeffs, var_name)
        elif s is EvalScheme.ESTRIN:
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

        @cache
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

        @cache
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
        """Light simplifier: drop only trivial alias lines like 'd2 = c7' or 'd3 = -S5'."""
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

    def _convert_lines_to_simd(self, lines: list[str], target: SIMD = SIMD.AVX512) -> list[str]:
        """Annotate per-stage lines with AVX-512 FMAs packed by common operand.

        Looks for lines of form 'lhs = fma(a, b, c)' and groups those sharing the
        same 'b' into packs of up to 8 lanes (double). Emits a single fmadd
        comment per pack, then preserves all original scalar lines and order.
        """
        if target is not SIMD.AVX512:
            raise NotImplementedError('Only AVX512 is implemented')

        assign_pat = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*(.+)$')
        fma_pat = re.compile(r'^fma\(\s*(?P<a>.+?)\s*,\s*(?P<b>.+?)\s*,\s*(?P<c>.+?)\s*\)\s*$')

        # Parse entries and track original indices
        entries: list[tuple[int, str, str, str, str]] = []  # (idx, lhs, a, b, c)
        for idx, ln in enumerate(lines):
            m = assign_pat.match(ln)
            if not m:
                continue
            lhs, rhs = m.group(1), m.group(2).strip()
            fm = fma_pat.match(rhs)
            if fm:
                a = fm.group('a').strip()
                b = fm.group('b').strip()
                c = fm.group('c').strip()
                entries.append((idx, lhs, a, b, c))

        # Group by common b operand
        groups: dict[str, list[tuple[int, str, str, str]]] = {}
        for idx, lhs, a, b, c in entries:
            groups.setdefault(b, []).append((idx, lhs, a, c))

        # Build code to insert at the earliest line index of each group
        inserts_at: dict[int, list[str]] = {}
        drop_indices: set[int] = set()

        def chunk(seq, n):
            for i in range(0, len(seq), n):
                yield seq[i:i + n]

        def pad_eight(values: list[str]) -> list[str]:
            v = list(values)
            while len(v) < 8:
                v.append('0.0')
            return v[:8]

    # Use a global, monotonically-increasing id to ensure unique symbol names across calls
        for common, group in groups.items():
            if len(group) < 2:
                continue  # skip singletons

            # Sort by original order for stable packing and mark to drop
            group_sorted = sorted(group, key=lambda t: t[0])
            first_idx = group_sorted[0][0]
            lines_for_group: list[str] = []

            for ch in chunk(group_sorted, 8):
                ls = [lhs for (idx, lhs, _, _) in ch]
                as_ = pad_eight([a for (_, _, a, _) in ch])
                cs_ = pad_eight([c for (_, _, _, c) in ch])
                lanes = ', '.join(ls)
                lines_for_group.append(f"// avx512 fmadd pack: common={common} -> lanes {lanes}")
                pack_id = self._simd_gencounter
                self._simd_gencounter += 1
                lines_for_group.append(f"__m512d __simd_va{pack_id} = _mm512_setr_pd({', '.join(as_)});")
                lines_for_group.append(f"__m512d __simd_vc{pack_id} = _mm512_setr_pd({', '.join(cs_)});")
                lines_for_group.append(f"__m512d __simd_vx{pack_id} = _mm512_set1_pd({common});")
                lines_for_group.append(f"__m512d __simd_vout{pack_id} = _mm512_fmadd_pd(__simd_va{pack_id}, __simd_vx{pack_id}, __simd_vc{pack_id});")
                lines_for_group.append(f"double __simd_pack{pack_id}[8];")
                lines_for_group.append(f"_mm512_storeu_pd(__simd_pack{pack_id}, __simd_vout{pack_id});")
                for lane, lhs in enumerate(ls):
                    lines_for_group.append(f"{lhs} = __simd_pack{pack_id}[{lane}];")

            inserts_at[first_idx] = lines_for_group
            # Mark all indices in this group to drop (they are replaced)
            for idx, *_ in group:
                drop_indices.add(idx)

        # Emit original lines with inserts placed at calculated positions; drop replaced scalars
        out: list[str] = []
        for idx, ln in enumerate(lines):
            if idx in inserts_at:
                out.extend(inserts_at[idx])
            if idx in drop_indices:
                continue
            out.append(ln)
        return out

    def _parallelize(self, body_lines: list[str]) -> list[str]:
        """Reorder assignments into parallel stages using a dependency DAG.

        - Nodes: assignment LHS variables (dN, y, etc.).
        - Edge dep->lhs if lhs depends on dep on its RHS.
        - Output: non-assignment lines first (unchanged), then staged assignments.
        """

        assign_pat = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*(.+)$')
        id_pat = re.compile(r'\b([A-Za-z_]\w*)\b')

        assignments: list[tuple[str, str]] = []
        non_assign: list[str] = []
        for ln in body_lines:
            m = assign_pat.match(ln)
            if m:
                lhs = m.group(1)
                assignments.append((lhs, ln))
            else:
                non_assign.append(ln)

        if len(assignments) < 2:
            return body_lines

        lhs_vars = [lhs for lhs, _ in assignments]
        lhs_set = set(lhs_vars)

        G = nx.DiGraph()
        G.add_nodes_from(lhs_vars)

        for lhs, ln in assignments:
            m = assign_pat.match(ln)
            rhs = m.group(2) if m else ''
            rhs_ids = set(id_pat.findall(rhs))
            for dep in rhs_ids:
                if dep in lhs_set and dep != lhs:
                    G.add_edge(dep, lhs)

        try:
            topo = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            return body_lines

        try:
            generations = list(nx.algorithms.dag.topological_generations(G))
        except Exception:
            generations = [topo]

        line_by_lhs = {lhs: ln for lhs, ln in assignments}

        new_lines: list[str] = []
        new_lines.extend(non_assign)

        stage_num = 0
        for gen in generations:
            stage = list(gen)
            stage.sort(key=lambda v: lhs_vars.index(v))
            if stage:
                new_lines.append(f"// ---- stage {stage_num} ----")
                stage_lines = [line_by_lhs[v] for v in stage if v in line_by_lhs]
                stage_lines = self._convert_lines_to_simd(stage_lines, target=SIMD.AVX512)
                new_lines.extend(stage_lines)
                stage_num += 1

        return new_lines if new_lines else body_lines

    def _inject_fma(self, body_lines: list[str]) -> list[str]:
        """Rewrite patterns of the form a*b +/- c into fma(a,b,c) for C backends.

        Supported shapes (whitespace-agnostic, one assignment per line):
          lhs = a*b + c
          lhs = a*b - c
          lhs = c + a*b
          lhs = c - a*b
        Lines already containing 'fma(' are left unchanged.
        """
        # Regexes are deliberately simple and local (no semicolons in body_lines).
        pat_ab_c = re.compile(r'^\s*(?P<lhs>[A-Za-z_]\w*)\s*=\s*(?P<a>[^*]+?)\s*\*\s*(?P<b>[^+\-]+?)\s*(?P<op>[+-])\s*(?P<c>.+?)\s*$')
        pat_c_ab = re.compile(r'^\s*(?P<lhs>[A-Za-z_]\w*)\s*=\s*(?P<c>.+?)\s*(?P<op>[+-])\s*(?P<a>[^*]+?)\s*\*\s*(?P<b>.+?)\s*$')

        out: list[str] = []
        for ln in body_lines:
            s = ln.strip()

            # Skip non-assignments or lines already using fma
            if 'fma(' in s or '=' not in s:
                out.append(ln)
                continue

            m = pat_ab_c.match(s)
            if m:
                lhs = m.group('lhs')
                a = m.group('a').strip()
                b = m.group('b').strip()
                op = m.group('op')
                c = m.group('c').strip()
                if op == '+':
                    out.append(f"{lhs} = fma({a}, {b}, {c})")
                else:  # a*b - c
                    out.append(f"{lhs} = fma({a}, {b}, -({c}))")
                continue

            m = pat_c_ab.match(s)
            if m:
                lhs = m.group('lhs')
                c = m.group('c').strip()
                op = m.group('op')
                a = m.group('a').strip()
                b = m.group('b').strip()
                if op == '+':
                    out.append(f"{lhs} = fma({a}, {b}, {c})")
                else:  # c - a*b
                    out.append(f"{lhs} = fma(-({a}), {b}, {c})")
                continue

            out.append(ln)
        return out

    def generate_python_code(self, body_lines: list[str], n_coefs: int,
                             assign_coefs: bool = False,
                             coef_style: CoefStyle | str = CoefStyle.C_INDEX,
                             embed_coefs: Sequence[float] | None = None,
                             coefs_var_name: str = 'coefs') -> str:
        """Emit Python code for the polynomial evaluator."""
        deg = n_coefs - 1
        style = CoefStyle.coerce(coef_style)

        header: list[str] = []
        if embed_coefs is not None:
            ec = [float(c) for c in embed_coefs]
            header.append(f"{coefs_var_name} = np.array([" + ', '.join(f"{v:.17g}" for v in ec) + '], dtype=np.float64)')

        lines = header + [f"def optimized_polynomial_deg{deg}(x: np.floating) -> np.floating:"]

        if assign_coefs:
            src_name = coefs_var_name if embed_coefs is not None else 'coefs'
            if style is CoefStyle.S_POWER:
                for i in range(n_coefs):
                    p = deg - i
                    lines.append(f"S{p} = {src_name}[{i}]")
            elif style is CoefStyle.C_INDEX:
                for i in range(n_coefs):
                    lines.append(f"c{i+1} = {src_name}[{i}]")
            else:
                assert_never(style)

            lines.append('')
        else:
            # Inline replace tokens using embedded array (if present)
            text = '\n'.join(body_lines)
            src_name = coefs_var_name if embed_coefs is not None else 'coefs'
            if style is CoefStyle.C_INDEX:
                def repl_c(m: re.Match) -> str:
                    idx = int(m.group(1)) - 1
                    return f"{src_name}[{idx}]"
                text = re.sub(r'\bc(\d+)\b', repl_c, text)
            elif style is CoefStyle.S_POWER:
                def repl_s(m: re.Match) -> str:
                    p = int(m.group(1))
                    idx = deg - p
                    return f"{src_name}[{idx}]"
                text = re.sub(r'\bS(\d+)\b', repl_s, text)
            else:
                assert_never(style)

            body_lines = text.split('\n')

        lines.extend(body_lines)
        lines.append('return y')
        return '\n    '.join(lines)

    def generate_c_code(self, body_lines: list[str], n_coefs: int,
                         assign_coefs: bool = False,
                         coef_style: CoefStyle | str = CoefStyle.C_INDEX,
                         embed_coefs: Sequence[float] | None = None,
                         inject_fmas: bool = True,
                         parallelize: bool = True) -> str:
        """Emit C code for the polynomial evaluator (static inline function)."""
        deg = n_coefs - 1
        style = CoefStyle.coerce(coef_style)
        c_prelude: list[str] = []

        if embed_coefs is not None:
            ec = [float(c) for c in embed_coefs]
            c_prelude.append(
                '  static const double coefs[' + str(n_coefs) + '] = { ' + ', '.join(f"{v:.17g}" for v in ec) + ' };'
            )

        if assign_coefs:
            if style is CoefStyle.C_INDEX:
                for i in range(n_coefs):
                    c_prelude.append(f"  const double c{i+1} = coefs[{i}];")
            elif style is CoefStyle.S_POWER:  # S_POWER signed
                for i in range(n_coefs):
                    p = deg - i
                    c_prelude.append(f"  const double S{p} = coefs[{i}];")
            else:
                assert_never(style)

            c_body_lines = list(body_lines)
        else:
            # Inline replace tokens directly with coefs[...]
            text = '\n'.join(body_lines)
            if style is CoefStyle.C_INDEX:
                def repl_c(m: re.Match) -> str:
                    idx = int(m.group(1)) - 1
                    return f"coefs[{idx}]"
                text = re.sub(r'\bc(\d+)\b', repl_c, text)
            elif style is CoefStyle.S_POWER:
                def repl_s(m: re.Match) -> str:
                    p = int(m.group(1))
                    idx = deg - p
                    return f"coefs[{idx}]"
                text = re.sub(r'\bS(\d+)\b', repl_s, text)
            else:
                assert_never(style)

            c_body_lines = text.split('\n')

        # Inject FMAs & parallelize where profitable
        if inject_fmas:
            c_body_lines = self._inject_fma(c_body_lines)

        if parallelize:
            c_body_lines = self._parallelize(c_body_lines)

        # Collect temporaries to declare (lhs vars in assignments other than y)
        temps: list[str] = []
        assign_pat_decl = re.compile(r'^\s*([A-Za-z_]\w*)\s*=')
        for ln in c_body_lines:
            m = assign_pat_decl.match(ln)
            if not m:
                continue

            lhs = m.group(1)
            if lhs and lhs != 'y' and lhs not in temps:
                temps.append(lhs)

        fma_used = any('fma(' in ln for ln in c_body_lines)
        avx_used = any('_mm512_' in ln for ln in c_body_lines)

        includes = ['#include <stddef.h>']
        if fma_used:
            includes.append('#include <math.h>')
        if avx_used:
            includes.append('#include <immintrin.h>')
        header = [
            *includes,
            f"static inline double optimized_polynomial_deg{deg}(double x) {{"
        ]
        decls = [f"  double {v};" for v in temps]
        decls.append('  double y;')

        body = [
            f"  {ln};" if (not ln.strip().endswith(';') and not ln.lstrip().startswith('//'))
            else f"  {ln}"
            for ln in c_body_lines
        ]
        footer = ['  return y;', '}']

        return '\n'.join(header + (['\n'.join(c_prelude)] if c_prelude else []) + decls + body + footer)

    def generate_sv_code(self, body_lines: list[str], n_coefs: int,
                         assign_coefs: bool = False,
                         coef_style: CoefStyle | str = CoefStyle.C_INDEX,
                         embed_coefs: Sequence[float] | None = None) -> str:
        """Emit SystemVerilog code (stub)."""
        return ''

    def generate_code(self, body_lines: list[str], n_coefs: int,
                      assign_coefs: bool = False,
                      coef_style: CoefStyle | str = CoefStyle.C_INDEX,
                      target: CodeTarget | str = CodeTarget.PYTHON,
                      embed_coefs: Sequence[float] | None = None,
                      coefs_var_name: str = 'COEFS') -> str:
        """Dispatch to the appropriate code generator based on CodeTarget enum.

        coef_style: see CoefStyle for options and semantics.
        """
        tgt = CodeTarget.coerce(target)
        if tgt is CodeTarget.PYTHON:
            return self.generate_python_code(body_lines, n_coefs, assign_coefs, coef_style, embed_coefs, coefs_var_name,
                                             parallelize=False)

        if tgt is CodeTarget.C:
            return self.generate_c_code(body_lines, n_coefs, assign_coefs, coef_style, embed_coefs,
                                        parallelize=False)

        return self.generate_sv_code(body_lines, n_coefs, assign_coefs, coef_style, embed_coefs,
                                     parallelize=False)


def optimize_polynomial_iccad(poly: np.poly1d, var_name: str = 'x', scheme: 'EvalScheme | str' = EvalScheme.PAPER) -> tuple[str, dict]:
    """Public API: generate code for a univariate polynomial using a scheme.

    Currently emits C by default with embedded coefficients for maximum performance.
    """
    opt = ICCADOptimizer()
    eval_scheme = EvalScheme.coerce(scheme)
    code_lines, _ = opt.optimize_polynomial_univariate(poly.coefficients.tolist(), var_name=var_name, scheme=eval_scheme)
    n = len(poly.coefficients.tolist())
    coef_style = (CoefStyle.S_POWER
                  if eval_scheme is EvalScheme.PAPER
                  else CoefStyle.C_INDEX)
    code = opt.generate_code(code_lines, n_coefs=n, assign_coefs=False, coef_style=coef_style, target=CodeTarget.C, embed_coefs=poly.coefficients.tolist())
    stats = {'degree': len(poly.coefficients) - 1, 'scheme': eval_scheme.value, 'ops_lines': len(code_lines)}
    return code, stats
