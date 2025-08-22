"""Utilities for discovering and filtering note files."""

from pathlib import Path
from typing import Iterable, List, Sequence

EXCLUDED_PATTERNS: Sequence[str] = [
    ".obsidian",
    ".trash",
    "templates",
    "template",
    ".git",
]

def discover_markdown_files(root: Path, excluded_patterns: Iterable[str] = EXCLUDED_PATTERNS) -> List[Path]:
    """Return markdown files under *root* filtered by standard rules.

    Hidden files and directories are skipped outright.  Files whose paths contain
    any of *excluded_patterns* are also ignored.  The resulting list is sorted by
    modification time with newest files first.
    """
    markdown_files: List[Path] = []
    for pattern in ("*.md", "*.markdown"):
        markdown_files.extend(root.rglob(pattern))

    valid_files: List[Path] = []
    for file_path in markdown_files:
        if any(part.startswith(".") for part in file_path.parts):
            continue
        if any(excluded in str(file_path).lower() for excluded in excluded_patterns):
            continue
        try:
            if file_path.stat().st_size == 0:
                continue
        except OSError:
            continue
        valid_files.append(file_path)

    valid_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return valid_files
