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


def parabolic_peak_refine(y: np.ndarray, i: int) -> float:
    """Refine the index of a discrete maximum by parabolic interpolation.

    Given a 1D array y and an index i (assumed near a peak), fit a parabola
    to (i-1, i, i+1) and return the sub-sample peak location in float.

    Returns the input index if neighbors aren't valid for interpolation.
    """
    n = y.size
    if 1 <= i < (n - 1):
        y1 = float(y[i - 1])
        y2 = float(y[i])
        y3 = float(y[i + 1])
        denom = (y1 - 2.0 * y2 + y3)
        if np.isfinite(denom) and abs(denom) > 0.0:
            delta = 0.5 * (y1 - y3) / denom
            delta = float(np.clip(delta, -1.0, 1.0))
            return float(i) + delta
    return float(i)


def acf_biased_norm(x: np.ndarray) -> np.ndarray:
    """Biased ACF normalized to r[0] == 1 for finite, positive variance signals."""
    n = x.size
    r_full = sp.signal.correlate(x, x, mode='full', method='fft')
    r = r_full[n - 1:]
    if not np.isfinite(r[0]) or r[0] <= 0:
        return r
    return r / r[0]


def smooth_ma(arr: np.ndarray, k: int) -> np.ndarray:
    """Centered moving-average smoothing with odd window k; k<3 returns arr."""
    if k >= 3 and (k % 2) == 1:
        w = np.ones(int(k), dtype=np.float64) / float(k)
        return np.convolve(arr, w, mode='same')
    if k >= 3 and (k % 2) != 1:
        raise ValueError('Smoothing window should be odd valued.')
    return arr


def _auto_prominence(win: np.ndarray) -> float | None:
    smax = float(np.max(win))
    smin = float(np.min(win))
    srange = max(smax - smin, 0.0)
    if srange <= 0.0:
        return None
    return 0.1 * srange


def find_peaks_with_prominence(win: np.ndarray, prominence: float | None, min_dist: int) -> tuple[np.ndarray, np.ndarray]:
    if prominence is None:
        pth = _auto_prominence(win)
        if pth is None:
            return np.array([], dtype=int), np.array([], dtype=float)
        peaks, props = sp.signal.find_peaks(win, prominence=pth, distance=max(1, int(min_dist)))
        if peaks.size == 0:
            return peaks, np.array([], dtype=float)
        prominences = props.get('prominences', None)
        if prominences is None or len(prominences) == 0:
            return np.array([], dtype=int), np.array([], dtype=float)
        return peaks, np.asarray(prominences)
    else:
        pth = float(np.clip(prominence, 0.0, 1.0))
        peaks, props = sp.signal.find_peaks(win, prominence=pth, distance=max(1, int(min_dist)))
        if peaks.size == 0:
            return peaks, np.array([], dtype=float)
        prominences = props.get('prominences', None)
        if prominences is None or len(prominences) == 0:
            return np.array([], dtype=int), np.array([], dtype=float)
        return peaks, np.asarray(prominences)


def filter_peaks_abs(peaks: np.ndarray, w0: int, lo: int, hi: int, smooth_win: int, prominences: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    peaks_abs = peaks + int(w0)
    guard = max(2, int(smooth_win) // 2)
    valid_mask = (peaks_abs >= (lo + guard)) & (peaks_abs <= (hi - 1))
    if not np.any(valid_mask):
        return np.array([], dtype=int), np.array([], dtype=int), np.array([], dtype=float)
    return peaks[valid_mask], peaks_abs[valid_mask], prominences[valid_mask]


def select_peak_index(prominences: np.ndarray, prefer: int) -> int:
    if prominences.size == 0:
        return -1
    if prefer == 1:
        return 0
    if prefer == 0:
        return int(np.argmax(prominences))
    order = np.argsort(-prominences)
    rank = min(max(int(prefer - 2), 0), order.size - 1)
    return int(order[rank])


def refine_local_max(r: np.ndarray, p_abs: int, lo: int, hi: int) -> float:
    win_lo = max(lo, p_abs - 2)
    win_hi = min(hi - 1, p_abs + 2)
    if win_hi > win_lo:
        local_idx = int(np.argmax(r[win_lo:win_hi + 1]))
        return float(win_lo + local_idx)
    return float(p_abs)


def estimate_min_period_multiple(r: np.ndarray, n: int, min_period: int, lo_default: int, hi_default: int) -> np.uint32 | None:
    """Estimate base period then return smallest integer multiple >= min_period within [lo, n-1]."""
    lo0 = max(2, lo_default)
    hi0 = max(lo0 + 2, min(hi_default, n // 2))
    win0 = r[lo0:hi0]
    if win0.size < 3:
        return None
    peaks0, _ = sp.signal.find_peaks(win0, distance=max(1, lo0 // 2))
    p0_abs = int(lo0 + int(peaks0[0])) if peaks0.size > 0 else int(lo0 + int(np.argmax(win0)))
    p0_f = parabolic_peak_refine(r, p0_abs)
    p0_int = max(1, int(np.rint(p0_f)))
    mp = int(min_period)
    cand = p0_int if mp <= p0_int else int(np.ceil(mp / p0_int)) * p0_int
    if cand <= (n - 1):
        return np.uint32(cand)
    k_max = (n - 1) // p0_int
    cand2 = k_max * p0_int
    if cand2 >= mp and cand2 >= lo0:
        return np.uint32(cand2)
    return None
