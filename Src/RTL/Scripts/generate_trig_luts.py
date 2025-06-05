"""
Generates a quarter table lookup for various trig functions (sin, cos, tan, tanh)
"""
import argparse as ap
import numpy as np
import sys
import os
from collections.abc import Sequence, Callable

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Allocator.Interpreter.helpers import str2bool, bools2bitstr, eval_arithmetic_str_unsafe
from dataclasses import TrigLuts


def bram(v: int | str) -> int:
    if isinstance(v, str):
        v = int(eval_arithmetic_str_unsafe(v))
    if isinstance(v, int):
        if v <= 4:
            raise ap.ArgumentTypeError('bram must hold at least one double (sizeof(double) = 4)')
        v = np.log2(v) - 2 # Convert to table width, - 2 as units are in bytes
        return int(np.ceil(v))


def main() -> None:
    """# Summary

    Entry-point into lut generator. Run this script with the -h option for help.
    """
    parser = ap.ArgumentParser(description=__doc__.strip())
    parser.add_argument('-bram', type=bram, default=bram(1024))
    parser.add_argument('-qt', type=str2bool, default=True)
    parser.add_argument('-atan-k', type=float, default=0.1)
    parser.add_argument('--sin', action='store_true', default=False)
    parser.add_argument('--cos', action='store_true', default=False)
    parser.add_argument('--tan', action='store_true', default=False)
    parser.add_argument('--asin', action='store_true', default=False)
    parser.add_argument('--acos', action='store_true', default=False)
    parser.add_argument('--atan', action='store_true', default=False)
    args = vars(parser.parse_args())

    TRIG_LUTS = TrigLuts(**{'SIN': 1, 'COS': 1, 'TAN': 1, 'ASIN': 1, 'ACOS': 1, 'ATAN': 1})
    N_TABLE_ENTRIES = 1 << args['bram']
    TRIG = TRIG_LUTS.SIN.value | TRIG_LUTS.COS.value | TRIG_LUTS.TAN.value

    trig_args = {k : v for k, v in args.items() if k not in ('bram', 'qt', 'atan_k')}
    if sum(trig_args.values()) == 0:
        trig_opts = (1 << len(trig_args)) - 1
        # Don't generate both acos & asin & cos & sin lut's unless explicitly specified
        trig_opts ^= (TRIG_LUTS.COS.value | TRIG_LUTS.ACOS.value)
    else:
        trig_opts = bools2bitstr(*trig_args.values())

    if trig_opts & TRIG:
        """
        sin(-x) = -sin(x)
        => x |-> [0, pi]

        The 2nd observation is that:
        sin(x) 0 <= x <= pi / 2 ~looks~ like a flipped version of sin(x) pi/2 <= x <= pi

        To show this:
        sin(x + pi/2) is the part we want to show is horizontally flipped
        d/dx sin(x + pi/2) = d/dx cos(x) = -sin(x)
        sin(x) + (-sin(x)) = 0
        => It is horizontally flipped => x |-> [0, pi/2]
        """
        if args['qt']:
            stop = np.pi / 2
            sz = N_TABLE_ENTRIES >> 2
        else:
            stop = np.pi * 2
            sz = N_TABLE_ENTRIES

        if trig_opts & TRIG_LUTS.TAN.value:
            # TODO: solve for where to stop for tan LUT
            stop -= 1/sz # Stop divide by infinity
            phi2 = np.linspace(0, stop, sz, dtype=np.double)

        phi = np.linspace(0, stop, sz, dtype=np.double)

    if trig_opts & (TRIG_LUTS.ASIN.value | TRIG_LUTS.ACOS.value):
        """
        arcsin(-x) = -arcsin(x)
        => x |-> [0, 1]
        if x > sqrt(2) / 2
        => arcsin(x) = pi/2 - arcsin(sqrt(1 - x^2))
        => x |-> [0, sqrt(2) / 2]
        """
        if args['qt']:
            start = 0
            stop = np.sqrt(2) / 2
            sz = N_TABLE_ENTRIES >> 2
        else:
            start = -1
            stop = 1
            sz = N_TABLE_ENTRIES
        x = np.linspace(start, stop, sz, dtype=np.double)

    if trig_opts & TRIG_LUTS.ATAN.value:
        """
        Firstly, the function is odd atan(-x) = -atan(x)
        => x |-> [0, inf)

        Also atan(x) may be written as 0.5*i*ln(1 - i*x) - 0.5*i*ln(1 + i*x)
        => Indefinite integral of atan(x) from 0 to N for some natural number N is:
        x * arctan(x) - 0.5 * ln(x^2 + 1) + C
        => integral from 0 to N is:
        y = N * arctan(N) - 0.5 * ln(N^2 + 1)

        => y/N = arctan(N) - (0.5 * ln(N^2 + 1)) / N
        => err for y/N = (0.5 * ln(N^2 + 1)) / N

        let (0.5 * ln(N^2 + 1)) / N = k
        where k is the ideal threshold.

        (I don't know if there is a closed form for N,
        so the newton raphson method is used)
        """

        def newton_raphson_N(k: int, tolerance: float = 1e-7, max_iter: int = 100) -> float | None:
            N_current = 8 # This value seems stable
            for _ in range(max_iter):
                # Define f(N) = ln(N^2 + 1) - 2 * N * k
                f_N = np.log(N_current**2 + 1) - 2 * N_current * k

                # Define f'(N) = (2N / (N^2 + 1)) - 2k (zero not possible for real N)
                denominator_f_prime = N_current**2 + 1
                f_prime_N = (2 * N_current / denominator_f_prime) - 2 * k

                if abs(f_prime_N) < tolerance: # Avoid division by a very small number (or zero)
                    break

                # Newton-Raphson iteration
                try:
                    N_next = N_current - f_N / f_prime_N
                except OverflowError | ZeroDivisionError:
                    break

                # Check for convergence
                if abs(N_next - N_current) < tolerance:
                    return N_next

                # Update N for the next iteration
                N_current = N_next

            return

        k = args['atan_k']
        N = newton_raphson_N(k)
        if N is not None:
            err = 0.5 * np.log(N**2 + 1) / N
        err_threshold = 0.1 * k # I.e. 10% of the threshold value
        if k > k + err_threshold or k < k - err_threshold:
            print('---Building atan LUT---'
                  f'\n\tError: couldn\'t find an optimal table size N based on precision threshold {k}'
                  ' Try using a bigger value.'
                  f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
                  )

        print('---Building atan LUT---'
              f'\n\tFound optimal value for N {N}'
              f'\n\tErr W.R.T k (lower is better): {abs(err - k)}'
              )

        atan_tbl_sz = 1 << int(np.ceil(np.log2(N)))
        N = int(np.ceil(N))
        x2 = np.linspace(0, N, atan_tbl_sz)


    if trig_opts & TRIG_LUTS.SIN.value:
        sin_tbl = np.sin(phi)
        assess_lut_accuracy(np.sin, sin_tbl, phi, oversample_factor=8)
    if trig_opts & TRIG_LUTS.COS.value:
        cos_tbl = np.cos(phi)
        assess_lut_accuracy(np.cos, cos_tbl, phi, oversample_factor=8)
    if trig_opts & TRIG_LUTS.TAN.value:
        tan_tbl = np.tan(phi2)
        assess_lut_accuracy(np.tan, tan_tbl, phi, oversample_factor=8)
    if trig_opts & TRIG_LUTS.ASIN.value:
        asin_tbl = np.arcsin(x)
        assess_lut_accuracy(np.arcsin, asin_tbl, x, oversample_factor=8)
    if trig_opts & TRIG_LUTS.ACOS.value:
        acos_tbl = np.arccos(x)
        assess_lut_accuracy(np.arccos, acos_tbl, x, oversample_factor=8)
    if trig_opts & TRIG_LUTS.ATAN.value:
        atan_tbl = np.arctan(x2)
        acc_scores = assess_lut_accuracy(np.arctan, atan_tbl, x2, oversample_factor=8)
        print(f'\tErr W.R.T k {abs(k - np.average(acc_scores))}')


def assess_lut_accuracy(fn: Callable, tbl: Sequence[float], axis: Sequence[float],
                         oversample_factor: int) -> None:
    tbl_arr = np.asarray(tbl, dtype=np.double)
    axis_arr = np.asarray(axis, dtype=np.double)
    l_axis = np.size(axis_arr)
    min_ax_val, max_ax_val = np.min(axis_arr), np.max(axis_arr)

    if l_axis == 0:
        print(f'---Accuracy test results for {fn.__name__}---\n\tAxis is empty. Cannot perform test.')
        return

    if np.size(tbl_arr) != l_axis:
        print(f'---Accuracy test results for {fn.__name__}---\n\tTable size ({np.size(tbl_arr)}) '
              f'does not match axis size ({l_axis}). Cannot perform test')
        return

    fn_eval_points: np.ndarray
    if l_axis == 1:
        fn_eval_points = np.array([axis_arr[0]], dtype=np.double)
    else:
        l_test_axis_orig = oversample_factor * l_axis
        test_axis_orig = np.linspace(min_ax_val, max_ax_val, l_test_axis_orig, dtype=np.double)
        actual_indices_for_tbl = np.arange(l_axis)
        fn_eval_indices = actual_indices_for_tbl * oversample_factor
        fn_eval_indices = np.clip(fn_eval_indices, 0, l_test_axis_orig - 1)
        fn_eval_points = test_axis_orig[fn_eval_indices]

    fn_values_at_eval_points = np.asarray(fn(fn_eval_points), dtype=np.double)

    if fn_values_at_eval_points.shape != tbl_arr.shape:
        print(f'---Accuracy test results for {fn.__name__}---\n'
              f'\tShape mismatch between evaluated function values ({fn_values_at_eval_points.shape}) '
              f'and table values ({tbl_arr.shape}). Cannot compute scores.')
        return

    acc_scores = np.abs(tbl_arr - fn_values_at_eval_points)

    print(f'---Accuracy test results for {fn.__name__}---'
          f'\n\tLUT size in bytes: {np.size(tbl_arr) * 4} ({np.size(tbl_arr) / 250:.3f}kB)'
          f'\n\tAvg. acc score (lower is better): {np.average(acc_scores)}'
          f'\n\tOver-sample factor for fn evaluation grid: x{oversample_factor}'
          f'\n\tMin-acc loss: {np.min(acc_scores)}'
          f'\n\tMax-acc loss: {np.max(acc_scores)}')

    return acc_scores


if __name__ == '__main__':
    main()
