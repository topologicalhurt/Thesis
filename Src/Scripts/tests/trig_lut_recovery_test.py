"""
------------------------------------------------------------------------
Filename: 	trig_lut_recovery_test.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	From the .hex memory for trig functions, attempt to 'reconstruct' the original function and perform
tests based on accuracy of the reconstruction

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

# TODO:
# (1) Fix sin test
# (2) Implement all other tests


import pytest
import numpy as np

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from Allocator.Interpreter.dataclass import BYTEORDER, FLOAT_STR_NPMAP

from Scripts.consts import RTL_TRIG_HEX_DIR
from Scripts.dataclass import TRIGLUTDEFS, TRIGLUTFNDEFS
from Scripts.generate_trig_luts import assess_lut_accuracy
from Scripts.hex_utils import TrigLutManager


class ReconstructFn:
    def __init__(self, domain: Sequence[np.floating],
                 fn: Callable[..., np.floating],
                 dtype: np.floating):
        self.domain = np.asarray(domain, dtype=dtype)
        self.fn = fn
        self._size = self.domain.size

    def quantize(self, x: np.floating) -> int:
        pass

    @property
    def size(self) -> int:
        return self._size


class ReconstructSin(ReconstructFn):
    def __init__(self, domain: Sequence[np.floating], dtype: np.floating):
        super().__init__(domain=domain, fn=np.sin, dtype=dtype)

    def quantize(self, theta: np.floating) -> int:
        return self.domain[round((theta / (np.pi / 2.0)) * (self.size - 1))]

    def reconstruct_high(self, theta: np.floating) -> np.floating:
        theta = theta % (2 * np.pi)
        if 0 <= theta and theta < np.pi/2:
            return self.quantize(theta)
        if np.pi / 2 <= theta and theta < np.pi:
            return self.quantize(np.pi - theta)
        if np.pi <= theta < np.pi * 3/2:
            return -self.quantize(theta - np.pi)
        if np.pi * 3/2 <= theta < 2 * np.pi:
            return -self.quantize(2 * np.pi - theta)


class ReconstructArcSin(ReconstructFn):
    def __init__(self, domain: Sequence[np.floating], dtype: np.floating):
        super().__init__(domain=domain, fn=np.arcsin, dtype=dtype)

    def reconstruct_high(self, x: np.floating) -> np.floating:
        pass


@pytest.fixture
def hex_manager():
    return TrigLutManager(RTL_TRIG_HEX_DIR)


@pytest.fixture
def high_opt_lowp_wout_cos_domains(hex_manager: TrigLutManager):
    # Read in all files with (function_name)_32_high_lowp name
    domains = {m : f'{fn.__name__.lower()}_32_high_lowp.hex'
                for (_, m), fn in zip(TRIGLUTDEFS.__members__.items(), TRIGLUTFNDEFS.values())}
    # Exclude cos, arccos .hex files (which are excluded by default)
    domains = {m : hex_manager.read_lut_from_hex(file_name, FLOAT_STR_NPMAP.FLOAT32.value[1],
                                                 target_order=BYTEORDER.NATIVE)
                for m, file_name in domains.items()
                if not file_name.startswith('cos') and not file_name.startswith('arccos')}
    return domains


@dataclass
class TestDomains:
    sin: Sequence[np.floating]
    cos: Sequence[np.floating] | None
    tan: Sequence[np.floating]
    asin: Sequence[np.floating]
    acos: Sequence[np.floating] | None
    atan: Sequence[np.floating]


@dataclass
class SinusoidLutDomains:
    sin: ReconstructSin
    cos: ReconstructSin | None # TODO: should be ReconstructCos


@dataclass
class ArcSinusoidLutDomains:
    asin: ReconstructArcSin
    acos: ReconstructArcSin | None # TODO: should be ReconstructArcCos


@pytest.fixture
def sinusoids(high_opt_lowp_wout_cos_domains: Mapping):
    domains = high_opt_lowp_wout_cos_domains
    return SinusoidLutDomains(
        sin=ReconstructSin(domain=domains[TRIGLUTDEFS.SIN],
                           dtype=FLOAT_STR_NPMAP.FLOAT32.value[1]),
        cos=None # TODO: implement ReconstructCos
    )


@pytest.fixture
def arc_sinusoids(high_opt_lowp_wout_cos_domains: Mapping):
    domains = high_opt_lowp_wout_cos_domains
    return ArcSinusoidLutDomains(
        asin=ReconstructArcSin(domain=domains[TRIGLUTDEFS.ASIN],
                               dtype=FLOAT_STR_NPMAP.FLOAT32.value[1]),
        acos=None # TODO: implement ReconstructArcCos
    )


@pytest.fixture
def sinusoids_test_axis(sinusoids: SinusoidLutDomains, arc_sinusoids: ArcSinusoidLutDomains):
    return TestDomains(
        sin=np.linspace(0, np.pi * 2, sinusoids.sin.size * 4),
        cos=np.linspace(0, np.pi * 2, sinusoids.sin.size * 4),
        tan=None,
        asin=np.linspace(0, 1, arc_sinusoids.asin.size * 4),
        acos=np.linspace(0, 1, arc_sinusoids.asin.size * 4),
        atan=None
    )


def test_reconstruct_sin_high_32(sinusoids: SinusoidLutDomains, sinusoids_test_axis: TestDomains):
    reconstructed_sin = [sinusoids.sin.reconstruct_high(theta) for theta in sinusoids_test_axis.sin]
    assess_lut_accuracy(np.sin, reconstructed_sin, sinusoids_test_axis.sin,
                        oversample_factor=128,
                        type=FLOAT_STR_NPMAP.FLOAT32.value[1])
    for a1, a2 in zip(reconstructed_sin, sinusoids_test_axis.sin):
        print(f'{a1} |-> {a2}')
    assert True
