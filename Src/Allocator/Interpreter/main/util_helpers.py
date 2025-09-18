"""
------------------------------------------------------------------------
Filename: 	helpers.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Common helper / utility functions

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

from pathlib import Path

from Allocator.Interpreter.main.common_utils import join_regex


def greater_than_n_regex(n: int) -> str:
    """# Summary

    Returns the regex for >= n
    """
    result = [r'\d*']
    i = 0   # Value will be log10(n) after loop
    while n:
        d, r = divmod(n, 10)
        result.append(rf'[{r}-9]')
        n = d
        i += 1
    result = reversed(result)
    return join_regex(fr'[1-9]\d{{{i},}}', ''.join(result))


def get_repo_root(start: Path | None = None) -> Path:
    """Discover the Git worktree root WITHOUT invoking the git executable.

    Walks upward from `start` (or CWD) looking for a `.git` directory OR a
    `.git` file (worktree/submodule pointer). Returns the first directory
    containing one of these. Raises FileNotFoundError if no repository root
    is found.
    """
    p = (start or Path.cwd()).resolve()
    for candidate in (p, *p.parents):
        git_path = candidate / '.git'
        if git_path.is_dir():
            return candidate
        if git_path.is_file():  # worktree / submodule pointer
            try:
                with git_path.open('r', encoding='utf-8') as f:
                    first = f.readline().strip()
                if first.startswith('gitdir:'):
                    return candidate
            except OSError:
                continue
    raise FileNotFoundError(f'No .git directory found from {p}')
