#!/usr/bin/env python3

"""
------------------------------------------------------------------------
Filename: 	build_dbl_clock_fft.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Generates a double-piped FFT from ZipCPU's implementation
See: https://zipcpu.com/dsp/2018/10/02/fft.html

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

import subprocess
import sys

from Scripts.consts import META_INFO


PT_SIZE=1024
IN_WIDTH=24
OUT_WIDTH=24
INVERSE=False


def main():
    target_make_path = META_INFO.GIT_ROOT / 'submodules' / 'dblclockfft'
    executable = target_make_path / 'sw' / 'fftgen'

    if not executable.is_file():

        if not target_make_path.is_dir():
            print(f'Error: {target_make_path} Not a git repository. Check submodules are correctly added.'
                  ' Try running: git submodule update --init --recursive'
                  )
            return 1

        # Go to the directory and run make
        print(f'Attempting to build {target_make_path}...')
        result = subprocess.run(
            ['make'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, cwd=target_make_path
        )
        print('--- Build Output ---')
        print(result.stdout)

        if result.stderr:
            print('--- Error building ---')
            print(result.stderr)
            print(f'Build failed with exit code {result.returncode}')
            return result.returncode

        print('Build completed successfully!')

    # Call fftgen
    fftgen_out_location = META_INFO.GIT_ROOT / 'Src' / 'RTL' / 'Ip' / 'fft'
    subprocess.check_output(['./fftgen', '-d', str(fftgen_out_location), '-f',
                             str(PT_SIZE), '-n', str(IN_WIDTH), '-m', str(OUT_WIDTH),
                             '-i', '1' if INVERSE else '0'], cwd=executable.parent)


if __name__ == '__main__':
    sys.exit(main())
