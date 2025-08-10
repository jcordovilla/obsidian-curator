#!/usr/bin/env python3
"""Basic functionality test for the Obsidian curator system."""

import sys
from pathlib import Path

# Add the current directory to the path so we can import obsidian_curator
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from obsidian_curator import ObsidianCurator, CurationConfig
        from obsidian_curator.models import Note, ContentType, QualityScore, Theme
        from obsidian_curator.content_processor import ContentProcessor
        from obsidian_curator.theme_classifier import ThemeClassifier
        from obsidian_curator.vault_organizer import VaultOrganizer
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_models():
    """Test that data models work correctly."""
    print("Testing data models...")
    
    try:
        from obsidian_curator.models import Note, ContentType, QualityScore, Theme
        
        # Test ContentType enum
        assert ContentType.WEB_CLIPPING == "web_clipping"
        assert ContentType.PERSONAL_NOTE == "personal_note"
        print("✅ ContentType enum works")
        
        # Test QualityScore model
        scores = QualityScore(
            overall=0.8,
            relevance=0.9,
            completeness=0.7,
            credibility=0.8,
            clarity=0.9
        )
        assert scores.overall == 0.8
        assert scores.average_score > 0.8
        print("✅ QualityScore model works")
        
        # Test Theme model
        theme = Theme(
            name="infrastructure",
            confidence=0.9,
            subthemes=["ppps", "financing"],
            keywords=["infrastructure", "development"]
        )
        assert theme.name == "infrastructure"
        assert theme.confidence == 0.9
        print("✅ Theme model works")
        
        # Test Note model
        note = Note(
            file_path=Path("test.md"),
            title="Test Note",
            content="This is a test note content.",
            content_type=ContentType.PERSONAL_NOTE
        )
        assert note.title == "Test Note"
        assert note.content_type == ContentType.PERSONAL_NOTE
        print("✅ Note model works")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_configuration():
    """Test configuration creation."""
    print("Testing configuration...")
    
    try:
        from obsidian_curator import CurationConfig
        
        config = CurationConfig(
            ai_model="gpt-oss:20b",
            quality_threshold=0.7,
            relevance_threshold=0.6,
            max_tokens=2000,
            target_themes=["infrastructure", "construction"],
            preserve_metadata=True,
            clean_html=True
        )
        
        assert config.ai_model == "gpt-oss:20b"
        assert config.quality_threshold == 0.7
        assert config.relevance_threshold == 0.6
        assert "infrastructure" in config.target_themes
        
        print("✅ Configuration works")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_theme_classifier():
    """Test theme classifier functionality."""
    print("Testing theme classifier...")
    
    try:
        from obsidian_curator.theme_classifier import ThemeClassifier
        
        classifier = ThemeClassifier()
        
        # Test theme hierarchy
        assert "infrastructure" in classifier.theme_hierarchy
        assert "construction" in classifier.theme_hierarchy
        assert "ppps" in classifier.theme_hierarchy["infrastructure"]
        
        # Test theme mapping
        mapped_theme = classifier._map_to_hierarchy("public-private partnerships")
        assert "ppps" in mapped_theme or "infrastructure" in mapped_theme
        
        print("✅ Theme classifier works")
        return True
        
    except Exception as e:
        print(f"❌ Theme classifier test failed: {e}")
        return False

def test_content_processor():
    """Test content processor functionality."""
    print("Testing content processor...")
    
    try:
        from obsidian_curator.content_processor import ContentProcessor
        
        processor = ContentProcessor(clean_html=True, preserve_metadata=True)
        
        # Test content type detection
        content_type = processor._determine_content_type({}, "Some regular content")
        assert content_type in ["personal_note", "unknown"]
        
        print("✅ Content processor works")
        return True
        
    except Exception as e:
        print(f"❌ Content processor test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Obsidian Curator functionality tests...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_models,
        test_configuration,
        test_theme_classifier,
        test_content_processor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
