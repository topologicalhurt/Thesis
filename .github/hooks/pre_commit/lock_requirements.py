#!/usr/bin/env python3
"""
Generate a single requirements_lock.json capturing latest versions of third-party deps.

Features:
- Scans tracked Python files via `git ls-files` within selected module roots.
- Filters out stdlib, builtins, and local project modules (e.g., Allocator, Scripts).
- Maps common import names to PyPI package names.
- Resolves latest versions using pip's resolver (dry-run report) when available,
  falling back to `pip index versions`.
- Outputs clean JSON ONLY on stdout; logs to stderr.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import hashlib
import argparse as ap
from pathlib import Path

from typing import Iterable, Set, Dict, List, Tuple


# Minimal fallback map for notorious mismatches when pip cannot infer a distro
FALLBACK_IMPORT_TO_DIST: Dict[str, str] = {
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'PIL': 'Pillow',
    'dateutil': 'python-dateutil',
}

MODULES: Dict[str, str] = {
    'allocator': 'Src/Allocator',
    'scripts': 'Src/Scripts',
    'notebook': 'docs/Notebook',
}

SKIP_IMPORT_PREFIXES = (
    'Allocator',
    'Scripts',
    'Src/Allocator',
    'Src/Scripts',
)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run(cmd: List[str], cwd: str | None = None) -> Tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault('PIP_DISABLE_PIP_VERSION_CHECK', '1')
    env.setdefault('PIP_NO_INPUT', '1')
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def git_ls_py_files(root: Path | str) -> List[Path]:
    root = Path(root)
    code, out, err = run(['git', 'ls-files', '--', str(root)])
    if code != 0 or not out.strip():
        # Fallback to filesystem walk
        paths: List[Path] = []
        for p in root.rglob('*.py'):
            if 'submodules' in p.parts:
                continue
            paths.append(p)
        return paths
    return [Path(p) for p in out.splitlines() if p.endswith('.py')]


def load_stdlib_names() -> Set[str]:
    names: Set[str] = set()
    try:
        names = set(sys.stdlib_module_names)  # py3.10+
    except Exception:
        # Minimal fallback
        names.update({'sys', 'os', 're', 'json', 'math', 'itertools', 'subprocess', 'pathlib', 'logging'})
    return names


def parse_imports(py_path: Path | str) -> Set[str]:
    try:
        with open(py_path, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=str(py_path))
    except SyntaxError:
        return set()

    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split('.')[0])
    return mods


def is_local_module(name: str, root: Path | str) -> bool:
    # Treat as local if a package/module exists under project src roots
    root = Path(root)
    candidates = [
        root / 'Src' / name / '__init__.py',
        root / 'Src' / f'{name}.py',
        root / name / '__init__.py',
        root / f'{name}.py',
    ]
    return any(p.exists() for p in candidates)


def packages_distributions_map() -> Dict[str, List[str]]:
    try:
        # Python 3.10+: returns mapping of top-level import names to distributions installed
        from importlib.metadata import packages_distributions  # type: ignore
        return dict(packages_distributions())
    except Exception:
        return {}


def resolve_import_to_dist_via_installed(name: str, pkgdist: Dict[str, List[str]]) -> str | None:
    dists = pkgdist.get(name)
    if dists:
        return dists[0]
    return None


def resolve_import_to_dist_via_pip(name: str) -> str | None:
    """Ask pip's resolver what it would install for this requirement and use that distribution name."""
    # First attempt: use the import name as requirement
    code, out, err = run([sys.executable, '-m', 'pip', 'install', '--dry-run', '--report', '-', name])
    if code == 0 and out.strip():
        try:
            data = json.loads(out)
            for item in data.get('install', []):
                meta = item.get('metadata', {})
                if meta.get('name'):
                    return meta['name']
        except json.JSONDecodeError:
            pass

    # Try some normalized/common variants
    candidates = [
        name.lower(),
        name.replace('_', '-'),
        f'python-{name}',
    ]
    for cand in candidates:
        code, out, err = run([sys.executable, '-m', 'pip', 'install', '--dry-run', '--report', '-', cand])
        if code == 0 and out.strip():
            try:
                data = json.loads(out)
                for item in data.get('install', []):
                    meta = item.get('metadata', {})
                    if meta.get('name'):
                        return meta['name']
            except json.JSONDecodeError:
                continue
    return None


def resolve_imports_to_distributions(imports: Iterable[str]) -> List[str]:
    pkgdist = packages_distributions_map()
    dists: List[str] = []
    for name in imports:
        # 1) If already installed, map via metadata
        dist = resolve_import_to_dist_via_installed(name, pkgdist)
        if not dist:
            # 2) Ask pip resolver
            dist = resolve_import_to_dist_via_pip(name)
        if not dist:
            # 3) Fallback to minimal curated map or the import name itself
            dist = FALLBACK_IMPORT_TO_DIST.get(name, name)
        dists.append(dist)
    # De-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for d in dists:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def resolve_latest_via_pip_report(requirements: List[str]) -> Dict[str, Dict[str, str]]:
    """Use pip's resolver report to determine pinned versions and hashes."""
    lock: Dict[str, Dict[str, str]] = {}
    # pip --dry-run --report - <pkgs>
    cmd = [sys.executable, '-m', 'pip', 'install', '--dry-run', '--report', '-'] + requirements
    code, out, err = run(cmd)
    if code != 0 or not out.strip():
        eprint('pip report failed; stderr:', err.strip()[:4000])
        return lock
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        eprint('pip report returned non-JSON output')
        return lock

    # data.install is list of artifacts
    for item in data.get('install', []):
        meta = item.get('metadata', {})
        name = meta.get('name')
        version = meta.get('version')
        if not name or not version:
            continue
        # Normalize name to canonical PyPI name casing
        key = name
        hashes = []
        di = item.get('download_info') or {}
        ai = di.get('archive_info') or {}
        hash_val = ai.get('hashes', {}).get('sha256') or ai.get('hash')
        if hash_val:
            # Could be prefixed like 'sha256=<hex>'
            if '=' in hash_val:
                hash_val = hash_val.split('=', 1)[1]
            hashes.append({'algo': 'sha256', 'value': hash_val})
        lock[key] = {
            'version': version,
            'hashes': hashes,
            'source': 'pypi',
        }
    return lock


def resolve_latest_via_pip_index(names: List[str]) -> Dict[str, Dict[str, str]]:
    lock: Dict[str, Dict[str, str]] = {}
    for name in names:
        cmd = [sys.executable, '-m', 'pip', 'index', 'versions', name]
        code, out, err = run(cmd)
        if code != 0 or not out.strip():
            eprint(f'pip index failed for {name}: {err.strip()[:4000]}')
            continue
        m = re.search(r'LATEST:\s*([0-9][^\s,]*)', out)
        if m:
            lock[name] = {
                'version': m.group(1),
                'hashes': [],
                'source': 'pypi',
            }
    return lock


def compute_sha256_of_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_hashes_via_download(lock: Dict[str, Dict[str, str]]) -> None:
    """Best-effort: for entries missing hashes, pip download the artifact and compute sha256."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        for name, info in lock.items():
            if info.get('hashes'):
                continue
            version = info.get('version')
            if not version:
                continue
            # Download a wheel or sdist for this package/version
            code, out, err = run([sys.executable, '-m', 'pip', 'download', f'{name}=={version}', '-d', str(tdp), '--no-deps'])
            if code != 0:
                continue
            files = list(tdp.glob(f'{name.replace("-", "_").replace(".", "_")}*'))
            if not files:
                files = list(tdp.glob('*'))
            if not files:
                continue
            sha = compute_sha256_of_file(files[0])
            info['hashes'] = [{'algo': 'sha256', 'value': sha}]


def main() -> int:
    write_txt = False
    parser = ap.ArgumentParser(add_help=False)
    parser.add_argument('--write-txt', action='store_true', default=False)

    try:
        args, _ = parser.parse_known_args()
        write_txt = bool(args.write_txt)
    except SystemExit:
        write_txt = False

    root_str = os.environ.get('ROOT') or subprocess.getoutput('git rev-parse --show-toplevel') or str(Path.cwd())
    root = Path(root_str)
    os.chdir(str(root))

    stdlib = load_stdlib_names()

    # Collect per-module import names
    per_module_imports: Dict[str, Set[str]] = {k: set() for k in MODULES}
    for mod, mroot in MODULES.items():
        for py in git_ls_py_files(root / mroot):
            for name in parse_imports(py):
                if (name in stdlib) or name.startswith('_'):
                    continue
                if any(name.startswith(p) for p in SKIP_IMPORT_PREFIXES):
                    continue
                if is_local_module(name, root):
                    continue
                per_module_imports[mod].add(name)

    # Resolve to distributions per module
    per_module_wanted: Dict[str, List[str]] = {
        mod: sorted(resolve_imports_to_distributions(names)) for mod, names in per_module_imports.items()
    }

    # Union for global resolution
    wanted_union: List[str] = sorted({d for lst in per_module_wanted.values() for d in lst})

    lock: Dict[str, Dict[str, str]] = resolve_latest_via_pip_report(wanted_union)
    unresolved = [n for n in wanted_union if n not in lock]
    if unresolved:
        lock.update(resolve_latest_via_pip_index(unresolved))

    # Ensure hashes for all entries (best-effort)
    ensure_hashes_via_download(lock)

    # Build per-module dependency lists from global lock
    modules_out: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
    for mod, names in per_module_wanted.items():
        deps = []
        for name in names:
            info = lock.get(name, {})
            version = info.get('version')
            hv = hashlib.sha256(f'{name}=={version}'.encode('utf-8')).hexdigest() if version else None
            deps.append({
                'name': name,
                'version': version,
                'source': info.get('source', 'pypi'),
                'hashes': info.get('hashes', []),
                'lock_key': hv,
            })
        modules_out[mod] = {'dependencies': deps}

    # Global dependencies list (union)
    entries = []
    for name in sorted(lock.keys(), key=str.lower):
        info = lock[name]
        version = info.get('version')
        hv = hashlib.sha256(f'{name}=={version}'.encode('utf-8')).hexdigest() if version else None
        entries.append({
            'name': name,
            'version': version,
            'source': info.get('source', 'pypi'),
            'hashes': info.get('hashes', []),
            'lock_key': hv,
        })

    out = {
        'modules': modules_out,
        'dependencies': entries,
        'metadata': {
            'python': f'{sys.version_info[0]}.{sys.version_info[1]}',
            'tool': 'lock_requirements.py',
            'root': str(root),
        }
    }

    # Optionally write per-module requirements.txt
    if write_txt:
        mod_paths: Dict[str, Path] = {
            'allocator': root / 'Src' / 'Allocator' / 'requirements.txt',
            'scripts': root / 'Src' / 'Scripts' / 'requirements.txt',
            'notebook': root / 'docs' / 'Notebook' / 'requirements.txt',
        }
        for mod, data in modules_out.items():
            req_path = mod_paths.get(mod)
            if not req_path:
                continue
            req_path.parent.mkdir(parents=True, exist_ok=True)
            with req_path.open('w', encoding='utf-8') as f:
                for dep in data['dependencies']:
                    name = dep.get('name')
                    version = dep.get('version')
                    if name and version:
                        f.write(f'{name}=={version}\n')

    print(json.dumps(out, indent=2, sort_keys=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        eprint(f'ERROR: {exc}')
        sys.exit(2)
