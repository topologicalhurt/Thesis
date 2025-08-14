#!/usr/bin/env python

import sys
import argparse as ap
import regex as re

from Allocator.Interpreter.helpers import join_regex


CODESPELL_PATTERNS = [
    r'https?://[^\s]+',                                                    # URL pattern's
    r'([\'"]).*?\\.*?\1',                                                  # Single/double quoted strings with backslash
    r'r([\'"])\1{2}(?:.|\n)*\1{3}',                                        # Raw triple-quoted strings
    r're\.compile\s*\((.|\n)*\)'                                           # re.compile statements
]


def main():
    """Command line interface for joining regex patterns."""

    parser = ap.ArgumentParser(description='Safely join multiple regex patterns into a single alternation pattern.')

    parser.add_argument('patterns', nargs='*',
                        help='One or more regex patterns to join with alternation (|)'
                        )

    args = vars(parser.parse_args())

    if not args['patterns']:
        args['patterns'] = CODESPELL_PATTERNS

    args['patterns'] = [re.sub(r'(!|\$|#|&|`|;)', r'\\\1', pattern)
                        for pattern in args['patterns']]

    try:
        result = join_regex(*args['patterns'])
        print(result)
        sys.exit(0)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
