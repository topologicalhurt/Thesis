# setup.py
#
# To build the Cython module, run this command in your terminal:
# python setup.py build_ext --inplace

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
