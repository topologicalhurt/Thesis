import numpy as np


def chebyshev_sin(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    return np.astype(np.polynomial.chebyshev.chebinterpolate(np.sin, deg=deg), dtype)


def chebyshev_cos(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev cosine function is not implemented yet.')


def chebyshev_tan(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev tangent function is not implemented yet.')


def chebyshev_arcsin(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arcsine function is not implemented yet.')


def chebyshev_arccos(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arccosine function is not implemented yet.')


def chebyshev_arctan(deg: np.uint, dtype: np.dtype) -> np.ndarray[np.floating]:
    raise NotImplementedError('Chebyshev arctangent function is not implemented yet.')
