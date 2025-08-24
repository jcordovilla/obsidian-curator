#!/usr/bin/env python3
"""Test script for AI content classification functionality."""

import sys
from pathlib import Path

# Add the obsidian_curator package to the path
sys.path.insert(0, str(Path(__file__).parent))

from obsidian_curator.ai_content_classifier import AIContentClassifier, ContentCategory
from obsidian_curator.specialized_processors import SpecializedContentProcessor
from obsidian_curator.content_processor import ContentProcessor


def test_ai_classification():
    """Test the AI content classification system."""
    print("🧠 Testing AI Content Classification System")
    print("=" * 50)
    
    # Test content samples
    test_cases = [
        {
            "name": "URL Bookmark",
            "content": """# Infrastructure Investment Guide
https://www.example.com/infrastructure-guide
A comprehensive guide to infrastructure investment strategies.""",
            "expected_category": ContentCategory.URL_BOOKMARK
        },
        {
            "name": "Web Clipping",
            "content": """<div class="article">
<h1>Public-Private Partnerships in Infrastructure</h1>
<p>This article discusses the benefits and challenges of PPPs...</p>
<div class="navigation">Menu | Home | About</div>
</div>""",
            "expected_category": ContentCategory.WEB_CLIPPING
        },
        {
            "name": "PDF Annotation",
            "content": """![[technical_report.pdf]]
This is my analysis of the technical report above.
Key findings: The project is feasible but requires careful planning.""",
            "expected_category": ContentCategory.PDF_ANNOTATION
        },
        {
            "name": "Pure Text Note",
            "content": """# My Infrastructure Analysis

This is my personal analysis of the current state of infrastructure development in Spain.

Key observations:
1. There's a significant gap in funding
2. Private sector participation is limited
3. Regulatory framework needs improvement

I believe the solution lies in creating better incentives for private investment while maintaining public oversight.""",
            "expected_category": ContentCategory.PURE_TEXT_NOTE
        },
        {
            "name": "Social Media Post",
            "content": """LinkedIn Post: Just published my thoughts on infrastructure funding.

The current model isn't sustainable. We need innovative approaches that combine public and private resources.

#Infrastructure #Funding #Innovation #PublicPrivatePartnerships

Follow me for more insights on infrastructure development.""",
            "expected_category": ContentCategory.SOCIAL_MEDIA_POST
        }
    ]
    
    # Initialize AI classifier
    print("Initializing AI Content Classifier...")
    try:
        classifier = AIContentClassifier(
            model="phi3:mini",
            enable_ai=True,
            fallback_to_rules=True
        )
        print("✅ AI Classifier initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI Classifier: {e}")
        print("Falling back to rule-based classification only")
        classifier = AIContentClassifier(
            model="phi3:mini",
            enable_ai=False,
            fallback_to_rules=True
        )
    
    # Initialize specialized processor
    print("Initializing Specialized Content Processor...")
    processor = SpecializedContentProcessor()
    print("✅ Specialized Processor initialized successfully")
    
    # Test each case
    print("\n🔍 Testing Content Classification:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Expected: {test_case['expected_category'].value}")
        
        try:
            # Classify content
            analysis = classifier.classify_content(
                test_case['content'],
                {"title": test_case['name']},
                Path(f"test_{i}.md")
            )
            
            print(f"   Actual:   {analysis.category.value}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Strategy: {analysis.processing_strategy}")
            
            # Check if classification matches expectation
            if analysis.category == test_case['expected_category']:
                print("   ✅ Classification correct!")
            else:
                print("   ❌ Classification mismatch")
            
            # Process content with specialized processor
            result = processor.process_content(
                test_case['content'],
                analysis,
                {"title": test_case['name']},
                Path(f"test_{i}.md")
            )
            
            print(f"   Quality Score: {result.quality_score:.2f}")
            print(f"   Content Type: {result.content_type.value}")
            print(f"   Processing Notes: {', '.join(result.processing_notes[:2])}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test the integrated content processor
    print("\n🔧 Testing Integrated Content Processor:")
    print("-" * 50)
    
    try:
        content_processor = ContentProcessor(
            clean_html=True,
            preserve_metadata=True,
            extract_linked_content=False,
            enable_ai_classification=True
        )
        print("✅ Integrated Content Processor initialized successfully")
        
        # Test with a sample note
        test_note_path = Path("test_note.md")
        test_note_path.write_text(test_cases[0]["content"])
        
        try:
            note = content_processor.process_note(test_note_path)
            print(f"✅ Note processed successfully")
            print(f"   Title: {note.title}")
            print(f"   Content Type: {note.content_type.value}")
            print(f"   Content Length: {len(note.content)} chars")
            
            # Check if AI analysis metadata was added
            if hasattr(note, 'metadata') and note.metadata:
                if 'ai_analysis' in note.metadata:
                    ai_meta = note.metadata['ai_analysis']
                    print(f"   AI Category: {ai_meta.get('category', 'N/A')}")
                    print(f"   AI Confidence: {ai_meta.get('confidence', 'N/A')}")
                    print(f"   Processing Strategy: {ai_meta.get('processing_strategy', 'N/A')}")
                else:
                    print("   ⚠️  No AI analysis metadata found")
            
        except Exception as e:
            print(f"❌ Failed to process note: {e}")
        
        # Clean up test file
        test_note_path.unlink(missing_ok=True)
        
    except Exception as e:
        print(f"❌ Failed to initialize integrated processor: {e}")
    
    print("\n🎯 Test Summary:")
    print("=" * 50)
    print("The AI content classification system provides:")
    print("• Intelligent content type detection")
    print("• Specialized processing strategies")
    print("• Quality assessment and validation")
    print("• Fallback to rule-based classification")
    print("• Integration with existing content processing pipeline")
    
    print("\n🚀 To use in your curation workflow:")
    print("1. Set enable_ai_classification: true in config.yaml")
    print("2. The system will automatically classify and process content")
    print("3. Each note will get AI analysis metadata")
    print("4. Content will be processed using specialized strategies")


if __name__ == "__main__":
    test_ai_classification()
