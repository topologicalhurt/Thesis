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


import logging
import ast
import shutil
import subprocess as sp

from pathlib import Path

from Scripts.decorators import deprecated


LOGGER = logging.getLogger('Scripts.consts')


def get_git_author() -> tuple[str, str] | None:
    """Return (user.name, user.email) from git config without relying on bare 'git' in PATH.

    Strategy:
    1. Locate git executable via shutil.which; if present, invoke directly using its absolute path.
    2. Fallback: parse .git/config (repository local) then ~/.gitconfig for user section.
    3. On failure, return None.
    """
    git_exe = shutil.which('git')
    name: str | None = None
    email: str | None = None

    def _parse_git_config_file(cfg: Path):
        nonlocal name, email
        if not cfg.exists() or not cfg.is_file():
            return
        try:
            cur_section = None
            for line in cfg.read_text(encoding='utf-8', errors='ignore').splitlines():
                line = line.strip()
                if not line or line.startswith(('#',';')):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    cur_section = line[1:-1].strip().strip('"')
                    continue
                if cur_section == 'user' and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == 'name' and not name:
                        name = v
                    elif k == 'email' and not email:
                        email = v
                if name and email:
                    return
        except OSError:
            return

    # Try git executable if found
    if git_exe:
        try:
            author = sp.run([git_exe, 'config', '--get', 'user.name'], capture_output=True, text=True, check=True)
            name = author.stdout.strip() or None
            email_proc = sp.run([git_exe, 'config', '--get', 'user.email'], capture_output=True, text=True, check=True)
            email = email_proc.stdout.strip() or None
        except (sp.CalledProcessError, FileNotFoundError):
            pass

    # Parse config files if still missing
    if not (name and email):
        # local repo config
        try:
            repo_root = get_repo_root()
            _parse_git_config_file(repo_root / '.git' / 'config')
        except FileNotFoundError:
            pass
        # global config (~/.gitconfig)
        if not (name and email):
            home_cfg = Path.home() / '.gitconfig'
            _parse_git_config_file(home_cfg)

    if name and email:
        return name, email

    LOGGER.warning('Could not determine git author from config or executable.')
    return None


@deprecated('Use get_repo_root() which avoids invoking external git executable.')
def get_repo_root_shell() -> Path | None:
    """(Deprecated) Determine repository root via 'git rev-parse --show-toplevel'.

    Falls back to returning None on failure. Prefer get_repo_root for a pure
    filesystem implementation that avoids executing arbitrary repository hooks.
    """
    git_exe = shutil.which('git')
    try:
        result = sp.run([git_exe, 'rev-parse', '--show-toplevel'],
                        capture_output=True, text=True, check=True)
        return Path(result.stdout.strip())
    except (sp.CalledProcessError, FileNotFoundError):
        return None


def extract_docstring_from_file(file_path: Path) -> str | None:
    """Safely extract the module-level docstring from a Python source file.

    Returns the cleaned docstring (``stripped``) or ``None`` if no module docstring
    could be determined (syntax error, encoding error, or absent docstring).
    """
    try:
        source = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    doc = ast.get_docstring(tree, clean=True)
    if doc is not None:
        return doc.strip()

    # Fallback: explicitly inspect first node (should rarely be needed; ast.get_docstring normally covers this)
    if (tree.body and isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, ast.Constant) and
            isinstance(tree.body[0].value.value, str)):
        return tree.body[0].value.value.strip()
    return None
