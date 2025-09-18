"""
------------------------------------------------------------------------
Filename: 	hashable_array.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	------------------------------------------------------------------------
Filename:       hashable_array.py

Project:        LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:        Hashable wrapper for numpy arrays.

- Stores an immutable copy of the input array.
- Hash is based on a stable digest of (dtype, shape, content).
- Equality compares dtype, shape, and content equality.

Note: Mutating the original input after wrapping does not affect the wrapper
since an internal copy is made and marked read-only.

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

from __future__ import annotations

import numpy as np

from Allocator.Interpreter.main.common_utils import combined_fast_stable_hash


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
