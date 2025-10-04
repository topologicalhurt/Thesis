import numpy as np


def sinc_err(x, N):
    """
    Compute the formula:
    Σ(k=1 to 2N) i^(k-1) * x^(k+1) / (k+1)! - i(π + x) + ln(x) + γ

    Parameters:
    -----------
    x : float or array-like
        The input value(s)
    N : int
        Upper limit is 2N for the sum

    Returns:
    --------
    complex or array of complex
        The result of the formula
    """
    gamma = 0.5772156649015329
    x = np.asarray(x, dtype=float)

    k = np.arange(1, 2*N + 1)
    log_factorials = np.cumsum(np.log(k + 1))
    i_powers = (1j) ** (k - 1)
    log_x_powers = (k + 1) * np.log(x[..., np.newaxis])

    log_terms = log_x_powers - log_factorials
    terms = i_powers * np.exp(log_terms)
    series_sum = np.sum(terms, axis=-1)
    result = series_sum - 1j * (np.pi + x) + np.log(x) + gamma

    return result
