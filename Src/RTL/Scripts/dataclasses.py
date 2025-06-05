import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Allocator.Interpreter.dataclasses import BitField


class TrigLuts(BitField):
    """# Summary

    Bitfield corresponding to which trig LUT tables to build

    ## Args:
        BitField (_type_): _description_
    """

    ALLOWED = ('SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN')
