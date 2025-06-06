import argparse as ap


class PosIntParseException(ap.ArgumentTypeError):
    """Base exception for when a positive integer is expected in argparse type def"""


class ExpectedIntParseException(ap.ArgumentTypeError):
    """Base exception for when an integer is expected in argparse type def"""
