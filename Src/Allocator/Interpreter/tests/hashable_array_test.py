"""
------------------------------------------------------------------------
Filename: 	hashable_array_test.py

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

from Allocator.Interpreter.main.hashable_array import HashableArray


def test_hashable_array_basic_hash_and_eq():
    a1 = HashableArray(np.array([1, 2, 3], dtype=np.int16))
    a2 = HashableArray(np.array([1, 2, 3], dtype=np.int16))
    a3 = HashableArray(np.array([1, 2, 4], dtype=np.int16))

    assert a1 == a2
    assert hash(a1) == hash(a2)
    assert a1 != a3


def test_hashable_array_immutable_copy():
    src = np.array([1.0, 2.0, 3.0])
    ha = HashableArray(src)

    # Mutate source after wrapping; wrapper should be unaffected
    src[0] = 99.0

    hb = HashableArray([1.0, 2.0, 3.0])
    assert ha == hb
    assert hash(ha) == hash(hb)


def test_hashable_array_hash_stable_across_orders():
    # Ensure we hash C-order bytes; two arrays with same content but different strides should hash equal
    a_c = np.ascontiguousarray(np.arange(12).reshape(3, 4))
    a_f = np.asfortranarray(a_c)

    h1 = HashableArray(a_c)
    h2 = HashableArray(a_f)

    assert h1 == h2
    assert hash(h1) == hash(h2)
