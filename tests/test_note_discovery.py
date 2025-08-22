from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_curator.note_discovery import discover_markdown_files


def test_discover_markdown_files_filters_hidden_and_excluded(tmp_path: Path) -> None:
    (tmp_path / "visible.md").write_text("visible")
    (tmp_path / ".hidden.md").write_text("hidden")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "temp.md").write_text("temp")

    files = discover_markdown_files(tmp_path)
    assert tmp_path / "visible.md" in files
    assert all("hidden" not in f.name for f in files)
    assert all("templates" not in str(f) for f in files)
