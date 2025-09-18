import sys
import os
import subprocess
import hashlib

from pathlib import Path
from collections.abc import Sequence


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def join_regex(*regex: str, non_capture: bool = True, or_join: bool = True) -> str:
    wrapped = [f'(?:{p})' if non_capture else f'({p})' for p in regex]
    return '|'.join(wrapped) if or_join else ''.join(wrapped)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with file_path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_pip_sandboxed(cmd: Sequence[str], cwd: str | None = None) -> Sequence[int, str, str]:
    env = os.environ.copy()
    env.setdefault('PIP_DISABLE_PIP_VERSION_CHECK', '1')
    env.setdefault('PIP_NO_INPUT', '1')

    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=env, text=True)
    return p.returncode, p.stdout, p.stderr
