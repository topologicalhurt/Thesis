import importlib
import numpy as np

from enum import Enum


class ByteOrder(Enum):
    LITTLE=0
    BIG=1
    NATIVE=2


dataclasses = importlib.import_module('.dataclass', package='Allocator.Interpreter')
BitField = dataclasses.BitField
ExtendedEnum = dataclasses.ExtendedEnum


class TRIGLUTDEFS(ExtendedEnum):
    """# Summary

    Enum storing the supported trig LUTS
    """
    SIN = 0
    COS = 1
    TAN = 2
    ASIN = 3
    ACOS = 4
    ATAN = 5
    _SINUSOIDS = (SIN, COS)
    _ARC_SINUSOIDS = (ASIN, ACOS)


class TRIGLUTFNDEFS(ExtendedEnum):
    """# Summary

    Enum storing the trig names & their corresponding functions
    """
    SIN = np.sin
    COS = np.cos
    TAN = np.tan
    ASIN = np.arcsin
    ACOS = np.arccos
    ATAN = np.arctan


class TRIGLUTS(BitField):
    """# Summary

    Bitfield corresponding to which trig LUT tables to build
    """
    ALLOWED = TRIGLUTDEFS.fields()


class TABLEMODE(ExtendedEnum):
    """# Summary

    Abstract parent of classes defining LUT 'fold' mode
    I.e. a periodic function (E.g. sinusoids)
    OR a function having an entire domain that can be reconstructed from a
    subset of it's domain (E.g. arctan)
    """
    def __str__(self) -> str:
        return f'1/{2**self.value}' if self.value != 1 else '1'


class TRIGFOLD(TABLEMODE):
    """# Summary

    Enum corresponding to how the trig LUT is 'folded' E.G. refer to the basic sin case
    for an example.
    (Using higher modes will, ostensibly, take more effort to recover the data.)

    Note: there are no real advantages to not using 2 = high mode for
    most functions.

    = 0 (lowest mode - full table / complete period)

    = 1 (medium mode - half table / half period)

    = 2 (high mode - quarter table / quarter period)
    """
    LOW = 0
    MED = 1
    HIGH = 2


class TRIGPREC(ExtendedEnum):
    """# Summary

    Enum corresponding to how trig LUT is sized

    = 0 (lowest mode - normal precision)

    = 1 (medium mode - double precision)

    = 2 (high mode - full precision)
    """
    LOWP = 0
    MEDP = 1
    HIGHP = 2
