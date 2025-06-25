import argparse as ap


class ExpectedIntParseException(ap.ArgumentTypeError):
    """Base exception for when an integer is expected in argparse type def"""


class ExpectedPosIntParseException(ap.ArgumentTypeError):
    """Base exception for when a positive integer is expected in argparse type def"""


class ExpectedNegIntParseException(ap.ArgumentTypeError):
    """Base exception for when a negative integer is expected in argparse type def"""


class ExpectedFloatParseException(ap.ArgumentTypeError):
    """Base exception for when a floating point number is expected in argparse type def"""


class ExpectedPosFloatParseException(ap.ArgumentTypeError):
    """Base exception for when a positive floating point number is expected in argparse type def"""


class ExpectedNegFloatParseException(ap.ArgumentTypeError):
    """Base exception for when a negative floating point number is expected in argparse type def"""
