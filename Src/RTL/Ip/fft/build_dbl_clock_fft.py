#!/usr/bin/env python3

"""
Generates a double-piped FFT from ZipCPU's implementation
See: https://zipcpu.com/dsp/2018/10/02/fft.html
"""

import subprocess
import os
import sys


PT_SIZE=1024
IN_WIDTH=24
OUT_WIDTH=24
INVERSE=False


def main():
    git_root = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.STDOUT
    )
    git_root = git_root.rstrip().decode('utf8')
    target_make_path = os.path.join(git_root, 'submodules', 'dblclockfft')
    executable = os.path.join(target_make_path, 'sw', 'fftgen')

    if not os.path.isfile(executable):

        if not os.path.isdir(target_make_path):
            print(
                f'Error: {target_make_path} Not a git repository. Check submodules are correctly added'
            )
            print('Try running: git submodule update --init --recursive')
            return 1

        # Go to the directory and run make
        os.chdir(target_make_path)
        print(f'Attempting to build {target_make_path}...')
        result = subprocess.run(
            ['make'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
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
    os.chdir(os.path.join(target_make_path, 'sw'))
    fftgen_out_location = os.path.join(git_root, 'Src', 'RTL', 'Ip', 'fft')
    subprocess.check_output(['./fftgen', '-d', fftgen_out_location, '-f',
                             str(PT_SIZE), '-n', str(IN_WIDTH), '-m', str(OUT_WIDTH),
                             '-i', '1' if INVERSE else '0'])


if __name__ == '__main__':
    sys.exit(main())
