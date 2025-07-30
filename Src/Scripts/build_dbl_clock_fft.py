#!/usr/bin/env python3

"""
Generates a double-piped FFT from ZipCPU's implementation
See: https://zipcpu.com/dsp/2018/10/02/fft.html
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
