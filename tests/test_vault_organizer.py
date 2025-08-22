from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_curator.models import (
    Note,
    ContentType,
    QualityScore,
    Theme,
    CurationResult,
    CurationConfig,
)
from obsidian_curator.vault_organizer import VaultOrganizer


def make_result(title: str) -> CurationResult:
    note = Note(
        file_path=Path(f"{title}.md"),
        title=title,
        content="text",
        content_type=ContentType.PERSONAL_NOTE,
    )
    quality = QualityScore(
        overall=0.8,
        relevance=0.8,
        completeness=0.8,
        credibility=0.8,
        clarity=0.8,
    )
    theme = Theme(name="test", confidence=1.0)
    return CurationResult(
        note=note,
        cleaned_content="text",
        quality_scores=quality,
        themes=[theme],
        is_curated=True,
        curation_reason="",
    )


def test_save_note_generates_unique_filenames(tmp_path: Path) -> None:
    organizer = VaultOrganizer(CurationConfig())
    result1 = make_result("Duplicate Title")
    result2 = make_result("Duplicate Title")
    organizer._save_note(result1, tmp_path)
    organizer._save_note(result2, tmp_path)
    files = sorted(p.name for p in tmp_path.glob("*.md"))
    assert len(files) == 2
    assert files[0] != files[1]
