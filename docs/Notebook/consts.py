from pathlib import Path

from Src.Scripts.util_helpers import get_repo_root


CURRENT_DIR = Path(__file__).parent.resolve()
ROOT = get_repo_root()
DOCS_DIR = ROOT / 'docs'
RESOURCES_DIR = DOCS_DIR / 'resources'
MARKDOWN_DIR = RESOURCES_DIR / 'markdown'
