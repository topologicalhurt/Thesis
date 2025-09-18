"""
------------------------------------------------------------------------
Filename: 	bitfield_test.py

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

import itertools
import string
import pytest
import numpy as np

from Allocator.Interpreter.main.common_utils import combined_fast_stable_hash
from Allocator.Interpreter.main.bitfield import BITFIELD
from Allocator.Interpreter.main.extendedenum import ExtendedEnum


@pytest.fixture
def growth_kwargs():
    return {k: v for k, v in zip(string.ascii_uppercase, range(38, 64))}


@pytest.fixture
def flags_lsb():
    # LSB-first: positions increase from offset
    return BITFIELD(offset=0, count=True, msb_first=False, A=0, B=0, C=0)


@pytest.fixture
def flags_msb():
    # MSB-first: first member gets highest bit when positions are absolute
    return BITFIELD(offset=0, count=True, msb_first=True, A=0, B=0, C=0)


@pytest.fixture
def flags_iterable_offsets():
    # Provide absolute base offsets per member
    return BITFIELD(offset=[3, 1, 0], count=False, msb_first=False, A=0, B=0, C=0)


@pytest.fixture
def flags_count_off_increasing_lsb():
    return BITFIELD(offset=0, count=False, msb_first=False, A=0, B=1, C=2)


@pytest.fixture
def flags_count_off_increasing_msb():
    return BITFIELD(offset=0, count=False, msb_first=True, A=0, B=1, C=2)


@pytest.fixture
def colors_lsb():
    # RED = 1, GREEN = 2, BLUE = 4
    return BITFIELD(offset=0, count=True, msb_first=False, RED=0, GREEN=0, BLUE=0)


@pytest.fixture
def colors_msb_true():
    # RED = 4, GREEN = 2, BLUE = 1
    return BITFIELD(offset=0, count=True, msb_first=True, RED=0, GREEN=0, BLUE=0)


@pytest.fixture
def colors_count_off():
    # Explicit absolute positions
    return BITFIELD(offset=0, count=False, msb_first=False, RED=0, GREEN=1, BLUE=2)


class _DummyEnum(ExtendedEnum):
    A = 0
    B = 1
    C = 2


@pytest.fixture
def dummy_enum():
    return _DummyEnum


class _PlainEnum(ExtendedEnum):
    A = 0
    B = 1
    C = 2


@pytest.fixture
def plain_enum():
    return _PlainEnum


@pytest.fixture
def simple_flags_bitfield():
    return BITFIELD(FOO=0, BAR=0, BAZ=0)


class TestBitfieldBasic:
    BIT_GROWTH_KWARGS = {k: v for k, v in zip(string.ascii_uppercase, range(38, 64))}

    def test_no_drops_lsb_default(self, flags_lsb):
        # LSB-first: positions increase from offset
        E = flags_lsb
        # Expect masks 1,2,4
        assert {m.name: m.value for m in E.get_members()} == {'A': 1, 'B': 2, 'C': 4}
        assert E.int_sig == 1 | 2 | 4
        assert E.bit_length == 3

    def test_no_drops_msb_first(self, flags_msb):
        # MSB-first: first member gets highest bit when positions are absolute
        E = flags_msb
        # Positions computed: [0,1,2] -> msb order -> [2,1,0]
        # Masks: 4,2,1
        assert {m.name: m.value for m in E.get_members()} == {'A': 4, 'B': 2, 'C': 1}
        assert E.int_sig == 1 | 2 | 4
        assert E.bit_length == 3

    def test_iterable_offsets(self, flags_iterable_offsets):
        # Provide absolute base offsets per member
        E = flags_iterable_offsets
        # Positions: [3,1,0] => masks: 8,2,1
        assert {m.name: m.value for m in E.get_members()} == {'A': 8, 'B': 2, 'C': 1}
        assert E.int_sig == 8 | 2 | 1

    def test_bools2bitstr_alignment_lsb(self):
        # LSB-first packer: positions [0,1,2]
        val = BITFIELD.bools2bitstr(False, True, True, msb_first=False, offset=0, count=True)
        assert val == (0 << 0) | (1 << 1) | (1 << 2)

    def test_bools2bitstr_alignment_msb(self):
        # MSB-first packer with 3 flags should set bits [2,1,0] for [f0,f1,f2]
        val = BITFIELD.bools2bitstr(True, False, True, msb_first=True, offset=0, count=True)

        # Flags map to positions [2,1,0]: True at 2, False at 1, True at 0 -> 4 + 0 + 1 = 5
        assert val == 5

    def test_bitfield_count_off_no_overwrite(self, colors_count_off):
        E = BITFIELD(offset=0, count=False, msb_first=False, RED=0, GREEN=0, BLUE=0)
        assert list(E) == [('RED', 1, 0)]  # Only RED is present, no GREEN or BLUE
        assert E.RED.value == 1            # The value of RED should be 0 << 1 = 1

    def test_bitfield_out_of_order(self):
        E1 = BITFIELD(offset=0, count=False, msb_first=False, C=1, A=3, B=2, D=4)
        E2 = BITFIELD(offset=0, count=True, msb_first=False, C=1, A=4, B=2, E=0, D=5)

        # E1 = (1 << 1) + (1 << 3) + (1 << 2) + (1 << 4)
        assert E1.int_sig == 2 | 8 | 4 | 16
        # E2 = 1 << (1 + 1) << (4 + 1) + 1 << (2 + 2) + 1 << (0 + 3) + 1 << (5 + 4)
        assert E2.int_sig == 2 | 32 | 16 | 8 | 512

        assert {m.name: m.value for m in E1.get_members()} == {'A': 8, 'B': 4, 'C': 2, 'D': 16}
        assert {m.name: m.value for m in E2.get_members()} == {'A': 32, 'B': 16, 'C': 2, 'D': 512, 'E': 8}

    def test_bitfield_hash(self):
        E = BITFIELD(offset=0, count=False, msb_first=False, A=1, B=2, C=3, D=4)
        E2 = BITFIELD(offset=0, count=False, msb_first=False, A=1, B=2, C=3, D=4)
        E3 = BITFIELD(offset=0, count=False, msb_first=False, A=1, B=2, C=3, D=5)  # Different D
        hsh_args = [('A', 2), ('B', 4), ('C', 8), ('D', 16)]
        data = [(hsh[0].encode('utf-8'), hsh[1].to_bytes(1, signed=False)) for hsh in hsh_args]
        data = itertools.chain.from_iterable(data)

        assert hash(E) == combined_fast_stable_hash(data)
        assert E == E2
        assert E2 != E3
        assert(E.__name__ == E2.__name__)
        assert(E2.__name__ != E3.__name__)

    def test_bitfield_hash_out_of_order(self):
        E1 = BITFIELD(offset=0, count=False, msb_first=False, A=1, B=2, C=3, D=4)
        E2 = BITFIELD(offset=0, count=False, msb_first=False, C=3, A=1, B=2, D=4)

        assert hash(E1) == hash(E2)  # Same content, different order
        assert E1 == E2

    def test_bitfield_props(self, flags_lsb):
        E = flags_lsb
        assert E.n_bits == 3
        assert E.bit_length == 3
        assert E.int_sig == 1 | 2 | 4
        assert E.sig == np.uint64(7)
        assert E.values() == [1, 2, 4]
        assert E.fields() == ['A', 'B', 'C']

    def test_bitfield_overflow_behaviour(self):
        with pytest.raises(OverflowError, match=r'^Python int too large to convert to C long$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=64)

    def test_bitfield_with_negative_value_behaviour(self):
        with pytest.raises(ValueError, match=r'^Value for enum member "A" must be non-negative, got -1.$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=-1)

    def test_bitfield_overflow_multi_valued_behaviour(self, growth_kwargs):
        with pytest.raises(OverflowError, match=r'^Python int too large to convert to C long$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=64)

        BITFIELD(offset=0, count=False, msb_first=False, **growth_kwargs)
        with pytest.raises(OverflowError):
            BITFIELD(offset=1, count=False, msb_first=False, **growth_kwargs)

    def test_bitfield_with_negative_value_multi_valued_behaviour(self):
        with pytest.raises(ValueError, match=r'^Value for enum member "C" must be non-negative, got -1.$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=-1)

    def test_bitfield_growth(self, growth_kwargs):
        bitfield_with_counteracting_offset = BITFIELD(offset=-38, count=False, msb_first=False,
                                                      **growth_kwargs)
        bitfield_no_offset = BITFIELD(offset=0, count=False, msb_first=False,
                                      **growth_kwargs)

        assert int(bitfield_with_counteracting_offset.int_sig).bit_length() == 26
        assert int(bitfield_no_offset.int_sig).bit_length() == 64

    def test_bitfield_enumeration(self):
        # Ensure that iterating over the bitfield returns members in definition order
        E = BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=2)
        E2 = BITFIELD(offset=0, count=True, msb_first=True, A=0, B=1, C=2)
        assert list(E.enumerate_bit_positions()) == [4, 2, 0]
        assert list(E2.enumerate_bit_positions()) == [4, 2, 0]      # msb_first has no effect on bit positions

    def test_bitfield_iter(self, flags_count_off_increasing_lsb, flags_count_off_increasing_msb):
        E = flags_count_off_increasing_lsb
        expected_values_msb_last = [('A', 1, 2), ('B', 2, 1), ('C', 4, 0)]
        for i, (name, value, bitpos) in enumerate(E):
            assert (name, value, bitpos) == expected_values_msb_last[i]

        E2 = flags_count_off_increasing_msb
        expected_values_msb_first = [('A', 4, 2), ('B', 2, 1), ('C', 1, 0)]
        for i, (name, value, bitpos) in enumerate(E2):
            assert (name, value, bitpos) == expected_values_msb_first[i]

class TestBitfieldFromEnumMask:
    def test_bitfield_from_enum_mask_subset(self, colors_lsb):
        E = colors_lsb
        sub = BITFIELD.bitfield_from_enum_mask(e=E, mask=['RED', 'BLUE'], count=False, msb_first=False)

        # With offset=0, RED=1, GREEN=2, BLUE=4. Subset keeps mask semantics.
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 1, 'BLUE': 4}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, False)
        assert int(v) == 1  # RED -> 1. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, True)
        assert int(v2) == 5  # RED -> 1, BLUE -> 4. 4 + 1 = 5

    def test_bitfield_from_enum_mask_subset_msb_true(self, colors_msb_true):
        E = colors_msb_true
        sub = BITFIELD.bitfield_from_enum_mask(E, ['RED', 'BLUE'], msb_first=True)

        # With offset=0, RED=4, GREEN=2, BLUE=1. Subset keeps mask semantics.
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 4, 'BLUE': 1}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], True, True, False)
        assert int(v) == 4  # RED -> 4. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], True, True, True)
        assert int(v2) == 5  # RED -> 4, BLUE -> 1. 4 + 1 = 5

    def test_bitfield_from_enum_mask_subset_count_off(self, colors_count_off):
        E = colors_count_off
        sub = BITFIELD.bitfield_from_enum_mask(E, ['RED', 'BLUE'], msb_first=False)

        # Using the values field, rather than count, should yield the same result as test_bitfield_from_enum_mask_subset
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 1, 'BLUE': 4}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, False)
        assert int(v) == 1  # RED -> 1. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, True)
        assert int(v2) == 5  # RED -> 1, BLUE -> 4. 4 + 1 = 5


def test_dynamic_bitfield_no_drop_simple(simple_flags_bitfield):
    # Create a simple bitfield with three members; ensure none are dropped
    Flags = simple_flags_bitfield
    names = Flags.fields()
    values = Flags.values()

    assert names == ['FOO', 'BAR', 'BAZ'], 'Members should preserve definition order and all be present'
    assert len(values) == 3 and len(set(values)) == 3, 'Each member must have a unique value'

    # Check each is a single-bit mask
    assert all(v > 0 and (v & (v - 1)) == 0 for v in values)

    # Signature is the OR of all member masks
    sig = 0
    for v in values:
        sig |= v
    assert sig == Flags.sig
    assert Flags.n_bits == 3


def test_bitstr_from_enum_mask_counts_bits_and_positions(dummy_enum):
    # Compute a mask selecting A and C
    mask_val = BITFIELD.bitstr_from_enum_mask(dummy_enum, ['A', 'C'], msb_first=True)
    print(bin(mask_val))
    assert bin(int(mask_val)).count('1') == 2   # Two bits should be set

    # Using the convenience to build a class from the same mask should expose two members
    BF = BITFIELD.bitfield_from_enum_mask(dummy_enum, ['A', 'C'], msb_first=True)

    assert BF.fields() == ['A', 'C'], 'Subset mask should not drop fields'
    vals = BF.values()
    assert all(v > 0 and (v & (v - 1)) == 0 for v in vals)
    assert len(set(vals)) == 2

def test_bitstr_from_enum_mask_keyword_first_and_defaults():
    # Base BITFIELD with mask values: RED=1, GREEN=2, BLUE=4
    COLORS = BITFIELD(offset=0, count=True, msb_first=False, RED=0, GREEN=0, BLUE=0)

    # Keyword-first, no flags provided -> defaults to selecting all of mask subset
    v_all = BITFIELD.bitstr_from_enum_mask(e=COLORS, mask=['RED', 'BLUE'], msb_first=False)
    assert int(v_all) == 1 | 4

    # Keyword-first with star-flags selects only BLUE
    v_blue_only = BITFIELD.bitstr_from_enum_mask(False, True, e=COLORS, mask=['RED', 'BLUE'], msb_first=False)
    assert int(v_blue_only) == 4

    # Positional-first with explicit flags selects only RED
    v_red_only = BITFIELD.bitstr_from_enum_mask(COLORS, ['RED', 'BLUE'], False, True, False)
    assert int(v_red_only) == 1


def test_bitfield_from_enum_mask_preserves_masks_regardless_of_msb_first_toggle():
    # Original msb_first False
    COLORS = BITFIELD(offset=0, count=True, msb_first=False, RED=0, GREEN=0, BLUE=0)
    sub = BITFIELD.bitfield_from_enum_mask(COLORS, ['GREEN', 'BLUE'], msb_first=True)
    assert {m.name: m.value for m in sub.get_members()} == {'GREEN': 2, 'BLUE': 4}


def test_bitfield_from_enum_mask_with_plain_enum_produces_expected_masks(plain_enum):
    # Plain positional enum -> bitfield masks are 1<<pos
    BF = BITFIELD.bitfield_from_enum_mask(plain_enum, ['A', 'C'], msb_first=True)
    assert {m.name: m.value for m in BF.get_members()} == {'A': 1 << 0, 'C': 1 << 2}


def test_bitstr_from_enum_mask_with_plain_enum_exact_value_and_defaults(plain_enum):
    # Selecting A and C from positional enum yields 1<<0 | 1<<2; defaults select all when flags omitted
    v = BITFIELD.bitstr_from_enum_mask(plain_enum, ['A', 'C'], msb_first=True)
    assert int(v) == (1 << 0) | (1 << 2)

    # Explicit flags: select only C
    v2 = BITFIELD.bitstr_from_enum_mask(plain_enum, ['A', 'C'], True, False, True)
    assert int(v2) == (1 << 2)


def test_bools2bitstr_iterable_offset_preserved_under_msb_first_when_count_false():
    # Iterable absolute positions should not be reordered by msb_first when count=False
    positions = [3, 1, 0]
    # True, True, True at positions -> 8 | 2 | 1
    v = BITFIELD.bools2bitstr(True, True, True, msb_first=True, offset=positions, count=False)
    assert int(v) == (1 << 3) | (1 << 1) | (1 << 0)
