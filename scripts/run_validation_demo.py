#!/usr/bin/env python3
"""
Demo script for the Human Validation Interface.

This script demonstrates how to use the validation interface
and shows the expected workflow.
"""

import json
from pathlib import Path
from human_validation_classification import ClassificationValidator

def create_demo_data():
    """Create demo classification results for demonstration."""
    return {
        "test_name": "demo_classification_test",
        "timestamp": "2025-01-08T18:00:00",
        "vault_path": "/demo/vault/path",
        "batches": [
            {
                "notes": [
                    {
                        "file_name": "demo_note_1.md",
                        "file_path": "/demo/vault/path/notes/demo_note_1.md",
                        "primary_pillar": "ppp_fundamentals",
                        "note_type": "literature_research",
                        "curation_action": "keep",
                        "confidence": 0.92,
                        "quality_scores": {
                            "relevance": 0.9,
                            "depth": 0.8,
                            "actionability": 0.7,
                            "uniqueness": 0.9,
                            "structure": 0.8,
                            "overall_score": 0.82
                        },
                        "curation_reasoning": "Excellent overview of PPP fundamentals with clear examples and actionable insights."
                    },
                    {
                        "file_name": "demo_note_2.md",
                        "file_path": "/demo/vault/path/notes/demo_note_2.md",
                        "primary_pillar": "digital_transformation",
                        "note_type": "technical_code",
                        "curation_action": "refine",
                        "confidence": 0.75,
                        "quality_scores": {
                            "relevance": 0.7,
                            "depth": 0.6,
                            "actionability": 0.8,
                            "uniqueness": 0.5,
                            "structure": 0.6,
                            "overall_score": 0.64
                        },
                        "curation_reasoning": "Good technical content but could benefit from better structure and documentation."
                    }
                ]
            }
        ]
    }

def run_demo():
    """Run a demonstration of the validation interface."""
    print("🚀 Human Validation Interface Demo")
    print("=" * 50)
    
    # Create demo data
    demo_data = create_demo_data()
    print("✓ Created demo classification data")
    
    # Create validator
    validator = ClassificationValidator()
    print("✓ Initialized validation interface")
    
    # Show available options
    print("\n📋 Available Classification Options:")
    print("Primary Pillars:", ", ".join(validator.available_pillars))
    print("Note Types:", ", ".join(validator.available_note_types))
    print("Curation Actions:", ", ".join(validator.available_actions))
    
    # Create a validation session
    session = validator.start_validation_session(demo_data)
    print(f"\n✓ Started validation session: {session.session_id}")
    print(f"  Total notes available: {session.total_notes}")
    
    # Simulate validation of first note
    print("\n🔍 Simulating validation of first note...")
    note_data = demo_data['batches'][0]['notes'][0]
    
    print(f"Note: {note_data['file_name']}")
    print(f"AI Classification:")
    print(f"  Pillar: {note_data['primary_pillar']}")
    print(f"  Type: {note_data['note_type']}")
    print(f"  Action: {note_data['curation_action']}")
    print(f"  Confidence: {note_data['confidence']:.2f}")
    
    # Simulate human agreement
    print(f"\nHuman Validation (Agreement):")
    print(f"  Pillar: {note_data['primary_pillar']} ✓")
    print(f"  Type: {note_data['note_type']} ✓")
    print(f"  Action: {note_data['curation_action']} ✓")
    print(f"  Result: Complete agreement")
    
    # Show what the interface would display
    print(f"\n📱 What the interface would show:")
    print(f"  • Note content (if vault path provided)")
    print(f"  • AI classification results")
    print(f"  • Interactive input prompts")
    print(f"  • Real-time agreement checking")
    print(f"  • Quality score comparison")
    
    # Demonstrate session summary
    print(f"\n📊 Session Summary Preview:")
    print(f"  Validated Notes: 1")
    print(f"  Agreement Rate: 100%")
    print(f"  Human Corrections: 0")
    
    # Show output structure
    print(f"\n💾 Output Structure:")
    print(f"  • Validation results saved to results/human_validation/")
    print(f"  • JSON format with detailed validation data")
    print(f"  • Session metadata and statistics")
    print(f"  • Individual note validation records")
    
    print(f"\n✅ Demo completed!")
    print(f"\nTo run the actual interface:")
    print(f"  python3 scripts/human_validation_classification.py")
    print(f"\nTo test the validation logic:")
    print(f"  python3 scripts/test_human_validation.py")

if __name__ == "__main__":
    run_demo()
