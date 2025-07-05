#!/usr/bin/env python
"""
Retrieves the imports / dependencies in a .py file using a tree walk
"""

import ast
import importlib.util
import sys
import os
import json
import warnings


warnings.filterwarnings('ignore', category=SyntaxWarning)

# Maps common import names to their actual package names on PyPI
IMPORT_TO_PACKAGE_MAP = {
    'yaml': 'PyYAML',
    'sklearn': 'scikit-learn',
    'cv2': 'opencv-python',
    'bs4': 'beautifulsoup4',
    'PIL': 'Pillow',
    'dateutil': 'python-dateutil',
    'dotenv': 'python-dotenv'
}


def main():
    if len(sys.argv) < 3:
        print('Usage: python get_imports.py <python_file> <cache_file>')
        sys.exit(1)

    filename = sys.argv[1]
    cache_file = sys.argv[2]

    installed_cache = load_cache(cache_file)
    imports = get_imports(filename)

    packages_to_install = []
    newly_found_imports = []

    for imp in imports:
        if is_third_party(imp):
            if imp not in installed_cache:
                # Translate the import name to the correct PyPI package name
                package_name = IMPORT_TO_PACKAGE_MAP.get(imp, imp)
                packages_to_install.append(package_name)
                newly_found_imports.append(imp) # Cache the original import name

    # Update cache with the newly found import names to avoid re-processing
    if newly_found_imports:
        installed_cache.update(newly_found_imports)
        save_cache(cache_file, installed_cache)

    # Print the list of correct package names to be installed by the shell script
    print(packages_to_install)


def get_imports(filename):
    """Parses a Python file and returns a list of top-level imports."""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            tree = ast.parse(f.read(), filename=filename)
        except SyntaxError:
            return []

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0: # Absolute imports only
                imports.add(node.module.split('.')[0])
    return list(imports)


def is_third_party(module_name):
    """
    Determines if a module is a third-party package.
    Returns True if it is, False if it's a built-in, standard library, or local module.
    """
    if module_name in sys.builtin_module_names:
        return False

    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return True

    if spec is None:
        return True

    if spec.origin and ('site-packages' in spec.origin or 'dist-packages' in spec.origin):
        return True

    return False


def load_cache(cache_file):
    """Load previously installed packages from cache file"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def save_cache(cache_file, installed_packages):
    """Save installed packages to cache file"""
    try:
        with open(cache_file, 'w') as f:
            json.dump(list(installed_packages), f)
    except IOError:
        pass  # Ignore cache save failures


if __name__ == '__main__':
    main()
