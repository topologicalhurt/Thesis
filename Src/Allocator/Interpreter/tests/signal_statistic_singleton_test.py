"""
------------------------------------------------------------------------
Filename: 	signal_statistic_singleton_test.py

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
import pytest

from typing import override

from Allocator.Interpreter.metricities.signal_statistic import SignalStatistic
from Allocator.Interpreter.main.dataclass import SIGNAL_TYPE
from Allocator.Interpreter.main.hashable_array import HashableArray


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
