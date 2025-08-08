import numpy as np

from Allocator.Interpreter.dataclass import TABLE_MODE


def reconstruct_sin_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number]:
    half_wave = np.concatenate([qwave, np.flip(qwave)])
    return np.concatenate([half_wave, -half_wave])


def reconstruct_cos_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number]:
        half_wave = np.concatenate([qwave, -np.flip(qwave)])
        return np.concatenate([half_wave, np.flip(half_wave)])


def reconstruct_arcsin_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number] | np.number:
    """
    Reconstruct arcsin(x) over x in [-1, 1] from a quarter-wave LUT f(t)
    storing arcsin(t) for t in [0, 1/√2].

    Identity used (half-angle, mapped to stored domain):
        arcsin(x) = sign(x) * 2 * arcsin( sqrt((1 - sqrt(1 - x^2)) / 2) )
    The inner argument always lies in [0, 1/√2], so only direct LUT access
    is needed (with linear interpolation over the stored domain).
    """
    n_points = qwave.size * 4
    x = np.linspace(-1.0, 1.0, n_points)

    # t(x) = sqrt((1 - sqrt(1 - x^2)) / 2) ∈ [0, 1/sqrt(2)] for all x∈[-1,1]
    one_minus_x2 = 1.0 - np.clip(x * x, 0.0, 1.0)
    inner = np.sqrt(one_minus_x2)
    t = np.sqrt((1.0 - inner) * 0.5)

    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    lut_domain = np.linspace(0.0, inv_sqrt2, qwave.size)
    arcsin_half = np.interp(t, lut_domain, qwave)

    return np.sign(x) * 2.0 * arcsin_half


def reconstruct_arccos_qwave(qwave: np.ndarray[np.number]) -> np.ndarray[np.number] | np.number:
    """
    Reconstruct arccos(x) using the identity:
    arccos(x) = 2 * f(√((1+x)/2))
    where f is the quarter table LUT for arccos over t in [0, 1/√2].

    For t > 1/√2, use the complement identity to map back into the stored domain:
        arccos(t) = π/2 - arccos( sqrt(1 - t^2) )
    """
    n_points = qwave.size * 4
    x = np.linspace(-1.0, 1.0, n_points)

    # t(x) = sqrt((1 + x)/2) ∈ [0, 1]
    t = np.sqrt(np.clip(1.0 + x, 0.0, 2.0) * 0.5)

    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    lut_domain = np.linspace(0.0, inv_sqrt2, qwave.size)

    y_half = np.empty_like(t)
    mask_direct = t <= inv_sqrt2
    mask_compl = ~mask_direct

    y_half[mask_direct] = np.interp(t[mask_direct], lut_domain, qwave)
    if np.any(mask_compl):
        t_comp = np.sqrt(np.maximum(0.0, 1.0 - t[mask_compl]**2))
        y_comp = np.interp(t_comp, lut_domain, qwave)
        y_half[mask_compl] = (np.pi / 2.0) - y_comp

    return 2.0 * y_half


def get_reconstructed_from_lut(table: np.ndarray[np.floating | np.integer],
                               table_mode: TABLE_MODE, signal_name: str) -> np.ndarray[np.floating] | np.float32:
    table_mode = table_mode.value

    if table_mode == 0 or table_mode == 3:
        return table

    if table_mode == 1:
        raise NotImplementedError('No reconstruction method exists for medium mode yet.')

    if table_mode == 2:
        qwave = table

        if qwave.size <= 1:
            return np.float32(0)

        if signal_name == 'sin':
            return reconstruct_sin_qwave(qwave=qwave)

        if signal_name == 'cos':
            return reconstruct_cos_qwave(qwave=qwave)

        if signal_name == 'arcsin':
            return reconstruct_arcsin_qwave(qwave=qwave)

        if signal_name == 'arccos':
            return reconstruct_arccos_qwave(qwave=qwave)

        raise NotImplementedError(f'No reconstruction method exists for {signal_name} yet')
