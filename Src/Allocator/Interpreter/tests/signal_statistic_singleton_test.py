import numpy as np
import pytest

from typing import override

from Allocator.Interpreter.signal_statistic import SignalStatistic
from Allocator.Interpreter.dataclass import SIGNAL_TYPE
from Allocator.Interpreter.hashable_array import HashableArray


@pytest.fixture
def frozen_signal_stat_cls():
    class _DummyFrozenStat(SignalStatistic, frozen=True):

        @override
        def get_report(self):
            return self.signal_metric

        @override
        def get_base_report(self):
            return self.signal_metric

    return _DummyFrozenStat


@pytest.fixture
def not_frozen_signal_stat_cls():
    class _DummyNotFrozenStat(SignalStatistic, frozen=False):

        @override
        def get_report(self):
            return self.signal_metric

        @override
        def get_base_report(self):
            return self.signal_metric

    return _DummyNotFrozenStat


@pytest.fixture
def default_signal_stat_cls():
    class _DummyDefaultStat(SignalStatistic):

        @override
        def get_report(self):
            return self.signal_metric

        @override
        def get_base_report(self):
            return self.signal_metric

    return _DummyDefaultStat


@pytest.mark.filterwarnings('ignore::UserWarning')
def test_signal_statistic_frozen_keeps_first_state(frozen_signal_stat_cls):
    C = frozen_signal_stat_cls
    s1 = C(HashableArray(np.array([1.0, 2.0])), SIGNAL_TYPE.TRIG, 'sin')
    s2 = C(HashableArray(np.array([9.0, 8.0])), SIGNAL_TYPE.TRIG, 'cos')

    assert s1 is s2
    # Because frozen=True, second init must NOT refresh name
    assert s1.signal_name == 'sin'
    assert s2.signal_name == 'sin'


def test_signal_statistic_not_frozen_refreshes_state(not_frozen_signal_stat_cls):
    C = not_frozen_signal_stat_cls
    s1 = C(HashableArray(np.array([1.0, 2.0])), SIGNAL_TYPE.TRIG, 'sin')
    s2 = C(HashableArray(np.array([9.0, 8.0])), SIGNAL_TYPE.TRIG, 'cos')

    assert s1 is s2
    # Because frozen=False, second init must refresh name
    assert s1.signal_name == 'cos'
    assert s2.signal_name == 'cos'


def test_signal_statistic_default_behaves_not_frozen(default_signal_stat_cls):
    C = default_signal_stat_cls

    # Default base class should not be frozen
    assert getattr(C, '__singleton_frozen__', False) is False
    s1 = C(HashableArray(np.array([1.0, 2.0])), SIGNAL_TYPE.TRIG, 'sin')
    s2 = C(HashableArray(np.array([9.0, 8.0])), SIGNAL_TYPE.TRIG, 'cos')

    assert s1 is s2
    # Default base is frozen=False, so second init must refresh name
    assert s1.signal_name == 'cos'
    assert s2.signal_name == 'cos'
