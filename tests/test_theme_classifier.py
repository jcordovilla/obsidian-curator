from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_curator.models import (
    Note,
    ContentType,
    QualityScore,
    Theme,
    CurationResult,
    ContentStructure,
)
from obsidian_curator.theme_classifier import ThemeClassifier


def make_result(title: str, theme_name: str) -> CurationResult:
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
    theme = Theme(name=theme_name, confidence=1.0)
    return CurationResult(
        note=note,
        cleaned_content="text",
        quality_scores=quality,
        themes=[theme],
        content_structure=None,
        is_curated=True,
        curation_reason="",
    )


def test_similarity_threshold_controls_matching() -> None:
    result = make_result("test", "unrelated theme")
    classifier = ThemeClassifier(similarity_threshold=0.9)
    groups = classifier.classify_themes([result])
    assert "unknown" in groups
