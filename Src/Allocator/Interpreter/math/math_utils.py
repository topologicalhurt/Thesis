import numpy as np


def ceil_div(a: int, b: int) -> int:
    return -(a // -b)


def quantize(x: np.floating, dtype: np.uint) -> np.uint:
    return dtype(1 << int(np.ceil(np.log2(x))))


def tri_sign_2d(a: tuple, b: tuple, c: tuple) -> float:
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])


def machine_has_quad_float_support() -> bool:
    try:
        # Try to access the float128 type.
        return hasattr(np, 'float128')
    except (TypeError, AttributeError):
        print('Warning: 128-bit float (float128) is not supported on this platform. Skipping.')
        return False


def machine_has_extended_float_support() -> bool:
    """Check if the machine supports 80-bit extended precision floats (longdouble on x86)."""
    try:
        # Check if longdouble is actually extended precision (80-bit) vs just double (64-bit)
        return hasattr(np, 'longdouble') and np.finfo(np.longdouble).bits > 64
    except (TypeError, AttributeError):
        return False


def largest_dtype_of_kind(kind: np.dtype) -> np.dtype:
    """# Summary

    Get the largest available bit-size for a numpy dtype
    """
    candidate_types = []
    for type_class in set(np.sctypeDict.values()):
        if isinstance(type_class, type) and issubclass(type_class, kind):
            try:
                if np.dtype(type_class).itemsize:
                    candidate_types.append(type_class)
            except TypeError:
                continue

    if not candidate_types:
        raise ValueError(f'Could not find any concrete numpy dtypes for kind {kind}')

    return max(candidate_types, key=lambda x: np.dtype(x).itemsize)
