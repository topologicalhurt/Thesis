"""
------------------------------------------------------------------------
Filename: 	signal_metrics.py

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
import scipy as sp

from collections.abc import Callable
from typing import override

from Allocator.Interpreter.dataclass import LUT_QUANT_ACC_REPORT, LUT_THD_ACC_REPORT, SIG_WINDOW_TYPE, SIGNAL_TYPE, QFormat, SignalStatistic


# TODO:
# (1): support more than just sin & cos reconstruction
# (2): make function using autocorr to check for periodicity
#       - if function is known / elementary, then just use conditional check
# (3): support options to remove up to nth harmonic of the fundamental freq. or just the fundamental freq
# (4): refactor potentially reusable signal methods into `signals.py`


class PeriodicityMetrics(SignalStatistic):

    def __init__(self, signal: np.ndarray[np.number], signal_type: SIGNAL_TYPE, signal_name: str | None = None):
        super().__init__(signal=signal, signal_type=signal_type, signal_name=signal_name)

    @override
    @property
    def is_periodic(self):
        _is_periodic = super().is_periodic
        return _is_periodic or self.auto_corr_period_test() > 0 and not _is_periodic

    def auto_corr_period_test(self) -> np.uint:
        """Use normalized autocorrelation to determine periodicity.
        Return the period of the function if it is periodic, with a result of 0 indicating no periodicity.
        """
        sig_norm = np.sum(self.unbiased_signal**2)

        # Per the np.correlate documentation, FFT isn't use to compute the convolution which is inefficient on large arrays
        # sp.signal.correlate DOES do this, however.
        if self.signal.size >= 1e5:
            autocorr = sp.signal.correlate(self._unbiased_signal, self._unbiased_signal, mode='same') / sig_norm # noqa: F841
        else:
            autocorr = np.correlate(self._unbiased_signal, self._unbiased_signal, mode='same') / sig_norm        # noqa: F841

        return 0 # BUG: TEMP


class DistortionMetrics(SignalStatistic):

    def __init__(self, signal: np.ndarray[np.number], signal_type: SIGNAL_TYPE, signal_name: str | None = None):
        super().__init__(signal=signal, signal_type=signal_type, signal_name=signal_name)

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
            return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

        if self.is_periodic:
            # Periodic path: FFT with integer-bin harmonics
            spec = np.fft.rfft(x)
            mag = np.abs(spec)
            if mag.size <= 1:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            k1 = np.argmax(mag[1:]) + 1  # strongest bin after DC
            # Use exact-bin power for periodic signals to avoid band overlap issues
            p_fund = np.float64(mag[k1] ** 2)
            if p_fund <= 0.0:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            max_h = (mag.size - 1) // k1
            if max_h < 2:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            harm_idx = np.arange(2, max_h + 1) * k1
            p_harm = np.float64(np.sum(mag[harm_idx] ** 2)) if harm_idx.size else 0.0
        else:
            """Non-periodic path: DCT-II analysis on finite interval.
            Optional: apply a gentle taper to mitigate endpoint slope (reduces Gibbs).
            Keep it mild to not depress the "fundamental" excessively."""
            w = window_type(n)
            xw = x * w

            # DCT-II via even extension + FFT (normalization cancels in ratio)
            y = np.concatenate([xw, xw[::-1]])
            Y = np.fft.rfft(y)
            N = n
            phase = np.exp(-1j * np.pi * np.arange(N) / (2 * N))
            c = (Y[:N] * phase).real  # DCT-II-like coefficients up to a constant factor

            # Ignore DC (k=0); pick strongest cosine term as "fundamental" for THD baseline
            if N <= 1:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            mags = np.abs(c)
            if mags[1:].size == 0:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            k_fund = np.argmax(mags[1:]) + 1
            p_fund = (mags[k_fund] ** 2)
            if p_fund <= 0.0:
                return LUT_THD_ACC_REPORT(thd_dB=-np.inf, thd_scalar=0.0)

            # Sum all higher-order cosine terms as "harmonics"
            mask = np.ones_like(mags, dtype=bool)
            mask[0] = False         # drop DC
            mask[k_fund] = False    # drop fundamental
            p_harm = np.float64(np.sum(mags[mask] ** 2))

        thd = np.sqrt(p_harm / p_fund) if p_harm > 0.0 else 0.0
        thd_db = 20.0 * np.log10(max(thd, np.finfo(float).tiny)) if thd > 0.0 else -np.inf
        return LUT_THD_ACC_REPORT(thd_dB=thd_db, thd_scalar=np.float64(thd))


    def assess_quantization_error(self,
                        fn: Callable[..., np.floating],
                        axis: np.ndarray[np.floating],
                        oversample_factor: np.uint,
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


def band_power(spec, center_bin: np.floating, half_width: np.uint) -> np.float64:
    """Sum power around a fractional bin center over ±half_width bins."""
    c = np.uint(np.round(center_bin))
    mag = np.abs(spec)
    lo = np.max(0, c - half_width)
    hi = np.min(mag.size - 1, c + half_width)
    return np.float64(np.sum(mag[lo:hi + 1] ** 2))
