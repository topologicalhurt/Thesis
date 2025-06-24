"""
Retrieves the imports / dependencies in a .py file using a tree walk
"""

import ast
import importlib.util
import sys
import subprocess
import os
import json


def get_imports(filename):
    with open(filename, 'r') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split('.')[0])
    return imports


def is_builtin_or_local(module_name):
    # Check if it's a built-in module
    if module_name in sys.builtin_module_names:
        return True
    # Check if it's a standard library module
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin and 'site-packages' not in spec.origin:
            return True
    except (ImportError, ModuleNotFoundError):
        pass
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
    if len(sys.argv) < 3:
        print('Usage: python get_imports.py <python_file> <cache_file>')
        sys.exit(1)

    filename = sys.argv[1]
    cache_file = sys.argv[2]

    # Load cache of previously installed packages
    installed_cache = load_cache(cache_file)

    imports = get_imports(filename)
    new_installations = set()

    for imp in imports:
        if not is_builtin_or_local(imp):
            if imp not in installed_cache:
                try:
                    subprocess.run(['pip', 'install', imp], check=True, capture_output=True)
                    print(f'Installed: {imp}')
                    new_installations.add(imp)
                except subprocess.CalledProcessError:
                    print(f'Failed to install: {imp}')
                    pass  # Ignore installation failures
            else:
                print(f'Cached (skipped): {imp}')

    # Update cache with new installations
    if new_installations:
        installed_cache.update(new_installations)
        save_cache(cache_file, installed_cache)

    # Exit with code 1 if new packages were installed, 0 if all cached
    sys.exit(1 if new_installations else 0)
