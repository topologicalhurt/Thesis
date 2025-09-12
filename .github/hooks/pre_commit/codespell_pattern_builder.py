#!/usr/bin/env python
"""Command line interface for joining regex patterns for codespell."""


import sys
import argparse as ap
import re

from Allocator.Interpreter.helpers import join_regex

from utils import eprint


CODESPELL_PATTERNS = [
    r'https?://[^\s]+',                                                    # URL pattern's
    r'([\'"]).*?\\.*?\1',                                                  # Single/double quoted strings with backslash
    r'r([\'"])\1{2}(?:.|\n)*\1{3}',                                        # Raw triple-quoted strings
    r're\.compile\s*\((.|\n)*\)'                                           # re.compile statements
]


def main():
    parser = ap.ArgumentParser(description='Safely join multiple regex patterns into a single alternation pattern for codespell.')
    parser.add_argument('patterns', nargs='*')
    args = vars(parser.parse_args())

    if args['patterns']:
        args['patterns'] = args['patterns'].extend(CODESPELL_PATTERNS)
    else:
        args['patterns'] = CODESPELL_PATTERNS

    args['patterns'] = [re.sub(r'(!|\$|#|&|`|;)', r'\\\1', pattern)
                        for pattern in args['patterns']]

    try:
        result = join_regex(*args['patterns'])
        print(result)
        sys.exit(0)
    except ValueError as e:
        eprint(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
