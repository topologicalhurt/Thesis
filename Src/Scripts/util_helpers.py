"""
------------------------------------------------------------------------
Filename: 	util_helpers.py

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


import ast
import subprocess as sp

from pathlib import Path


def get_git_author() -> tuple[str, str] | None:
    """# Summary

    Get the current user's git credentials via shell

    ## Returns:
        tuple[str, str] | None: the tuple of (author_name, author_email) if the credentials could be found,
        None otherwise
    """
    try:
        name_args = ['git', 'config', '--get', 'user.name']
        author = sp.run(name_args, capture_output=True, text=True, check=True)
        author = author.stdout.strip()

        email_args = ['git', 'config', '--get', 'user.email']
        author_email = sp.run(email_args, capture_output=True, text=True, check=True)
        author_email = author_email.stdout.strip()
    except (sp.CalledProcessError, FileNotFoundError) as e:
        print(f'Error retrieving git config: {e}')
        return None
    return author, author_email


def get_repo_root() -> Path | None:
    """Get the repository root directory.

    Returns:
        Path | None: Path to the repository root if found, None otherwise
    """
    try:
        result = sp.run(['git', 'rev-parse', '--show-toplevel'],
                       capture_output=True, text=True, check=True)
        return Path(result.stdout.strip())
    except (sp.CalledProcessError, FileNotFoundError) as e:
        raise ValueError(f'Error finding repository root: {e}')


def extract_docstring_from_file(file_path: Path) -> str | None:
    """Extract the module-level docstring from a Python file (equivalent to __doc__.strip())."""
    try:
        # Use compile() and exec() to get the __doc__ attribute like Python does
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to compile and execute to get __doc__
        try:
            # Create a module namespace
            module_dict = {}
            compiled = compile(content, str(file_path), 'exec')
            exec(compiled, module_dict)

            # Get the __doc__ attribute if it exists
            doc = module_dict.get('__doc__')
            if doc and isinstance(doc, str):
                return doc.strip()

        except (SyntaxError, Exception):
            # Fallback: parse with AST to get the first string literal
            try:
                tree = ast.parse(content)
                if (tree.body and isinstance(tree.body[0], ast.Expr) and
                    isinstance(tree.body[0].value, ast.Constant) and
                    isinstance(tree.body[0].value.value, str)):
                    return tree.body[0].value.value.strip()
            except SyntaxError:
                pass

    except (OSError, UnicodeDecodeError):
        pass

    return None
