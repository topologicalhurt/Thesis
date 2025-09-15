"""
------------------------------------------------------------------------
Filename: 	singleton_test.py

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

from abc import ABC

import pytest

from Allocator.Interpreter.main.singleton import SingletonSubclassBase


@pytest.fixture
def not_frozen_cls():
    class A(ABC, SingletonSubclassBase, frozen=False):
        _init_calls = 0

        def __init__(self, x):
            type(self)._init_calls += 1
            self.x = x

    return A


@pytest.fixture
def frozen_cls():
    class B(ABC, SingletonSubclassBase, frozen=True):
        _init_calls = 0

        def __init__(self, x):
            type(self)._init_calls += 1
            self.x = x

    return B


def test_subclass_singleton_refresh_when_not_frozen(not_frozen_cls):
    A = not_frozen_cls
    a1 = A(1)
    a2 = A(2)

    assert a1 is a2, 'Should return the same instance for subclass-level singleton'
    assert a1.x == 2 and a2.x == 2, 'When not frozen, __init__ should refresh state on subsequent instantiation'
    assert A._init_calls == 2, '__init__ should be called again when not frozen'


@pytest.mark.filterwarnings('ignore::UserWarning')
def test_subclass_singleton_frozen_no_refresh(frozen_cls):
    B = frozen_cls
    b1 = B(10)
    b2 = B(99)

    assert b1 is b2, 'Should return the same instance for subclass-level singleton'
    assert b1.x == 10 and b2.x == 10, 'When frozen, __init__ should NOT refresh state on subsequent instantiation'
    assert B._init_calls == 1, '__init__ should only be called once when frozen'
