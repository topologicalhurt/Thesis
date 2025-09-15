"""
------------------------------------------------------------------------
Filename: 	thd.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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

import functools
import numpy as np
import scipy as sp

from collections.abc import Callable
from typing import override

from Allocator.Interpreter.main.dataclass import LUT_QUANT_ACC_REPORT, LUT_THD_ACC_REPORT, SIG_WINDOW_TYPE, SIGNAL_TYPE, QFormat
from Allocator.Interpreter.metricities.signal_statistic import SignalStatistic


class DistortionMetrics(SignalStatistic):

    def __init__(self, signal: np.ndarray[np.number], signal_type: SIGNAL_TYPE, signal_name: str | None = None):
        super().__init__(signal=signal, signal_type=signal_type, signal_name=signal_name)

    @staticmethod
    def band_power(spec, center_bin: np.float32, half_width: np.uint32) -> np.float64:
        """Sum power around a fractional bin center over ±half_width bins."""
        c = np.uint32(np.round(center_bin))
        mag = np.abs(spec)
        lo = np.max(0, c - half_width)
        hi = np.min(mag.size - 1, c + half_width)
        return np.float64(np.sum(mag[lo:hi + 1] ** 2))

    @staticmethod
    def _dist_scalar_db(p_signal: np.float64, p_dist: np.float64) -> tuple[np.float64, np.float64]:
        if p_signal <= 0 or p_dist <= 0:
            return np.float64(0.0), np.float64(-np.inf)
        d = np.sqrt(p_dist / p_signal)
        return np.float64(d), np.float64(20.0 * np.log10(max(d, np.finfo(np.float64).tiny)))

    @override
    def get_report(self, *args, **kwargs) -> tuple[LUT_QUANT_ACC_REPORT, LUT_THD_ACC_REPORT]:
        if self.full_signal is None or self.quantized_full_signal is None:
            return DistortionMetrics.get_base_report()

        quant_acc_report = self.assess_quantization_error(*args, **kwargs)
        thd_acc_report = self.select_distortion_metric()
        return quant_acc_report, thd_acc_report

    @override
    @staticmethod
    def get_base_report() -> tuple[LUT_QUANT_ACC_REPORT, LUT_THD_ACC_REPORT]:
        return LUT_QUANT_ACC_REPORT(0, 0, 0, 0, []), LUT_THD_ACC_REPORT(-np.inf, 0.0, 'THD')

    def assess_thd(self, window_type: SIG_WINDOW_TYPE = SIG_WINDOW_TYPE.FLATTOP) -> LUT_THD_ACC_REPORT | None:
        """Assess THD.

        Strategy:
        - Periodic (e.g., sin/cos): use FFT bins at integer harmonics (after DC removal).
        - Non-periodic (e.g., arccos over [-1,1]): THD via DCT-II basis, using the
        ratio of energy in k>=2 cosine terms to the strongest cosine term (k>=1).

        Rationale: FFT-based harmonic analysis assumes periodicity. For finite-length,
        non-periodic functions the FFT spreads energy (leakage) and makes THD meaningless.
        A DCT on the finite interval is the appropriate orthogonal basis.
        """
        x = np.asarray(self.unbiased_signal, dtype=np.float64).copy()
        n = x.size
        if n < 4:
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

        if self.is_periodic:
            # Periodic path: FFT with integer-bin harmonics
            spec = np.fft.rfft(x)
            mag = np.abs(spec)
            if mag.size <= 1:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            k1 = np.argmax(mag[1:]) + 1  # strongest bin after DC
            # Use exact-bin power for periodic signals to avoid band overlap issues
            p_fund = np.float64(mag[k1] ** 2)
            if p_fund <= 0.0:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            max_h = (mag.size - 1) // k1
            if max_h < 2:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            harm_idx = np.arange(2, max_h + 1) * k1
            p_harm = np.float64(np.sum(mag[harm_idx] ** 2)) if harm_idx.size else np.float64(0.0)
        else:
            # Non-periodic: DCT-II. For inverse trig (monotonic) remove low-order trend first.
            x_proc = x
            if self.signal_name in ('asin', 'acos'):
                t = np.linspace(-1.0, 1.0, n, dtype=x.dtype)

                # cubic captures bulk smooth curvature; residual holds higher "ripples"
                coeff = np.polyfit(t, x, 3)
                trend = np.polyval(coeff, t)
                x_proc = x - trend

                if np.allclose(x_proc, 0.0):
                    return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            c = sp.fft.dct(x_proc, type=2, norm='ortho')
            mags = np.abs(c)

            if mags.size <= 2 or not np.any(mags[1:]):
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            k_fund = np.argmax(mags[1:]) + 1
            p_fund = np.float64(mags[k_fund] ** 2)

            if p_fund <= 0:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='THD')

            harm_mask = np.ones_like(mags, dtype=bool)
            harm_mask[0] = False
            harm_mask[k_fund] = False
            p_harm = np.float64(np.sum(mags[harm_mask] ** 2))

        thd, thd_db = self._dist_scalar_db(p_fund, p_harm)
        return LUT_THD_ACC_REPORT(thd_dB=thd_db, thd_scalar=np.float64(thd), test_type='THD')

    def _poly_detrend(self, x: np.ndarray, order: int | None) -> np.ndarray:
        """Polynomial detrend.

        Removes a low-order polynomial (Legendre-like on normalized grid) capturing smooth trend.
        Use to isolate higher-frequency residual before spectral metrics.

        Params:
            x: signal
            order: polynomial degree or None to skip
        Returns:
            residual = x - poly_fit(x)
        """
        if order is None:
            return x

        n = x.size
        t = np.linspace(-1.0, 1.0, n, dtype=x.dtype)
        order = min(order, n-1)
        c = np.polyfit(t, x, order)
        return x - np.polyval(c, t)

    def dct_kcut_distortion(self, k_cut: int, detrend_order: int | None = None) -> LUT_THD_ACC_REPORT | None:
        """K-cut distortion metric.

        Defines modeled content as first k_cut non-DC spectral bins (FFT for periodic, DCT-II for finite non-periodic).
        Distortion = sqrt(energy outside band / energy inside band). Optional polynomial detrend improves focus on ripples for monotonic inverse trig.

        Params:
            k_cut: number of lowest non-DC bins treated as modeled
            detrend_order: polynomial order for non-periodic detrend (None disables)
        Returns:
            LUT_THD_ACC_REPORT with dB and scalar of distortion ratio
        """
        x = np.asarray(self.unbiased_signal, dtype=np.float64)
        n = x.size

        if n < 4 or k_cut < 1:
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='K_CUT_DIST')

        if self.is_periodic:
            spec = np.fft.rfft(x)
            mag = np.abs(spec)

            if mag.size <= k_cut:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='K_CUT_DIST')

            p_total = np.sum(mag[1:]**2)
            p_main = np.sum(mag[1:k_cut+1]**2)
        else:
            xr = self._poly_detrend(x, detrend_order)
            c = sp.fft.dct(xr, type=2, norm='ortho')
            mags = np.abs(c)

            if mags.size <= k_cut:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='K_CUT_DIST')

            p_total = np.sum(mags[1:]**2)
            p_main = np.sum(mags[1:k_cut+1]**2)

        if p_total <= 0 or p_main <= 0:
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='K_CUT_DIST')

        p_harm = p_total - p_main
        d, d_db = self._dist_scalar_db(p_main, p_harm)
        return LUT_THD_ACC_REPORT(thd_dB=d_db, thd_scalar=np.float64(d), test_type='K_CUT_DIST')

    def residual_rms_ratio(self, detrend_order: int = 3) -> np.float64:
        """Residual RMS ratio.

        After polynomial detrend (default cubic) computes RMS(residual)/RMS(original).
        Simple scale-invariant measure of remaining high-order structure; near 0 => almost entirely smooth trend.

        Params:
            detrend_order: polynomial order for removal
        Returns:
            scalar in [0,1] (can exceed slightly with numeric noise)
        """
        x = np.asarray(self.unbiased_signal, dtype=np.float64)

        if x.size < detrend_order+2:
            return np.float64(0.0)

        r = self._poly_detrend(x, detrend_order)
        num = np.sqrt(np.mean(r**2))
        den = np.sqrt(np.mean(x**2))
        return np.float64(num/den) if den>0 else np.float64(0.0)

    def _cheb_detrend(self, x: np.ndarray, n_terms: int) -> tuple[np.ndarray, np.ndarray]:
        """Chebyshev detrend returning residual and coeffs (first n_terms)."""
        n = x.size
        if n < 2 or n_terms < 1:
            return x, np.zeros(1, dtype=x.dtype)
        t = np.linspace(-1.0, 1.0, n, dtype=x.dtype)
        deg = min(n_terms - 1, n - 1)
        coeffs = np.polynomial.chebyshev.chebfit(t, x, deg)
        model = np.polynomial.chebyshev.chebval(t, coeffs)
        return x - model, coeffs

    def cheb_model_distortion(self, n_terms: int = 8) -> LUT_THD_ACC_REPORT | None:
        """Chebyshev model distortion.

        Fits first n_terms Chebyshev polynomials (even-optimized basis for [-1,1]).
        Distortion = sqrt(E_residual / E_model) where model is truncated Chebyshev series.
        Useful for monotonic inverse trig where low-order Chebyshev captures bulk curvature.

        Params:
            n_terms: number of Chebyshev terms in model
        Returns:
            LUT_THD_ACC_REPORT with distortion scalar/dB
        """
        x = np.asarray(self.unbiased_signal, dtype=np.float64)

        if x.size < 4 or n_terms < 1:
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='CHEB_MODEL')

        residual, _ = self._cheb_detrend(x, n_terms)
        model_energy = np.sum((x - residual)**2)

        if model_energy <= 0:
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=np.float64(0.0), test_type='CHEB_MODEL')

        res_energy = np.sum(residual**2)
        d, d_db = self._dist_scalar_db(model_energy, res_energy)
        return LUT_THD_ACC_REPORT(thd_dB=d_db, thd_scalar=np.float64(d), test_type='CHEB_MODEL')

    def residual_rms_report(self, detrend_order: int = 3) -> LUT_THD_ACC_REPORT:
        r = self.residual_rms_ratio(detrend_order)
        _, d_db = self._dist_scalar_db(1.0, r)
        return LUT_THD_ACC_REPORT(thd_dB=d_db, thd_scalar=np.float64(r), test_type='RESIDUAL_RMS')

    def assess_quantization_error(self,
                        fn: Callable[..., np.float64],
                        axis: np.ndarray[np.float64],
                        oversample_factor: np.uint32,
                        q_format: QFormat | None = None,
                        dtype: np.dtype | None = None) -> LUT_QUANT_ACC_REPORT | None:
        """ # Summary

        Assesses the lut table's quantization error against a function, fn.
        It compares the generated LUT against the ideal function values at the
        exact same domain points, using the same floating point precision.
        """
        if self.full_signal.size != axis.size:
            raise ValueError(f'The reconstructed signal of size {self.full_signal.size} didn\'t match the test axis of size {axis.size}')

        if dtype is None:
            dtype = np.float64

        original_axis = np.asarray(axis, dtype=dtype)
        l_axis = np.size(original_axis)

        if l_axis < 2:
            return None

        min_ax_val, max_ax_val = np.min(original_axis), np.max(original_axis)
        l_test_axis = (l_axis - 1) * oversample_factor + 1
        test_axis = np.linspace(min_ax_val, max_ax_val, l_test_axis, dtype=dtype)

        ideal_float_values = fn(test_axis)
        ideal_q_values = q_format.get_converted(ideal_float_values)
        interpolated_lut_q_values = np.interp(test_axis, original_axis, self.quantized_full_signal)
        interpolated_lut_q_values = np.round(interpolated_lut_q_values).astype(self.quantized_full_signal.dtype)

        int_acc_scores = np.abs(interpolated_lut_q_values.astype(np.int64) - ideal_q_values.astype(np.int64))
        float_acc_scores = q_format.get_float_representation(int_acc_scores)
        acc_report = LUT_QUANT_ACC_REPORT(avg_acc=np.average(float_acc_scores), min_acc=np.min(float_acc_scores), max_acc=np.max(float_acc_scores),
                                    std=np.std(float_acc_scores), acc_scores=float_acc_scores)

        return acc_report

    def select_distortion_metric(self, execute: bool = True):
        name = (self.signal_name or '').lower()
        trig = ('sin','cos','tan')
        inv_trig = ('arcsin','arccos','arctan')
        if name in trig:
            fn = self.assess_thd
        elif name in inv_trig:
            fn = functools.partial(self.cheb_model_distortion, n_terms=16)
        else:
            fn = self.assess_thd if self.signal_type == SIGNAL_TYPE.TRIG else functools.partial(self.cheb_model_distortion, n_terms=16)
        return fn() if execute else fn
