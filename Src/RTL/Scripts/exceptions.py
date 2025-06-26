"""
------------------------------------------------------------------------
Filename: 	exceptions.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""


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
