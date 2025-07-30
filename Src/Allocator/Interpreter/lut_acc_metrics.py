import numpy as np

from collections.abc import Callable

from Allocator.Interpreter.dataclass import LUT, LUT_THD_ACC_REPORT, LUT_QUANT_ACC_REPORT, LUT_TYPE, SIG_WINDOW_TYPE, QFormat
from Allocator.Interpreter.helpers import find_nearest

from Scripts.dataclass import TABLEMODE


# TODO:
# (1): support more than just sin & cos reconstruction
# (2): make function using autocorr to check for periodicity
#       - if function is known / elementary, then just use conditional check
# (3): support options to remove up to nth harmonic of the fundamental freq. or just the fundamental freq
# (4): refactor potentially reusable signal methods into `signals.py`


class LutAccMetrics:
    def __init__(self, lut: LUT):
        self.lut = lut
        self.quantized_table = lut.q_format.get_converted(self.lut.table)

        # BUG: Tmp fix. until all reconstructed signals impl.
        try:
            self.full_signal = self.get_reconstructed_from_lut(fn=self.lut.fn, table_mode=self.lut.table_mode)
        except NotImplementedError:
            self.full_signal = self.lut.table

        self.is_trig = self.lut.type == LUT_TYPE.TRIG
        self.is_not_periodic = self.lut.fn.__name__ in ('arcsin', 'arccos', 'arctan', 'sinc') if self.is_trig else False

    def assess_lut_quantization_error(self,
                        fn: Callable[..., np.floating],
                        axis: np.ndarray[np.floating],
                        oversample_factor: np.uint,
                        q_format: QFormat | None = None,
                        dtype: np.dtype | None = None) -> LUT_QUANT_ACC_REPORT | None:
        """ # Summary

        Assesses the lut table's quantization error against a function, fn.
        It compares the generated LUT against the ideal function values at the
        exact same domain points, using the same floating point precision.
        """
        if dtype is None:
            dtype = np.float64

        original_axis = np.asarray(axis, dtype=dtype)
        l_axis = np.size(original_axis)

        if l_axis < 2:
            return None

        min_ax_val, max_ax_val = np.min(original_axis), np.max(original_axis)
        l_test_axis = (l_axis - 1) * oversample_factor + 1
        test_axis = np.linspace(min_ax_val, max_ax_val, l_test_axis, dtype=dtype)

        ideal_float_values = fn(test_axis)
        ideal_q_values = q_format.get_converted(ideal_float_values)
        interpolated_lut_q_values = np.interp(test_axis, original_axis, self.quantized_table)
        interpolated_lut_q_values = np.round(interpolated_lut_q_values).astype(self.quantized_table.dtype)

        int_acc_scores = np.abs(interpolated_lut_q_values.astype(np.int64) - ideal_q_values.astype(np.int64))
        float_acc_scores = q_format.get_float_representation(int_acc_scores)
        acc_report = LUT_QUANT_ACC_REPORT(avg_acc=np.average(float_acc_scores), min_acc=np.min(float_acc_scores), max_acc=np.max(float_acc_scores),
                                    std=np.std(float_acc_scores), acc_scores=float_acc_scores)

        return acc_report

    def get_reconstructed_from_lut(self, fn: Callable[..., np.ndarray[np.floating]],
                                   table_mode: TABLEMODE) -> np.ndarray[np.floating] | np.float32:
        table = self.lut.table
        table_mode = table_mode.value

        if table_mode == 0 or table_mode == 3:
            return table

        if table_mode == 1:
            raise NotImplementedError('No reconstruction method exists for medium mode yet.')

        if table_mode == 2:
            q_wave = table

            if q_wave.size < 2:
                return np.float32(0)

            if fn.__name__ == 'sin':
                half_wave = np.concatenate([q_wave, np.flip(q_wave[:-1])])
                return np.concatenate([half_wave, -half_wave[1:]])

            if fn.__name__ == 'cos':
                half_wave = np.concatenate([q_wave, -np.flip(q_wave[1:])])
                return np.concatenate([half_wave, -half_wave[1:]])

            if fn.__name__ == 'arcsin':
                # I.e. pretend we don't need to approximate order of taylor series
                upper_domain = np.linspace(self.lut.domain.max(), 1, num=q_wave.size)[1:]
                upper_first_quad_indices = np.sqrt(1-upper_domain**2)
                upper_first_quad = np.pi/2 - find_nearest(q_wave, upper_first_quad_indices)
                lower_third_quad = -np.flip(upper_first_quad)
                upper_third_quad = -np.flip(q_wave)
                first_quad = np.concatenate([q_wave, upper_first_quad])
                third_quad = np.concatenate([lower_third_quad, upper_third_quad])
                return np.concatenate([third_quad, first_quad])

            raise NotImplementedError(f'No reconstruction method exists for {fn.__name__} yet')

    def assess_lut_thd(self, window_type: SIG_WINDOW_TYPE = SIG_WINDOW_TYPE.KAISER) -> LUT_THD_ACC_REPORT:
        signal = self.full_signal
        if self.is_not_periodic:
            window = window_type(signal.size)
            signal = self.full_signal * window

        fft = np.fft.rfft(signal)
        mag = np.abs(fft)

        if mag.size < 2:
            return 0.0

        # Find the fundamental frequency (strongest component after DC)
        fundamental_idx = np.argmax(mag[1:]) + 1
        fundamental_mag_sq = mag[fundamental_idx]**2
        if fundamental_mag_sq == 0:
            return 0.0

        # Find the RMS over harmonics of the fundamental frequency
        max_harmonic = (mag.size - 1) // fundamental_idx
        harmonic_indices = np.arange(2, max_harmonic + 1) * fundamental_idx
        sum_of_harmonics_sq = np.sum(mag[harmonic_indices]**2)

        # THD is the ratio of the RMS of the harmonics to the RMS of the fundamental
        thd = np.sqrt(sum_of_harmonics_sq / fundamental_mag_sq)
        return LUT_THD_ACC_REPORT(thd_dB=20*np.log10(thd), thd_scalar=thd)
