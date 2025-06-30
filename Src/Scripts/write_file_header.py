#!/usr/bin/env python
"""
------------------------------------------------------------------------
Filename: 	write_file_header.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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


import os
import sys
import yaml
import textwrap
import argparse as ap
import regex as re

from pathlib import Path
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch

from Allocator.Interpreter.helpers import underline_matches

from Scripts.consts import ALLOCATOR_DIR, CURRENT_DIR, META_INFO, DOCUMENT_META
from Scripts.util_helpers import extract_docstring_from_file
from Scripts.argparse_helpers import get_action_from_parser_by_name, str2path, str2relpath


WHITELISTED = ('*.py', '*.sv', '*.v', '*.ipynb')
BLACKLISTED = ('RTL.*', '.*', 'obj_dir', 'Ip')
ROOT = Path(os.path.join(META_INFO.GIT_ROOT, 'Src'))
DOCUMENT_META = Path(DOCUMENT_META)

HEADER_W = 75
HEADER = """//{separator}
// Filename: 	{fname}
//
// Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.
//
// For more information see the repository: https://github.com/topologicalhurt/Thesis
//
// Purpose:	{file_description}
//
// Author: {author_name} {author_email}
//
//{separator}
// Copyright (C) {copyright_year}, LLAC project LLC
//
// This file is a part of the {module} module
{license_preamble}
// LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
//              As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html
//
// A copy of this license is included at the root directory. It should've been provided to you
// Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
//{separator}"""

RTL_PREAMBLE = """// It is intended to be used as part of the {rtl_module} design where a README.md detailing the design should exist, conforming to the details provided
// under docs/CONTRIBUTING.md. The {rtl_module} module is covered by the GPL 3.0 License (see below.)
//
// The design is NOT COVERED UNDER ANY WARRANTY.
//"""

ALLOCATOR_PREAMBLE = """// It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
// Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.
//
// The design is NOT COVERED UNDER ANY WARRANTY.
//"""

SCRIPT_PREAMBLE = """// It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.
//
// The design is NOT COVERED UNDER ANY WARRANTY.
//"""


def main() -> None:
    global args

    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('-f', '-files', type=str2relpath, nargs='*', default=None,
                    help='A list of files to write the standard file header to. Applied literally (I.e. not recursively).'
                    ' Prohibitions: -r (see: -r)'
                )

    parser.add_argument('-r', type=str2path, nargs='?', const=ROOT, default=None,
                help='When specified, recursively searches for whitelisted files / directories, avoiding blacklisted files / directories.'
                ' The argument is the root where -r is run from. If no argument is provided, uses the default ROOT.'
                ' Prohibitions: -f (see: -f)'
            )

    args = vars(parser.parse_args())

    if args['r'] is not None and args['f'] is not None:
        err_invoker = get_action_from_parser_by_name(parser, 'r')
        matches = underline_matches(' '.join(sys.argv[1:]), ('-r', r'(^|\s)(-f|-files)(?=\s|$)'), match_all=True, literal=False)
        raise ap.ArgumentError(err_invoker,
                        '-r cannot be supplied alongside -f. I.e.:'
                        f'\n{matches}'
                        )

    if args['r'] is None and not args['f']:
        if not args['f']:
            err_invoker = get_action_from_parser_by_name(parser, 'f')
            raise ap.ArgumentError(err_invoker,
                                   'Must supply one of -r, -f. \nWhen -f is supplied '
                                   ' it expects at least one valid posix path as an argument.'
                                   )

        err_invoker = get_action_from_parser_by_name(parser, 'r')
        raise ap.ArgumentError(err_invoker, 'Must supply one of -r, -f. See: --help')

    if args['r'] is not None:
        files = scan_files(ROOT, WHITELISTED, BLACKLISTED)
    else:
        files = args['f']

    if not files:
        print('No files were found matching your criteria. Double check the whitelist, blacklist & root directory.')
        sys.exit(1)

    write_resources_file(files)
    write_headers_to_files()


def should_process_file(fp: Path, whitelisted_patterns: Sequence[str], blacklisted_dirs: Sequence[str]) -> bool:
    """Check if file should be processed based on whitelist/blacklist rules."""

    # Check if any parent directory matches blacklist patterns
    for parent in fp.parents:
        parent_name = parent.name
        for pattern in blacklisted_dirs:
            if fnmatch(parent_name, pattern):
                return False

    # Check if file matches whitelist patterns
    filename = fp.name
    for pattern in whitelisted_patterns:
        if fnmatch(filename, pattern):
            return True

    return False


def scan_files(root_dir: Path, whitelisted_patterns: Sequence[str], blacklisted_dirs: Sequence[str]) -> Sequence[Path]:
    """Scan directory tree and return list of files matching criteria."""
    matched_files = []

    for root, dirs, files in os.walk(root_dir):
        # Remove blacklisted directories from dirs to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if not any(fnmatch(d, pattern) for pattern in blacklisted_dirs)]

        for file in files:
            fp = Path(os.path.join(root, file))
            if should_process_file(fp, whitelisted_patterns, blacklisted_dirs):
                matched_files.append(fp)

    return matched_files


def create_file_metadata(fp: Path) -> Mapping[str, str]:
    """Create metadata dictionary for a file."""
    ext = fp.suffix.lower()
    fname = fp.name

    separator = '-' * (HEADER_W - 3)
    copyright_year = META_INFO.DATE_RUN.year

    if ext in ['.sv', '.v']:
        license_preamble = RTL_PREAMBLE.format_map(
            {
                'rtl_module': fp.parent.name
            }
        )
        module = 'RTL'
    elif ext == '.py' and fp.is_relative_to(ALLOCATOR_DIR):
        license_preamble = ALLOCATOR_PREAMBLE
        module = 'ALLOCATOR'
    elif ext == '.py' and fp.is_relative_to(CURRENT_DIR):
        license_preamble = SCRIPT_PREAMBLE
        module = 'SCRIPTS'
    else:
        license_preamble = None
        module = None

    # For Python files, check if there's an existing docstring to use as description
    existing_docstring = None
    if ext == '.py':
        with open(fp, 'r') as f:
            if not _content_has_header(f.read()):
                existing_docstring = extract_docstring_from_file(fp)

    metadata = {
        'fname': fname,
        'file_description': existing_docstring if existing_docstring else 'N/A',
        'author_name': META_INFO.AUTHOR_CREDENTIALS[0],
        'author_email': META_INFO.AUTHOR_CREDENTIALS[1],
        'module': module,
        'copyright_year': copyright_year,
        'separator': separator,
        'license_preamble': license_preamble
    }

    # Add inputs/outputs artefacts for Verilog/SystemVerilog files
    if ext in ['.sv', '.v']:
        metadata['inputs'] = 'N/A'
        metadata['outputs'] = 'N/A'

    return metadata


def write_resources_file(files: Sequence[Path], output_path: Path = DOCUMENT_META) -> Mapping[str, Mapping[str, str]]:
    """Write file metadata to YAML file, merging with existing entries."""

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    existing_resources = {}
    if output_path.exists():
        try:
            with open(output_path, 'r') as f:
                existing_resources = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            print(f'Warning: Could not load existing YAML file: {e}')
            sys.exit(1)

    # Add metadata for new files only (update only)
    resources = existing_resources.copy()
    for fp in files:
        relative_path = Path(fp).relative_to(ROOT)
        if relative_path not in resources:
            resources[str(relative_path)] = create_file_metadata(fp)
            print(f'Added new file to metadata: {relative_path}')

    with open(output_path, 'w') as f:
        yaml.dump(resources, f, default_flow_style=False, sort_keys=True,
                  default_style="'", allow_unicode=True)

    return resources


def get_file_header(metadata: Mapping[str, str], file_path: Path) -> str:
    """Generate header string for a file using metadata."""
    header = HEADER.format(**metadata)

    if file_path.suffix == '.py':
        lines = header.split('\n')
        cleaned_lines = []

        for line in lines:
            if line.startswith('//'):
                cleaned_line = line[2:].lstrip()
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)

        # Wrap in triple quotes (for docstring)
        content = '\n'.join(cleaned_lines)
        return f'"""\n{content}\n"""'
    else:
        # For non-Python files, wrap each line individually to preserve comment structure
        lines = header.split('\n')
        wrapped_lines = []

        for line in lines:
            if line.strip() == '//':
                wrapped_lines.append(line)
            elif line.startswith('//'):
                # Extract the content after '//'
                content = line[2:].strip()
                if content:
                    # Wrap the content and re-add '//' prefix
                    wrapped = textwrap.fill(content, width=HEADER_W-3)  # -3 for '// '
                    for wrapped_line in wrapped.split('\n'):
                        wrapped_lines.append(f'// {wrapped_line}')
                else:
                    wrapped_lines.append('//')
            else:
                wrapped_lines.append(line)

        return '\n'.join(wrapped_lines)


def _content_has_header(content: str) -> bool:
    """Determine if content has a script generated header"""
    # Really jank, but it works
    return 'GNU GENERAL PUBLIC LICENSE' in content[:1000]


def write_headers_to_files(yaml_path: Path = DOCUMENT_META) -> None:
    """Write headers to all files based on metadata from the yaml_path."""
    try:
        with open(yaml_path, 'r') as f:
            resources = yaml.safe_load(f)
    except FileNotFoundError:
        print(f'Error: {yaml_path} not found. Run main() first to generate metadata.')
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f'Error parsing YAML file: {e}')
        sys.exit(1)

    for relative_path, metadata in resources.items():
        fp = ROOT / relative_path
        if not fp.exists():
            print(f'Warning: File {fp} does not exist, skipping.')
            continue

        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if file already has a header
            if _content_has_header(content):
                continue

            header = get_file_header(metadata, fp)

            new_content = f'{header}\n\n{content}'
            if metadata.get('file_description') != 'N/A' and fp.suffix == '.py':
                docstring_pattern = r'(""".*?"""|\'\'\'.*?\'\'\')'
                match = re.search(docstring_pattern, content, re.DOTALL)

                # If the docstring exists, replace it
                if match:
                    new_content = re.sub(docstring_pattern, header, content, count=1, flags=re.DOTALL)

            # Done! Write out to file
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)
                print(f'Added header to {relative_path}')

        except (OSError, UnicodeDecodeError) as e:
            print(f'Error processing {fp}: {e}')


if __name__ == '__main__':
    main()
