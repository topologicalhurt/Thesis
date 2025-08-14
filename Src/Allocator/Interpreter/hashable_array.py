"""
Hashable wrapper for numpy arrays.

- Stores an immutable copy of the input array.
- Hash is based on a stable digest of (dtype, shape, content).
- Equality compares dtype, shape, and content equality.

Note: Mutating the original input after wrapping does not affect the wrapper
since an internal copy is made and marked read-only.
"""
from __future__ import annotations

import numpy as np

from Allocator.Interpreter.helpers import combined_fast_stable_hash


class HashableArray:
    __slots__ = ('_arr', '_shape', '_dtype', '_digest')

    def __init__(self, arr: np.ndarray):
        a = np.asarray(arr, copy=True)
        a.setflags(write=False)

        self._arr: np.ndarray = a
        self._shape: tuple[int, ...] = a.shape
        self._dtype: str = a.dtype.str      # Use numpy dtype.str for a canonical representation (e.g., '<f8')

        dtype_bytes = self._dtype.encode('utf-8')
        shape_bytes = np.asarray(self._shape, dtype=np.int64).tobytes()
        content_bytes = a.tobytes(order='C')

        self._digest: int = combined_fast_stable_hash([dtype_bytes, shape_bytes, content_bytes])

    @property
    def array(self) -> np.ndarray:
        return self._arr

    def __hash__(self) -> int:
        return self._digest

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if not isinstance(other, HashableArray):
            return False

        return (
            self._dtype == other._dtype
            and self._shape == other._shape
            and np.array_equal(self._arr, other._arr)
        )

    def __repr__(self) -> str:
        return f"HashableArray(shape={self._shape}, dtype={self._dtype})"
