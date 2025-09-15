"""
------------------------------------------------------------------------
Filename: 	periodicity.py

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

import numpy as np

from dataclasses import dataclass
from typing import override

from Allocator.Interpreter.main.dataclass import INTERPOLATION_STRATEGY, SIGNAL_TYPE
from Allocator.Interpreter.metricities.signal_metrics import acf_biased_norm, estimate_min_period_multiple, filter_peaks_abs, find_peaks_with_prominence, refine_local_max, select_peak_index, smooth_ma, parabolic_peak_refine
from Allocator.Interpreter.metricities.signal_statistic import SignalStatistic


class PeriodicityMetrics(SignalStatistic):

    def __init__(self, signal: np.ndarray[np.number], signal_type: SIGNAL_TYPE, signal_name: str | None = None):
        super().__init__(signal=signal, signal_type=signal_type, signal_name=signal_name)

    @override
    @property
    def is_periodic(self):
        _is_periodic = super().is_periodic
        return _is_periodic or self.auto_corr_period_test() > 0 and not _is_periodic

    @override
    def get_report(self) -> dataclass:
        return None

    @override
    def get_base_report(self) -> dataclass:
        return None

    def auto_corr_period_test(self,
        min_period: np.uint | None = None,
        max_period: np.uint | None = None,
        prominence: np.floating | None = None,
        sub_interp_method: INTERPOLATION_STRATEGY = INTERPOLATION_STRATEGY.PARABOLIC,
        prefer: np.uint = 1,
        smooth_win: np.uint = 1) -> np.uint32:
        """Estimate fundamental period (in samples) via autocorrelation with robust handling.

        Params:
            min_period: minimum lag to consider (defaults to 2)
            max_period: maximum lag to consider (defaults to N//2)
            prominence: required peak prominence in normalized ACF [0..1]. If None then the peaks will be automatically detected.
            prefer: Indexed from 1 (for earliest valid peak), a value of i + 1 selects the ith most prominent peak.
            A value of 0 indicates that the most dominant peak should be used. Clips to latest occurring maxima if i > N peaks.
            smooth_win: odd window length for moving-average smoothing (<= 1 disables)

        Returns:
            period_samples (>0) if a significant post-zero-lag peak exists, else 0.

        Defaults:
        - Start search at lo=max(2, N//64) to skip tiny-lag artifacts
        - Prefer earliest valid peak by default (prefer=1)
        - Optional smoothing; odd window only
        """

        x = np.asarray(self.unbiased_signal, dtype=np.float64)
        if not np.all(np.isfinite(x)):
            return np.uint32(0)

        n = x.size
        if n < 4:
            return np.uint32(0)

        # Autocorrelation (one-sided), biased-normalized (no (N-k) envelope)
        r = acf_biased_norm(x)
        if r.size == 0 or not np.isfinite(r[0]) or r[0] <= 0:
            return np.uint32(0)

        lo = max(2, n // 64) if min_period is None else max(int(min_period), 1)
        hi_default = n - 1
        hi = hi_default if max_period is None else min(int(max_period), hi_default)
        if lo >= hi:
            return np.uint32(0)

        # If min_period is provided, estimate base period p0 and return the
        # smallest integer multiple >= min_period aligned to p0.
        if min_period is not None:
            cand = estimate_min_period_multiple(r, n, int(min_period), n // 64, n - 1)
            if cand is not None and lo <= int(cand) <= hi_default:
                return cand

        # Work on a slightly padded window to avoid edge artifacts
        w0 = max(0, lo - 1)
        win = r[w0:hi]
        if win.size == 0:
            return np.uint32(0)

        # Optional smoothing
        win = smooth_ma(win, int(smooth_win))

        # Peak detection with (auto) prominence and min distance
        min_dist = max(1, lo // 2)
        peaks, prominences = find_peaks_with_prominence(
            win,
            float(prominence) if prominence is not None else None,
            min_dist
        )
        if peaks.size == 0 or prominences.size == 0:
            return np.uint32(0)

        # Map peaks to absolute lag and filter out near-boundary artifacts
        peaks, peaks_abs, prominences = filter_peaks_abs(
            peaks, int(w0), int(lo), int(hi), int(smooth_win), prominences
        )
        if peaks.size == 0:
            return np.uint32(0)

        # Select according to preference
        idx = select_peak_index(prominences, int(prefer))
        if idx < 0:
            return np.uint32(0)

        # Absolute-lag peak and sub-sample refinement
        p_abs = int(peaks_abs[idx])
        if sub_interp_method == INTERPOLATION_STRATEGY.LOCAL_REFINE:
            period_f = refine_local_max(r, p_abs, int(lo), int(hi))
        elif sub_interp_method == INTERPOLATION_STRATEGY.PARABOLIC:
            period_f = parabolic_peak_refine(r, p_abs)
        else:
            raise NotImplementedError(f'Sub-interpretation method ({sub_interp_method}) not implemented')

        # Snap to nearest integer sample and clip
        return np.uint32(np.clip(int(np.rint(period_f)), lo, hi - 1))
