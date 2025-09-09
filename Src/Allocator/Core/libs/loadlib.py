"""
------------------------------------------------------------------------
Filename: 	loadlib.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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

import ctypes

from pathlib import Path


def load_libs(libs: list[str]) -> list[ctypes.CDLL]:
    build_path = Path(__file__).resolve().parent.parent / 'build'
    loaded_libs: list[ctypes.CDLL] = []
    for candidate in libs:

        # Try loading from build path first
        cand_build = build_path / candidate
        if cand_build.exists():
            try:
                loaded_libs.append(ctypes.CDLL(str(cand_build)))
                continue
            except OSError:
                pass

        # Fallback to system search path
        try:
            loaded_libs.append(ctypes.CDLL(candidate))
        except OSError as e:
            raise OSError(
                f"Could not load '{candidate}'. Tried '{cand_build}' and system path. Original error: {e}"
            ) from e

    return loaded_libs
