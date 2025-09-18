#!/usr/bin/env python3
"""
Dependency lock file generator for multi-module projects.
"""

from __future__ import annotations

import ast
import functools
import json
import requests
import hashlib
import subprocess
import sys
import os
import uuid
import argparse as ap

from typing import assert_never
from importlib.metadata import packages_distributions
from pathlib import Path
from dataclasses import dataclass, field, replace

from packaging.version import InvalidVersion, Version

from Allocator.Interpreter.main.extendedenum import ExtendedEnum

from Scripts.argparse_helpers import str2enumval, str2bool

from utils import eprint


# TODO: replace
IMPORT_TO_PACKAGE_MAP = {
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'PIL': 'Pillow',
    'dateutil': 'python-dateutil',
    'OpenGL': 'PyOpenGL',
}

MODULE_ROOTS = {
    'allocator': 'Src/Allocator',
    'scripts': 'Src/Scripts',
    # 'notebook': 'docs/Notebook',
}

# Treat these import prefixes as local (not third-party)
LOCAL_MODULE_PREFIXES = [
    'Allocator',
    'Scripts',
    'Core',
    'Src',
]
LOCAL_MODULE_PREFIXES += [f'Src.{p}' for p in LOCAL_MODULE_PREFIXES if p != 'Src']


class DepResolveMethod(ExtendedEnum):
    PIPDEPTREE = 'pipdeptree'
    PYPI = 'pypi'


@dataclass(frozen=True, slots=True)
class DependencyInfo:
    name: str
    version: str
    source: str = 'pypi'
    hashes: tuple[dict[str, str], ...] = field(default_factory=tuple)

    @property
    def lock_key(self) -> str:
        canonical = f"{self.name.lower()}=={self.version}"
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'version': self.version,
            'source': self.source,
            'hashes': [h for h in self.hashes],
            'lock_key': self.lock_key,
        }


@dataclass(slots=True)
class LockFile:
    modules: dict[str, list[DependencyInfo]] = field(default_factory=dict)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> 'LockFile | None':
        if not path.exists():
            return None

        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            eprint(f"Failed to parse lock file (invalid JSON): {path}")
            return None

        lock = cls()
        lock.metadata = dict(data.get('metadata', {}))

        def _parse_dependencies(dep_list: list[dict]) -> list[DependencyInfo]:
            deps: list[DependencyInfo] = []
            for dep_data in dep_list:
                name = dep_data.get('name')
                version = dep_data.get('version')

                if not name or not version:
                    continue

                deps.append(
                    DependencyInfo(
                        name=name,
                        version=version,
                        source=dep_data.get('source', 'pypi'),
                        hashes=tuple(dep_data.get('hashes', [])),
                    )
                )
            return deps

        # First call: global dependencies, Second call: per-module dependencies
        lock.dependencies.extend(_parse_dependencies(data.get('dependencies', [])))
        for module, module_data in data.get('modules', {}).items():
            lock.modules[module] = _parse_dependencies(module_data.get('dependencies', []))

    def to_dict(self) -> dict:
        modules_dict: dict[str, dict] = {}
        for module, deps in self.modules.items():
            modules_dict[module] = {'dependencies': [d.to_dict() for d in deps]}

        return {
            'modules': modules_dict,
            'dependencies': [d.to_dict() for d in self.dependencies],
            'metadata': self.metadata,
        }


class ImportAnalyzer:
    def __init__(self, root: Path):
        self.root = root
        self.stdlib_modules = set(getattr(sys, 'stdlib_module_names', set(sys.builtin_module_names)))

    def extract_imports(self, file_path: Path) -> set[str]:
        imports: set[str] = set()
        try:
            with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imports.add(node.module.split('.')[0])

        return imports

    def is_third_party(self, module_name: str) -> bool:
        if not module_name:
            return False

        if module_name in self.stdlib_modules or module_name.startswith('_'):
            return False

        if any(module_name.startswith(prefix) for prefix in LOCAL_MODULE_PREFIXES):
            return False

        candidates = [
            self.root / module_name,                      # <root>/<module> (top-level package/dir)
            self.root / f"{module_name}.py",              # <root>/<module>.py
            self.root / 'Src' / module_name,              # <root>/Src/<module>
            self.root / 'Src' / f"{module_name}.py",      # <root>/Src/<module>.py
            self.root / module_name / '__init__.py',      # <root>/<module>/__init__.py
            self.root / 'Src' / module_name / '__init__.py'
        ]
        return not any(p.exists() for p in candidates)

    def analyze_module(self, module_root: Path) -> set[str]:
        if not module_root.exists():
            return set()

        imports: set[str] = set()
        py_files = module_root.rglob('*.py')
        for py_file in py_files:
            file_imports = self.extract_imports(py_file)
            imports.update(name for name in file_imports if self.is_third_party(name))
        return imports


class DependencyResolver:
    def __init__(self):
        self._import_to_dist_cache: dict[str, str] = {}
        self._debug: bool = str2bool(os.environ.get('LOCK_DEBUG', ''))

        if packages_distributions is None:
            self._installed_map: dict[str, list[str]] = {}
        else:
            self._installed_map = packages_distributions()

    def resolve_import_to_package(self, import_name: str) -> str:
        if not import_name:
            return import_name

        cached = self._import_to_dist_cache.get(import_name)
        if cached:
            return cached

        pkg_list = self._installed_map.get(import_name)
        if pkg_list:
            package = pkg_list[0]
            self._import_to_dist_cache[import_name] = package
            return package

        if import_name in IMPORT_TO_PACKAGE_MAP:
            package = IMPORT_TO_PACKAGE_MAP[import_name]
            self._import_to_dist_cache[import_name] = package
            return package

        self._import_to_dist_cache[import_name] = import_name
        return import_name

    def resolve_versions_with_pipdeptree(self, packages: list[str], include_transitive: bool = False) -> dict[str, DependencyInfo]:
        resolved: dict[str, DependencyInfo] = {}

        cmd = [sys.executable, '-m', 'pipdeptree', '--json']
        proc = subprocess.run(cmd, capture_output=True, text=True)
        tree: list[dict] = []
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                tree = json.loads(proc.stdout)
            except json.JSONDecodeError:
                tree = []

        package_map: dict[str, dict] = {}
        deps_graph: dict[str, list[str]] = {}
        for item in tree:
            pkg = item.get('package') or {}
            key = (pkg.get('key') or '').lower()
            if key:
                package_map[key] = pkg
                deps = [ (d.get('key') or '').lower() for d in (item.get('dependencies') or []) ]
                deps_graph[key] = [d for d in deps if d]

        targets: set[str] = set(p.lower().replace('_', '-') for p in packages)
        if include_transitive:

            # BFS over deps_graph to include transitive dependencies
            queue = list(targets)
            while queue:
                cur = queue.pop(0)
                for dep in deps_graph.get(cur, []):
                    if dep not in targets:
                        targets.add(dep)
                        queue.append(dep)

        for key in sorted(targets):
            pkg_info = package_map.get(key)
            if pkg_info:
                name = pkg_info.get('package_name') or key
                resolved[name] = DependencyInfo(
                    name=name,
                    version=pkg_info.get('installed_version', ''),
                    source='pipdeptree'
                )

        return resolved

    @staticmethod
    def pick_release_file(release_files: list[dict]) -> dict | None:
        """Pick release file from pypi.

        in order of preference:
        1. Universal wheels
        2. Manylinux / musllinux wheels (Debian-style compatibility)
        3. Source tarball
        4. First file available
        """
        if not release_files:
            return None

        for f in release_files:
            if f['filename'].endswith('.whl') and 'py3-none-any' in f['filename']:
                return f

        for f in release_files:
            if f['filename'].endswith('.whl') and (
                'manylinux' in f['filename'] or 'musllinux' in f['filename']):
                return f

        for f in release_files:
            if f['filename'].endswith('.tar.gz'):
                return f

        return release_files[0]

    @staticmethod
    def get_latest_version(pkg: str) -> 'DependencyInfo | None':
        """When the resolve method is 'pypi', get the latest version and hash from PyPI.
        Use pick_release_file to choose the appropriate dist.
        """
        try:
            resp = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=10)
        except requests.RequestException:
            return None

        if resp.status_code != 200:
            return None

        data = resp.json()
        valid_versions: list[Version] = []
        for v in data['releases'].keys():
            try:
                valid_versions.append(Version(v))
            except InvalidVersion:
                continue    # skip non-PEP 440 versions

        if not valid_versions:
            return None

        latest_version = str(max(valid_versions))
        release_files = data['releases'].get(latest_version, [])
        f = DependencyResolver.pick_release_file(release_files)
        if f is None:
            return None

        return DependencyInfo(
            name=pkg,
            version=latest_version,
            source='pypi',
            hashes=({'algo': 'sha256', 'value': f['digests']['sha256']},),
        )

    def ensure_hashes(self, dependencies: dict[str, DependencyInfo]) -> dict[str, DependencyInfo]:
        updated: dict[str, DependencyInfo] = {}
        if not dependencies:
            return updated

        for key, dep in dependencies.items():
            if dep.hashes or not dep.version:
                updated[key] = dep
                continue

            try:
                resp = requests.get(f"https://pypi.org/pypi/{dep.name}/json", timeout=10)
            except requests.RequestException:
                continue
            finally:
                updated[key] = dep

            data = resp.json()
            files = data.get('releases', {}).get(dep.version, [])
            f = DependencyResolver.pick_release_file(files)
            if f is None:
                updated[key] = dep
                continue

            sha256 = (f.get('digests') or {}).get('sha256')
            if sha256:
                new_hashes = ({'algo': 'sha256', 'value': sha256},)
                updated[key] = replace(dep, hashes=new_hashes)
            else:
                updated[key] = dep

        return updated


class RequirementsManager:
    def __init__(self, root: Path):
        self.root = root
        self.lock_path = root / 'requirements_lock.json'
        self.analyzer = ImportAnalyzer(root)
        self.resolver = DependencyResolver()

    def load_or_create_lock(self, resolve_method: DepResolveMethod, update: bool = False, include_transitive: bool = False) -> LockFile:
        if not update and self.lock_path.exists():
            lock = LockFile.from_file(self.lock_path)
            if lock:
                return lock

        return self.generate_lock(resolve_method=resolve_method, include_transitive=include_transitive)

    def generate_lock(self, resolve_method: DepResolveMethod, include_transitive: bool) -> LockFile:
        lock = LockFile()
        lock.metadata = {
            'python': f"{sys.version_info.major}.{sys.version_info.minor}",
            'tool': 'lock_requirements.py',
            'lockfile_id': str(uuid.uuid4()),
        }

        module_imports: dict[str, list[str]] = {}
        all_packages: set[str] = set()

        for module, root_path in MODULE_ROOTS.items():
            imports = self.analyzer.analyze_module(self.root / root_path)
            packages = {self.resolver.resolve_import_to_package(imp) for imp in imports}
            module_imports[module] = sorted(packages)
            all_packages.update(packages)

        match resolve_method:
            case DepResolveMethod.PIPDEPTREE:
                resolved = self.resolver.resolve_versions_with_pipdeptree(sorted(all_packages), include_transitive=include_transitive)
            case DepResolveMethod.PYPI:
                tmp = {package: self.resolver.get_latest_version(package) for package in sorted(all_packages)}
                resolved = {k: v for k, v in tmp.items() if v is not None}
            case _:
                assert_never(resolve_method)

        resolved = self.resolver.ensure_hashes(resolved)

        for module, packages in module_imports.items():
            lock.modules[module] = [resolved[pkg] for pkg in packages if pkg in resolved]

        lock.dependencies = sorted(resolved.values(), key=lambda d: d.name.lower())

        return lock

    def write_lock(self, lock: LockFile) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open('w', encoding='utf-8') as f:
            json.dump(lock.to_dict(), f, indent=2, ensure_ascii=False)

    def write_requirements_files(self, lock: LockFile) -> None:
        paths = {
            'allocator': self.root / 'Src' / 'Allocator' / 'requirements.txt',
            'scripts': self.root / 'Src' / 'Scripts' / 'requirements.txt',
            # 'notebook': self.root / 'docs' / 'Notebook' / 'requirements.txt',
        }

        for module, deps in lock.modules.items():
            target = paths.get(module)

            if not target:
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('w', encoding='utf-8') as f:
                for dep in sorted(deps, key=lambda d: d.name.lower()):
                    f.write(f"{dep.name}=={dep.version}\n")


def main() -> int:
    parser = ap.ArgumentParser(description='Generate Python dependency lock files')
    parser.add_argument('--update', action='store_true', help='Update the lock file')
    parser.add_argument('--write-txt', action='store_true', help='Write requirements.txt files')
    parser.add_argument('--resolve-method', default='pypi',
                        type=functools.partial(str2enumval, target_enum=DepResolveMethod))
    parser.add_argument('--include-transitive', default='false', type=str2bool,
                        help='Include transitive dependencies (default: false)')
    args = parser.parse_args()

    root_env = os.environ.get('ROOT')
    if root_env is None:
        eprint('Invalid or missing ROOT environment variable')
        return 1

    root = Path(root_env)

    manager = RequirementsManager(root)
    lock = manager.load_or_create_lock(resolve_method=args.resolve_method,
                                       update=args.update,
                                       include_transitive=args.include_transitive)

    if args.update:
        manager.write_lock(lock)

    if args.write_txt:
        manager.write_requirements_files(lock)

    print(json.dumps(lock.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
