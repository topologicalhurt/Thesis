import numpy as np

from collections.abc import Callable
from typing import override

from Allocator.Interpreter.dataclass import LUT, LUT_QUANT_ACC_REPORT, SIGNAL_TYPE
from Allocator.Interpreter.signal_metrics import DistortionMetrics, PeriodicityMetrics
from Allocator.Interpreter.signal_reconstructor import get_reconstructed_from_lut


class LutAccMetrics(DistortionMetrics, PeriodicityMetrics):
    def __init__(self, lut: LUT):
        self.lut = lut

        # Normal float table -> Q format -> Normal float table is potentially entropic process
        self.quantized_table = lut.q_format.get_converted(self.lut.table)
        self.table = lut.q_format.get_float_representation(self.quantized_table)

        self.full_signal = get_reconstructed_from_lut(table=self.table, table_mode=self.lut.table_mode, signal_name=self.lut.fn.__name__)

        self.full_domain = self.lut.domain_fn()
        self.quantized_full_signal = lut.q_format.get_converted(self.full_signal)

        signal_type = SIGNAL_TYPE.lut_type_to_signal_type(self.lut.type)
        super().__init__(signal=self.full_signal, signal_type=signal_type, signal_name=self.lut.fn.__name__)

    @override
    def assess_quantization_error(self,
                        fn: Callable[..., np.floating],
                        axis: np.ndarray[np.floating],
                        oversample_factor: np.uint,
                        dtype: np.dtype | None = None) -> LUT_QUANT_ACC_REPORT | None:
        return super().assess_quantization_error(fn=fn, axis=axis, oversample_factor=oversample_factor, dtype=dtype, q_format=self.lut.q_format)
