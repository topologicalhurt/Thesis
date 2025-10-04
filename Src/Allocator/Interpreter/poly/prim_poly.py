import numpy as np

from dataclasses import dataclass, field

from Allocator.Interpreter.poly.dyadic_poly import DyadicPoly
from Allocator.Interpreter.main.common_utils import trailing_zeros_count


@dataclass(slots=True)
class PrimitiveDyadicPoly:
    dyadic: DyadicPoly
    M: np.uint8 = field(init=False)
    S: tuple[np.int16, np.uint64] = field(init=False)
    gcd: np.uint64 = field(init=False)
    prim_coeffs: np.ndarray[np.integer] = field(init=False)
    monic_prim_coeffs: np.ndarray[np.float64] = field(init=False)
    _cleared_coeffs: np.ndarray[np.integer] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.M = np.uint8(np.max(self.dyadic.m_bits))
        shifts = np.full(self.dyadic.m_bits.shape, self.M, dtype=np.uint8) - self.dyadic.m_bits
        self._cleared_coeffs = np.left_shift(self.dyadic.numerators, shifts)
        self.gcd = np.gcd.reduce(np.abs(self._cleared_coeffs))
        two_addic = np.uint8(trailing_zeros_count(self.gcd) if self.gcd != 0 else 0)
        self.S = (np.int16(two_addic) - np.int16(self.M), self.gcd >> two_addic)
        self.prim_coeffs = (self._cleared_coeffs // self.gcd).astype(self._cleared_coeffs.dtype)
        largest_coeff = self.prim_coeffs[np.nonzero(self.prim_coeffs)[0][-1]]
        self.monic_prim_coeffs = self.prim_coeffs.astype(np.float64) / largest_coeff

    def get_odd_evens(self) -> tuple[np.poly1d, np.poly1d]:
        return np.poly1d(self.prim_coeffs[::2]), np.poly1d(self.prim_coeffs[1::2])

    def __repr__(self) -> str:
        return (f'PrimitiveDyadicPoly(degree={self.dyadic.degree()},'
                f' interval=[{self.dyadic.a},{self.dyadic.b}],'
                f' M={self.M}, (SHIFT={self.S[0]}, SCALE={self.S[1]}),'
                f' prim_coeffs={list(self.prim_coeffs)},'
                f' monic_prim_coeffs={list(self.monic_prim_coeffs)})')


class PrimPolyQ:
    """Q(x) = P_even(x^2) + x * P_odd(x^2) on [a,b]

    Evaluates polynomial using squarer form to minimize DSP usage.
    see: https://warwick.ac.uk/fac/sci/eng/people/suhaib_fahmy/publications/fccm2013-xu.pdf
    """
    def __init__(self, prim_poly: PrimitiveDyadicPoly) -> None:
        self.prim_poly = prim_poly
        self.shift, self.odd = prim_poly.S
        self.P_even, self.P_odd = prim_poly.get_odd_evens()
        self.scale = np.float64(self.odd * 2.0 ** self.shift)

    def squarer_form(self) -> tuple[np.poly1d, np.poly1d, np.int16, np.uint64]:
        return (self.P_even, self.P_odd, self.shift, self.odd)

    def to_quad_form(self, coeffs: np.poly1d, x: np.ndarray) -> np.ndarray:
        u = x * x
        t = np.zeros_like(u, dtype=np.float64)
        for a in reversed(np.asarray(coeffs, dtype=np.float64)):
            t = t * u + a
        return t

    def evaluate(self, t: np.ndarray) -> np.ndarray:
        t = np.asarray(t, dtype=np.float64)
        y = self.to_quad_form(self.P_even, t)
        z = self.to_quad_form(self.P_odd, t)
        return (y + t * z) * self.scale

    def evaluate_on_grid(self, grid_sz: int = 2048) -> tuple[np.ndarray, np.ndarray]:
        t = np.linspace(self.prim_poly.dyadic.a, self.prim_poly.dyadic.b, grid_sz, dtype=np.float64)
        return t, self.evaluate(t)
