from pathlib import Path

from Allocator.Interpreter.main.util_helpers import get_repo_root


CURRENT_DIR = Path(__file__).parent.resolve()
ROOT = get_repo_root()
DOCS_DIR = ROOT / 'docs'
RESOURCES_DIR = DOCS_DIR / 'resources'
IMGS_DIR = RESOURCES_DIR / 'imgs'
MARKDOWN_DIR = RESOURCES_DIR / 'markdown'
