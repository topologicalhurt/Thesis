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
import yaml
import textwrap

from pathlib import Path
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch

from RTL.Scripts.consts import ALLOCATOR_DIR, CURRENT_DIR, META_INFO, RESOURCES_DIR
from RTL.Scripts.util_helpers import extract_docstring_from_file


WHITELISTED = ('*.py', '*.sv', '*.v', '*.ipynb')
BLACKLISTED = ('RTL.*', '.*', 'obj_dir', 'Ip')
ROOT = Path(os.path.join(META_INFO.GIT_ROOT, 'Src'))
OUTPUT_FILE = Path(os.path.join(RESOURCES_DIR, 'document_meta.yaml'))

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
//{separator}
"""

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

    metadata = {
        'fname': fname,
        'file_description': 'N/A',
        'purpose': 'N/A',
        'author_name': META_INFO.AUTHOR_CREDENTIALS[0],
        'author_email': META_INFO.AUTHOR_CREDENTIALS[1],
        'module': module,
        'copyright_year': copyright_year,
        'separator': separator,
        'license_preamble': license_preamble
    }

    # Add inputs/outputs description for Verilog/SystemVerilog files
    if ext in ['.sv', '.v']:
        metadata['inputs'] = 'N/A'
        metadata['outputs'] = 'N/A'

    return metadata


def write_resources_file(files: Sequence[Path], output_path: Path) -> Mapping[str, Mapping[str, str]]:
    """Write file metadata to YAML file."""
    resources = {}

    for filepath in files:
        relative_path = os.path.relpath(filepath, ROOT)
        resources[relative_path] = create_file_metadata(filepath)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Write file with single quotes
    with open(output_path, 'w') as f:
        yaml.dump(resources, f, default_flow_style=False, sort_keys=True,
                  default_style="'", allow_unicode=True)

    return resources


def get_file_header(metadata: Mapping[str, str], file_path: Path) -> str:
    """Generate header string for a file using metadata."""
    is_python = file_path.suffix == '.py'

    # For Python files, check if there's an existing docstring to use as description
    if is_python:
        existing_docstring = extract_docstring_from_file(file_path)
        if existing_docstring and metadata.get('file_description') == 'N/A':
            # Create a new metadata dict with the docstring as description
            updated_metadata = dict(metadata)
            updated_metadata['file_description'] = existing_docstring
            metadata = updated_metadata

    header = HEADER.format(**metadata)

    if is_python:
        # For Python files, remove '//' comments and wrap in docstring
        lines = header.split('\n')
        cleaned_lines = []

        for line in lines:
            if line.startswith('//'):
                # Remove '//' and leading space
                cleaned_line = line[2:].lstrip()
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)

        # Wrap in triple quotes
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


def write_headers_to_files(yaml_path: Path = OUTPUT_FILE) -> None:
    """Write headers to all files based on metadata from document_meta.yaml."""
    try:
        with open(yaml_path, 'r') as f:
            resources = yaml.safe_load(f)
    except FileNotFoundError:
        print(f'Error: {yaml_path} not found. Run main() first to generate metadata.')
        return
    except yaml.YAMLError as e:
        print(f'Error parsing YAML file: {e}')
        return

    for relative_path, metadata in resources.items():
        fp = ROOT / relative_path

        if not fp.exists():
            print(f'Warning: File {fp} does not exist, skipping.')
            continue

        # Skip files that already have headers
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if file already has a header
            if 'GNU GENERAL PUBLIC LICENSE' in content[:1000]:
                print(f'Header already exists in {relative_path}, skipping.')
                continue

            # Generate header
            header = get_file_header(metadata, fp)

            # Add appropriate line ending and newlines
            new_content = f'{header}\n\n{content}'

            # Write back to file
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f'Added header to {relative_path}')

        except (OSError, UnicodeDecodeError) as e:
            print(f'Error processing {fp}: {e}')


def main() -> None:
    files = scan_files(ROOT, WHITELISTED, BLACKLISTED)

    if files:
        write_resources_file(files, OUTPUT_FILE)
        write_headers_to_files()


if __name__ == '__main__':
    main()
