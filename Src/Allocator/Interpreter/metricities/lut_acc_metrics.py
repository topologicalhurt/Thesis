"""
------------------------------------------------------------------------
Filename: 	lut_acc_metrics.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the None module
None
LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

import numpy as np

from typing import override

from Allocator.Interpreter.main.dataclass import LUT, LUT_ACC_REPORT, LUT_QUANT_ACC_REPORT, SIGNAL_TYPE
from Allocator.Interpreter.metricities.thd import DistortionMetrics
from Allocator.Interpreter.metricities.periodicity import PeriodicityMetrics
from Allocator.Interpreter.metricities.signal_reconstructor import get_reconstructed_from_lut
from Allocator.Interpreter.main.consts import LOGGER


class LutAccMetrics(DistortionMetrics, PeriodicityMetrics):
    def __init__(self, lut: LUT):
        self.lut = lut

        # Normal float table -> Q format -> Normal float table is potentially entropic process
        self.quantized_table = lut.q_format.get_converted(self.lut.table)
        self.table = lut.q_format.get_float_representation(self.quantized_table)

        try:
            self.full_signal = get_reconstructed_from_lut(table=self.table, table_mode=self.lut.table_mode,
                                                          signal_name=self.lut.fn.__name__)
        except NotImplementedError:
            self.full_signal = self.table

            LOGGER.warning(f'Failed to reconstruct signal from LUT: {self.lut.fn.__name__}. '
                           'Mode is not supported / implemented.')
        finally:
            self.quantized_full_signal = lut.q_format.get_converted(self.full_signal)
            self.full_domain = self.lut.domain_fn()

            signal_type = SIGNAL_TYPE.lut_type_to_signal_type(self.lut.type)
            super().__init__(signal=self.full_signal, signal_type=signal_type, signal_name=self.lut.fn.__name__)

    @override
    def get_report(self,
                   axis: np.ndarray[np.floating],
                   oversample_factor: np.uint,
                   dtype: np.dtype | None = None
                   ) -> LUT_ACC_REPORT:
        quant_acc_report, thd_acc_report = super().get_report(axis=axis, oversample_factor=oversample_factor,
                                                              dtype=dtype)

        acc_report = LUT_ACC_REPORT(quant_acc_report=quant_acc_report,
                                    thd_acc_report=thd_acc_report,
                                    f_name=self.lut.fn.__name__
                                    )

        self.lut.update_acc_report(acc_report)
        return acc_report

    @override
    def get_base_report(self) -> LUT_ACC_REPORT:
        quant_acc_report, thd_acc_report = super().get_base_report()
        acc_report = LUT_ACC_REPORT(f_name=self.lut.fn.__name__,
                              quant_acc_report=quant_acc_report,
                              thd_acc_report=thd_acc_report
                              )

        self.lut.update_acc_report(acc_report)
        return acc_report

    @override
    def assess_quantization_error(self,
                        axis: np.ndarray[np.floating],
                        oversample_factor: np.uint,
                        dtype: np.dtype | None = None) -> LUT_QUANT_ACC_REPORT | None:
        return super().assess_quantization_error(fn=self.lut.fn_ref, axis=axis, oversample_factor=oversample_factor, dtype=dtype, q_format=self.lut.q_format)
