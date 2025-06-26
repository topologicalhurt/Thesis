"""
------------------------------------------------------------------------
Filename: 	setup.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:    setup.py
To build the Cython module, run this command in your terminal:
python setup.py build_ext --inplace

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


from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy # Required for include_dirs


# NOTE: This may make the compiled binary less portable.
compile_args = [
    '-O3',
    '-ffast-math',
    '-s',
]

# Trade safety for speed.
compiler_directives = {
    'language_level': 3,          # Use Python 3 semantics
    'boundscheck': False,         # Don't check for array out-of-bounds errors
    'wraparound': False,          # Don't support negative indexing
    'cdivision': True,            # Use C-style division (no zero-check)
    'initializedcheck': False,    # Don't check if memoryviews are initialized
}

extensions = [
    Extension(
        'LLAC',
        ['Interpreter/helpers.py'],
        include_dirs=[numpy.get_include()], # Necessary for numpy integration
        extra_compile_args=compile_args,
    ),
]

setup(
    name='LLAC',
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        # Use annotate=True to generate a HTML report showing where
        # code is interacting with Python, which is a source of slowness.
        annotate=True
    )
)
