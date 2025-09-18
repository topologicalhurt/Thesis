#!/usr/bin/env python
"""Command line interface for joining regex patterns for codespell."""

import sys
import argparse as ap
import re

from utils import eprint, join_regex


CODESPELL_PATTERNS = [
    r'https?://[^\s]+',                                                    # URL pattern's
    r'([\'"]).*?\\.*?\1',                                                  # Single/double quoted strings with backslash
    r'r([\'"])\1{2}(?:.|\n)*\1{3}',                                        # Raw triple-quoted strings
    r're\.compile\s*\((.|\n)*\)',                                          # re.compile statements

    # Heuristic: ignore concatenations of common HW/domain tokens repeated 2+ times (e.g., inout, readdata, writedata)
    # This avoids false positives like 'inout' in SystemVerilog while keeping checks for normal words.
    (lambda: (
        r'\b(?:' +
        join_regex(
            'in','out','read','write','addr','data','clk','rst','reset','en','valid','ready',
            'tx','rx','pll','fifo','dma','ref','sync','bus','i2s','i','o','n', or_join=True
        ) +
        r'){2,}\b'
    ))()
]


def main():
    parser = ap.ArgumentParser(description='Safely join multiple regex patterns into a single alternation pattern for codespell.')
    parser.add_argument('patterns', nargs='*')
    args = vars(parser.parse_args())

    if args['patterns']:
        args['patterns'] = list(args['patterns']) + CODESPELL_PATTERNS
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
