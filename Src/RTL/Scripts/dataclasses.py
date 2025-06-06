import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Allocator.Interpreter.dataclasses import BitField, ExtendedEnum


class TRIGLUTS(BitField):
    """# Summary

    Bitfield corresponding to which trig LUT tables to build
    """

    ALLOWED = ('SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN')


class TRIGLUTOPT(ExtendedEnum):
    """# Summary

    Enum corresponding to how aggressively to optimise the LUT
    (there are no real advantages to not using 2 = high mode)

    = 0 (lowest mode - full table / complete period)

    = 1 (medium mode - half table / half period)

    = 2 (high mode - quarter table / quarter period)
    """

    LOW=0
    MED=1
    HIGH=2
