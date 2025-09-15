"""
------------------------------------------------------------------------
Filename: 	auto_corr_period_test.py

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

import pytest
import numpy as np

from Allocator.Interpreter.metricities.periodicity import PeriodicityMetrics
from Allocator.Interpreter.main.dataclass import SIGNAL_TYPE


def _mk_sine(n: int, cycles: float, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n, dtype=np.float64)
    return np.sin(2 * np.pi * cycles * t / n + phase)


def _mk_square(n: int, cycles: float) -> np.ndarray:
    t = np.arange(n, dtype=np.float64)
    return np.sign(np.sin(2 * np.pi * cycles * t / n))


@pytest.fixture(scope='module')
def rng():
    return np.random.default_rng(1)


@pytest.fixture(scope='module')
def pm_factory():
    def _make(signal: np.ndarray) -> PeriodicityMetrics:
        return PeriodicityMetrics(signal=signal, signal_type=SIGNAL_TYPE.OTHER, signal_name=None)
    return _make


@pytest.fixture(scope='module')
def n4096():
    return 4096


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_pure_sine_detects_period(pm_factory, n4096, cycles):
    n = n4096
    x = _mk_sine(n, cycles)
    pm = pm_factory(x)
    p = pm.auto_corr_period_test()
    assert p == np.rint(n / cycles)


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_sine_with_dc_offset(pm_factory, n4096, cycles):
    n = n4096
    x = _mk_sine(n, cycles) + 0.75
    pm = pm_factory(x)
    p = pm.auto_corr_period_test()
    assert p == np.rint(n / cycles)


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_sine_with_noise_and_smoothing(pm_factory, rng, n4096, cycles):
    # Target 0.5% threshold of actual period
    sm_threshold = 0.005
    lo_threshold = 0.005

    n = n4096
    x = _mk_sine(n, cycles) + 0.2 * rng.standard_normal(n)
    pm = pm_factory(x)
    p_lo = pm.auto_corr_period_test(prominence=None, smooth_win=1)
    p_sm = pm.auto_corr_period_test(prominence=None, smooth_win=7)

    expected_cycles_sm = n / cycles
    assert (1 - sm_threshold) * expected_cycles_sm <= p_sm <= (1 + sm_threshold) * expected_cycles_sm
    assert (1 - lo_threshold) * expected_cycles_sm <= p_lo <= (1 + lo_threshold) * expected_cycles_sm


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_square_wave_period(pm_factory, n4096, cycles):
    n = n4096
    x = _mk_square(n, cycles)
    pm = pm_factory(x)
    p = pm.auto_corr_period_test()
    assert p == np.rint(n / cycles)


def test_short_signal_returns_zero(pm_factory):
    x = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    pm = pm_factory(x)
    assert pm.auto_corr_period_test() == 0


def test_ramp_returns_zero(pm_factory):
    n = 1024
    x = np.linspace(0.0, 1.0, n, dtype=np.float64)
    pm = pm_factory(x)
    assert pm.auto_corr_period_test() == 0


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_min_period_excludes_true_first_peak(pm_factory, n4096, cycles):
    n = n4096
    true_p = np.rint(n / cycles)
    x = _mk_sine(n, cycles)
    pm = pm_factory(x)
    p = pm.auto_corr_period_test(min_period=true_p + 5)
    assert p >= true_p + 5
    assert p % true_p == 0


# @pytest.mark.parametrize("cycles", [3, 5, 8, 10])
# def test_prominence_too_high_returns_zero(pm_factory, n4096, cycles):
#     n = n4096
#     x = _mk_sine(n, cycles) + 0.15 * np.sin(2 * np.pi * (cycles * 3) * np.arange(n) / n)
#     pm = pm_factory(x)
#     p0 = pm.auto_corr_period_test(prominence=None)
#     ph = pm.auto_corr_period_test(prominence=0.95)
#     assert p0 == np.rint(n / cycles)
#     assert ph == 0


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_invalid_smooth_win_raises(pm_factory, n4096, cycles):
    n = n4096
    x = _mk_sine(n, cycles)
    pm = pm_factory(x)
    with pytest.raises(ValueError):
        pm.auto_corr_period_test(smooth_win=4)


@pytest.mark.parametrize('cycles', [3, 5, 8, 10])
def test_nan_inf_handling(pm_factory, n4096, cycles):
    n = n4096
    x = _mk_sine(n, cycles)
    x[100] = np.nan
    x[500] = np.inf
    pm = pm_factory(x)
    p = pm.auto_corr_period_test()
    assert p == 0


def test_prefer_earliest_vs_dominant(pm_factory, n4096):
    n = n4096
    t = np.arange(n, dtype=np.float64)
    p1 = 64
    p2 = 128
    x = 0.4 * np.sin(2 * np.pi * t / p1) + 1.0 * np.sin(2 * np.pi * t / p2)
    pm = pm_factory(x)
    p_dom = pm.auto_corr_period_test(prefer=0)
    p_earliest = pm.auto_corr_period_test(prefer=1)

    assert p_dom in {p2, p1}
    assert p_earliest in {p1, p2}
    assert p_earliest <= p_dom
