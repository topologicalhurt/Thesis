import itertools
import string
import pytest
import numpy as np

from Allocator.Interpreter.helpers import combined_fast_stable_hash
from Allocator.Interpreter.bitfield import BITFIELD
from Allocator.Interpreter.extendedenum import ExtendedEnum


class TestBitfieldBasic:
    BIT_GROWTH_KWARGS = {k: v for k, v in zip(string.ascii_uppercase, range(38, 64))}

    def test_no_drops_lsb_default(self):
        # LSB-first: positions increase from offset
        E = BITFIELD(offset=0, count=True, msb_first=False, A=0, B=0, C=0)
        # Expect masks 1,2,4
        assert {m.name: m.value for m in E.get_members()} == {'A': 1, 'B': 2, 'C': 4}
        assert E.int_sig == 1 | 2 | 4
        assert E.bit_length == 3

    def test_no_drops_msb_first(self):
        # MSB-first: first member gets highest bit when positions are absolute
        E = BITFIELD(offset=0, count=True, msb_first=True, A=0, B=0, C=0)
        # Positions computed: [0,1,2] -> msb order -> [2,1,0]
        # Masks: 4,2,1
        assert {m.name: m.value for m in E.get_members()} == {'A': 4, 'B': 2, 'C': 1}
        assert E.int_sig == 1 | 2 | 4
        assert E.bit_length == 3

    def test_iterable_offsets(self):
        # Provide absolute base offsets per member
        E = BITFIELD(offset=[3, 1, 0], count=False, msb_first=False, A=0, B=0, C=0)
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

    def test_bitfield_count_off_no_overwrite(self):
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

    def test_bitfield_props(self):
        E = BITFIELD(offset=0, count=True, msb_first=False, A=0, B=0, C=0)
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

    def test_bitfield_overflow_multi_valued_behaviour(self):
        with pytest.raises(OverflowError, match=r'^Python int too large to convert to C long$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=64)

        BITFIELD(offset=0, count=False, msb_first=False, **TestBitfieldBasic.BIT_GROWTH_KWARGS)
        with pytest.raises(OverflowError):
            BITFIELD(offset=1, count=False, msb_first=False, **TestBitfieldBasic.BIT_GROWTH_KWARGS)

    def test_bitfield_with_negative_value_multi_valued_behaviour(self):
        with pytest.raises(ValueError, match=r'^Value for enum member "C" must be non-negative, got -1.$'):
            BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=-1)

    def test_bitfield_growth(self):
        bitfield_with_counteracting_offset = BITFIELD(offset=-38, count=False, msb_first=False,
                                                      **TestBitfieldBasic.BIT_GROWTH_KWARGS)
        bitfield_no_offset = BITFIELD(offset=0, count=False, msb_first=False,
                                      **TestBitfieldBasic.BIT_GROWTH_KWARGS)

        assert int(bitfield_with_counteracting_offset.int_sig).bit_length() == 26
        assert int(bitfield_no_offset.int_sig).bit_length() == 64

    def test_bitfield_enumeration(self):
        # Ensure that iterating over the bitfield returns members in definition order
        E = BITFIELD(offset=0, count=True, msb_first=False, A=0, B=1, C=2)
        E2 = BITFIELD(offset=0, count=True, msb_first=True, A=0, B=1, C=2)
        assert list(E.enumerate_bit_positions()) == [4, 2, 0]
        assert list(E2.enumerate_bit_positions()) == [4, 2, 0]      # msb_first has no effect on bit positions

    def test_bitfield_iter(self):
        E = BITFIELD(offset=0, count=False, msb_first=False, A=0, B=1, C=2)
        expected_values_msb_last = [('A', 1, 2), ('B', 2, 1), ('C', 4, 0)]
        for i, (name, value, bitpos) in enumerate(E):
            assert (name, value, bitpos) == expected_values_msb_last[i]

        E2 = BITFIELD(offset=0, count=False, msb_first=True, A=0, B=1, C=2)
        expected_values_msb_first = [('A', 4, 2), ('B', 2, 1), ('C', 1, 0)]
        for i, (name, value, bitpos) in enumerate(E2):
            assert (name, value, bitpos) == expected_values_msb_first[i]

class TestBitfieldFromEnumMask:
    # Create a dynamic enum class directly; do not subclass an existing Enum
    # RED = 1, GREEN = 2, BLUE = 4
    COLORS = BITFIELD(offset=0, count=True, msb_first=False, RED=0, GREEN=0, BLUE=0)
    COLORS_MSB_FIRST_TRUE = BITFIELD(offset=0, count=True, msb_first=True, RED=0, GREEN=0, BLUE=0)
    COLORS_COUNT_OFF = BITFIELD(offset=0, count=False, msb_first=False, RED=0, GREEN=1, BLUE=2)

    def test_bitfield_from_enum_mask_subset(self):
        E = self.__class__.COLORS
        sub = BITFIELD.bitfield_from_enum_mask(E, ['RED', 'BLUE'], msb_first=False)

        # With offset=0, RED=1, GREEN=2, BLUE=4. Subset keeps mask semantics.
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 1, 'BLUE': 4}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, False)
        assert int(v) == 1  # RED -> 1. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, True)
        assert int(v2) == 5  # RED -> 1, BLUE -> 4. 4 + 1 = 5

    def test_bitfield_from_enum_mask_subset_msb_true(self):
        E = self.__class__.COLORS_MSB_FIRST_TRUE
        sub = BITFIELD.bitfield_from_enum_mask(E, ['RED', 'BLUE'], msb_first=True)

        # With offset=0, RED=4, GREEN=2, BLUE=1. Subset keeps mask semantics.
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 4, 'BLUE': 1}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], True, True, False)
        assert int(v) == 4  # RED -> 4. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], True, True, True)
        assert int(v2) == 5  # RED -> 4, BLUE -> 1. 4 + 1 = 5

    def test_bitfield_from_enum_mask_subset_count_off(self):
        E = self.__class__.COLORS_COUNT_OFF
        sub = BITFIELD.bitfield_from_enum_mask(E, ['RED', 'BLUE'], msb_first=False)

        # Using the values field, rather than count, should yield the same result as test_bitfield_from_enum_mask_subset
        assert {m.name: m.value for m in sub.get_members()} == {'RED': 1, 'BLUE': 4}

        v = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, False)
        assert int(v) == 1  # RED -> 1. Select RED only in bitstr

        v2 = BITFIELD.bitstr_from_enum_mask(E, ['RED', 'BLUE'], False, True, True)
        assert int(v2) == 5  # RED -> 1, BLUE -> 4. 4 + 1 = 5


def test_dynamic_bitfield_no_drop_simple():
    # Create a simple bitfield with three members; ensure none are dropped
    Flags = BITFIELD(FOO=0, BAR=0, BAZ=0)
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


class DummyEnum(ExtendedEnum):
    A = 0
    B = 1
    C = 2


def test_bitstr_from_enum_mask_counts_bits_and_positions():
    # Compute a mask selecting A and C
    mask_val = BITFIELD.bitstr_from_enum_mask(DummyEnum, ['A', 'C'], msb_first=True)
    assert bin(int(mask_val)).count('1') == 2   # Two bits should be set

    # Using the convenience to build a class from the same mask should expose two members
    BF = BITFIELD.bitfield_from_enum_mask(DummyEnum, ['A', 'C'], msb_first=True)

    assert BF.fields() == ['A', 'C'], 'Subset mask should not drop fields'
    vals = BF.values()
    assert all(v > 0 and (v & (v - 1)) == 0 for v in vals)
    assert len(set(vals)) == 2
