# import pytest
# import numpy as np

# from Allocator.Interpreter.signal_metrics import PeriodicityMetrics
# from Allocator.Interpreter.dataclass import SIGNAL_TYPE


# def _mk_sine(n: int, cycles: float, phase: float = 0.0) -> np.ndarray:
#     t = np.arange(n, dtype=np.float64)
#     return np.sin(2 * np.pi * cycles * t / n + phase)


# def _mk_square(n: int, cycles: float) -> np.ndarray:
#     t = np.arange(n, dtype=np.float64)
#     return np.sign(np.sin(2 * np.pi * cycles * t / n))


# @pytest.fixture(scope="module")
# def rng():
#     return np.random.default_rng(123)


# @pytest.fixture(scope="module")
# def pm_factory():
#     def _make(signal: np.ndarray) -> PeriodicityMetrics:
#         return PeriodicityMetrics(signal=signal, signal_type=SIGNAL_TYPE.OTHER, signal_name=None)
#     return _make


# @pytest.fixture(scope="module")
# def n4096():
#     return 4096


# @pytest.mark.parametrize("cycles", [3, 5, 8, 13])
# def test_pure_sine_detects_period(pm_factory, n4096, cycles):
#     n = n4096
#     x = _mk_sine(n, cycles)
#     pm = pm_factory(x)
#     p = pm.auto_corr_period_test()
#     assert int(p) == n // cycles


# def test_sine_with_dc_offset(pm_factory, n4096):
#     n = n4096
#     cycles = 5
#     x = _mk_sine(n, cycles) + 0.75
#     pm = pm_factory(x)
#     p = pm.auto_corr_period_test()
#     assert int(p) == n // cycles


# def test_sine_with_noise_and_smoothing(pm_factory, rng, n4096):
#     n = n4096
#     cycles = 7
#     x = _mk_sine(n, cycles) + 0.2 * rng.standard_normal(n)
#     pm = pm_factory(x)
#     p_lo = pm.auto_corr_period_test(prominence=None, smooth_win=1)
#     p_sm = pm.auto_corr_period_test(prominence=None, smooth_win=7)
#     assert int(p_sm) == n // cycles
#     assert int(p_lo) in {0, n // cycles}


# def test_square_wave_period(pm_factory, n4096):
#     n = n4096
#     cycles = 6
#     x = _mk_square(n, cycles)
#     pm = pm_factory(x)
#     p = pm.auto_corr_period_test()
#     assert int(p) == n // cycles


# def test_short_signal_returns_zero(pm_factory):
#     x = np.array([0.0, 1.0, 0.0], dtype=np.float64)
#     pm = pm_factory(x)
#     assert int(pm.auto_corr_period_test()) == 0


# def test_ramp_returns_zero(pm_factory):
#     n = 1024
#     x = np.linspace(0.0, 1.0, n, dtype=np.float64)
#     pm = pm_factory(x)
#     assert int(pm.auto_corr_period_test()) == 0


# def test_min_period_excludes_true_first_peak(pm_factory, n4096):
#     n = n4096
#     cycles = 10
#     true_p = n // cycles
#     x = _mk_sine(n, cycles)
#     pm = pm_factory(x)
#     p = int(pm.auto_corr_period_test(min_period=true_p + 5))
#     assert p >= true_p + 5
#     assert p % true_p == 0


# def test_prominence_too_high_returns_zero(pm_factory, n4096):
#     n = n4096
#     cycles = 9
#     x = _mk_sine(n, cycles) + 0.15 * np.sin(2 * np.pi * (cycles * 3) * np.arange(n) / n)
#     pm = pm_factory(x)
#     p0 = int(pm.auto_corr_period_test(prominence=None))
#     ph = int(pm.auto_corr_period_test(prominence=0.95))
#     assert p0 == n // cycles
#     assert ph == 0


# def test_invalid_smooth_win_raises(pm_factory, n4096):
#     n = n4096
#     cycles = 4
#     x = _mk_sine(n, cycles)
#     pm = pm_factory(x)
#     with pytest.raises(ValueError):
#         pm.auto_corr_period_test(smooth_win=4)


# def test_nan_inf_handling(pm_factory, n4096):
#     n = n4096
#     cycles = 3
#     x = _mk_sine(n, cycles)
#     x[100] = np.nan
#     x[500] = np.inf
#     pm = pm_factory(x)
#     p = pm.auto_corr_period_test()
#     assert int(p) == n // cycles


# def test_prefer_earliest_vs_dominant(pm_factory, n4096):
#     n = n4096
#     t = np.arange(n, dtype=np.float64)
#     p1 = 64
#     p2 = 128
#     x = 0.4 * np.sin(2 * np.pi * t / p1) + 1.0 * np.sin(2 * np.pi * t / p2)
#     pm = pm_factory(x)
#     p_dom = int(pm.auto_corr_period_test(prefer=0))
#     p_earliest = int(pm.auto_corr_period_test(prefer=1))
#     assert p_dom in {p2, p1}
#     assert p_earliest in {p1, p2}
#     assert p_earliest <= p_dom
