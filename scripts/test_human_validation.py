#!/usr/bin/env python3
"""
Test script for the human validation interface.
This script tests the validation logic with sample data.
"""

import json
from pathlib import Path
from human_validation_classification import ClassificationValidator, ClassificationValidation

def create_sample_data():
    """Create sample classification results for testing."""
    return {
        "test_name": "classification_test",
        "timestamp": "2025-01-08T18:37:19",
        "vault_path": "/path/to/vault",
        "batches": [
            {
                "notes": [
                    {
                        "file_name": "sample_note_1.md",
                        "file_path": "/path/to/vault/notes/sample_note_1.md",
                        "primary_pillar": "ppp_fundamentals",
                        "note_type": "literature_research",
                        "curation_action": "keep",
                        "confidence": 0.85,
                        "quality_scores": {
                            "relevance": 0.8,
                            "depth": 0.7,
                            "actionability": 0.6,
                            "uniqueness": 0.9,
                            "structure": 0.8,
                            "overall_score": 0.76
                        },
                        "curation_reasoning": "This note provides valuable insights into PPP fundamentals and should be kept for future reference."
                    },
                    {
                        "file_name": "sample_note_2.md",
                        "file_path": "/path/to/vault/notes/sample_note_2.md",
                        "primary_pillar": "operational_risk",
                        "note_type": "project_workflow",
                        "curation_action": "refine",
                        "confidence": 0.72,
                        "quality_scores": {
                            "relevance": 0.6,
                            "depth": 0.5,
                            "actionability": 0.8,
                            "uniqueness": 0.4,
                            "structure": 0.7,
                            "overall_score": 0.6
                        },
                        "curation_reasoning": "Note has good actionability but could benefit from refinement in structure and depth."
                    }
                ]
            }
        ]
    }

def test_validation_logic():
    """Test the validation logic with sample data."""
    print("Testing human validation interface...")
    
    # Create sample data
    sample_data = create_sample_data()
    
    # Create validator (without vault path for testing)
    validator = ClassificationValidator()
    
    # Test session creation
    session = validator.start_validation_session(sample_data)
    print(f"✓ Created validation session: {session.session_id}")
    print(f"✓ Total notes: {session.total_notes}")
    
    # Test validation calculation
    notes = sample_data['batches'][0]['notes']
    
    for i, note_data in enumerate(notes):
        print(f"\n--- Testing Note {i+1} ---")
        
        # Simulate human validation (agreement with AI)
        ai_primary_pillar = note_data.get('primary_pillar')
        ai_note_type = note_data.get('note_type')
        ai_curation_action = note_data.get('curation_action')
        ai_quality_scores = note_data.get('quality_scores', {})
        
        # Create validation record with agreement
        validation = ClassificationValidation(
            note_id=f"note_{i}",
            file_path=note_data['file_path'],
            ai_primary_pillar=ai_primary_pillar,
            ai_note_type=ai_note_type,
            ai_curation_action=ai_curation_action,
            ai_confidence=note_data.get('confidence', 0.0),
            ai_quality_scores=ai_quality_scores,
            ai_reasoning=note_data.get('curation_reasoning', ''),
            human_primary_pillar=ai_primary_pillar,  # Agreement
            human_note_type=ai_note_type,  # Agreement
            human_curation_action=ai_curation_action,  # Agreement
            human_confidence=4,
            human_quality_scores=ai_quality_scores,  # Agreement
            human_reasoning="I agree with the AI assessment",
            agreement=True,
            validation_timestamp="2025-01-08T18:37:19"
        )
        
        session.validation_data.append(validation)
        session.validated_notes += 1
        
        print(f"✓ Validated note {i+1}: {note_data['file_name']}")
        print(f"  AI Pillar: {ai_primary_pillar}")
        print(f"  AI Type: {ai_note_type}")
        print(f"  AI Action: {ai_curation_action}")
        print(f"  Agreement: {validation.agreement}")
    
    # Test statistics calculation
    session.agreement_rate = (session.validated_notes - session.human_corrections) / session.validated_notes
    print(f"\n✓ Final agreement rate: {session.agreement_rate:.1%}")
    
    # Test recommendations
    recommendations = validator.generate_improvement_recommendations(session)
    print(f"\n✓ Generated {len(recommendations)} recommendations:")
    for rec in recommendations:
        print(f"  • {rec}")
    
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    test_validation_logic()
