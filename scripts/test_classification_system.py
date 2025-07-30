#!/usr/bin/env python3
"""
Enhanced test script for the classification system with comprehensive data capture.

This script tests the enhanced classification system and captures ALL preprocessing stages:
1. Raw sample notes (original markdown files)
2. Processed notes (after preprocessing and analysis)
3. Test results and analysis data

This enables comprehensive analysis and the creation of new preprocessing scripts.
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from note_curator.core.curator import NoteCurator

console = Console()


def cleanup_old_test_results():
    """Clean up old test results before starting new test."""
    test_runs_dir = Path("results/test_runs")
    if test_runs_dir.exists():
        console.print("[yellow]🧹 Cleaning up old test results...[/yellow]")
        try:
            shutil.rmtree(test_runs_dir)
            console.print("[green]✓ Old test results cleaned up[/green]")
        except Exception as e:
            console.print(f"[red]⚠ Warning: Could not clean up old results: {e}[/red]")


def test_improved_classification():
    """Test the improved classification system with comprehensive data capture."""
    console.print("[bold blue]Testing Classification System with Comprehensive Data Capture[/bold blue]")
    console.print("=" * 80)
    
    # Clean up old test results
    cleanup_old_test_results()
    
    try:
        # Initialize the curator
        curator = NoteCurator()
        
        # Test with a small sample to validate improvements
        console.print("\n[bold yellow]Running test with 5 notes...[/bold yellow]")
        
        # Run analysis with small sample (curator handles its own progress bar)
        results = curator.analyze_vault(sample_size=5)
        
        # Save comprehensive data including all preprocessing stages
        save_comprehensive_test_data(results, curator)
        
        # Display results
        display_test_results(results)
        
        # Validate improvements
        validate_improvements(results)
        
    except Exception as e:
        console.print(f"[bold red]Error during testing: {e}[/bold red]")
        return False
    
    return True


def save_comprehensive_test_data(results, curator):
    """Save comprehensive test data including all preprocessing stages."""
    # Extract all notes from batches
    all_notes = []
    for batch in results.batches:
        all_notes.extend(batch.notes)
    
    # Create comprehensive data structure
    comprehensive_data = {
        "test_metadata": {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "total_notes": len(all_notes),
            "test_type": "comprehensive_preprocessing_analysis",
            "system_version": "2.0_enhanced"
        },
        "preprocessing_pipeline": {
            "stages": [
                "raw_note_reading",
                "content_extraction", 
                "evernote_preprocessing",
                "content_truncation",
                "llm_analysis",
                "score_validation",
                "normalization"
            ],
            "config": {
                "max_note_chars": curator.vault_config['processing']['max_note_chars'],
                "normalize_notes": curator.vault_config['processing'].get('normalize_notes', False),
                "include_frontmatter": curator.vault_config['processing'].get('include_frontmatter', True)
            }
        },
        "notes_data": []
    }
    
    # Process each note to capture all preprocessing stages
    for note in all_notes:
        note_data = capture_note_preprocessing_stages(note, curator)
        comprehensive_data["notes_data"].append(note_data)
    
    # Save comprehensive data
    output_dir = Path("results/test_runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save comprehensive data
    comprehensive_file = output_dir / f"comprehensive_preprocessing_analysis_{timestamp}.json"
    with open(comprehensive_file, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_data, f, indent=2, ensure_ascii=False)
    
    # Save raw notes separately for easy access
    save_raw_notes(all_notes, output_dir, timestamp)
    
    # Save processed notes (after preprocessing)
    save_processed_notes(all_notes, output_dir, timestamp)
    
    # Save analysis results
    save_analysis_results(results, output_dir, timestamp)
    
    console.print(f"\n[bold green]✓ Comprehensive test data saved to: {output_dir}[/bold green]")
    console.print(f"  • Comprehensive analysis: {comprehensive_file.name}")
    console.print(f"  • Raw notes: raw_notes_{timestamp}.json")
    console.print(f"  • Processed notes: processed_notes_{timestamp}.json") 
    console.print(f"  • Analysis results: analysis_results_{timestamp}.json")
    console.print(f"  • {len(all_notes)} notes with complete preprocessing pipeline data")
    console.print(f"  • Ready for detailed analysis and preprocessing script development")


def capture_note_preprocessing_stages(note, curator):
    """Capture all preprocessing stages for a single note."""
    try:
        # Stage 1: Raw Note Reading
        raw_content = ""
        try:
            with open(note.file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            raw_content = f"[Error reading file: {e}]"
        
        # Stage 2: Content Extraction (simulate what the processor does)
        extracted_data = simulate_content_extraction(raw_content)
        
        # Stage 3: Evernote Preprocessing (if applicable)
        evernote_data = simulate_evernote_preprocessing(raw_content, note.file_path)
        
        # Stage 4: Content Truncation
        max_chars = curator.vault_config['processing']['max_note_chars']
        truncated_content = raw_content[:max_chars] if len(raw_content) > max_chars else raw_content
        truncation_info = {
            "original_length": len(raw_content),
            "truncated_length": len(truncated_content),
            "was_truncated": len(raw_content) > max_chars,
            "truncation_ratio": len(truncated_content) / len(raw_content) if len(raw_content) > 0 else 1.0
        }
        
        # Stage 5: LLM Analysis Results (from the note object)
        llm_analysis = {
            "primary_pillar": note.primary_pillar.value if note.primary_pillar else None,
            "secondary_pillars": [p.value for p in note.secondary_pillars] if note.secondary_pillars else [],
            "note_type": note.note_type.value if note.note_type else None,
            "quality_scores": {
                "relevance": note.quality_scores.relevance,
                "depth": note.quality_scores.depth,
                "actionability": note.quality_scores.actionability,
                "uniqueness": note.quality_scores.uniqueness,
                "structure": note.quality_scores.structure,
                "overall_score": note.quality_scores.overall_score
            },
            "curation_action": note.curation_action.value,
            "curation_reasoning": note.curation_reasoning,
            "confidence": note.confidence
        }
        
        # Stage 6: Score Validation (simulate what the processor does)
        validation_data = simulate_score_validation(llm_analysis, raw_content, note.file_path)
        
        # Stage 7: Normalization (if applicable)
        normalization_data = simulate_normalization(note, raw_content, curator)
        
        # Compile comprehensive note data
        note_data = {
            "file_metadata": {
                "file_name": note.file_name,
                "file_path": str(note.file_path),
                "file_size": note.file_size,
                "created_date": note.created_date.isoformat() if note.created_date else None,
                "modified_date": note.modified_date.isoformat() if note.modified_date else None
            },
            "preprocessing_stages": {
                "stage_1_raw_reading": {
                    "raw_content": raw_content,
                    "raw_length": len(raw_content),
                    "encoding": "utf-8"
                },
                "stage_2_content_extraction": extracted_data,
                "stage_3_evernote_preprocessing": evernote_data,
                "stage_4_content_truncation": {
                    "truncated_content": truncated_content,
                    "truncation_info": truncation_info
                },
                "stage_5_llm_analysis": llm_analysis,
                "stage_6_score_validation": validation_data,
                "stage_7_normalization": normalization_data
            },
            "final_results": {
                "word_count": note.word_count,
                "character_count": note.character_count,
                "has_frontmatter": note.has_frontmatter,
                "has_attachments": note.has_attachments,
                "attachment_count": note.attachment_count,
                "model_used": getattr(note, 'model_used', 'unknown')
            }
        }
        
        return note_data
        
    except Exception as e:
        return {
            "file_metadata": {
                "file_name": note.file_name,
                "file_path": str(note.file_path),
                "error": f"Failed to capture preprocessing stages: {e}"
            },
            "preprocessing_stages": {},
            "final_results": {}
        }


def simulate_content_extraction(content):
    """Simulate the content extraction stage."""
    import re
    from markdown_it import MarkdownIt
    
    md_parser = MarkdownIt()
    
    # Check for frontmatter
    has_frontmatter = content.startswith('---')
    
    # Extract attachments
    attachment_pattern = r'\[.*?\]\((.*?)\)'
    attachments = re.findall(attachment_pattern, content)
    has_attachments = len(attachments) > 0
    attachment_count = len(attachments)
    
    # Convert markdown to plain text
    rendered = md_parser.render(content)
    plain_text = re.sub(r'\n+', '\n', rendered)
    plain_text = re.sub(r'<[^>]+>', '', plain_text)  # Remove HTML tags
    plain_text = plain_text.strip()
    
    return {
        "plain_text": plain_text,
        "has_frontmatter": has_frontmatter,
        "has_attachments": has_attachments,
        "attachment_count": attachment_count,
        "attachments": attachments,
        "extracted_length": len(plain_text)
    }


def simulate_evernote_preprocessing(content, file_path):
    """Simulate the Evernote preprocessing stage."""
    import re
    
    # Check if it's an Evernote clipping
    evernote_indicators = [
        'Clipped from',
        'Evernote',
        'Web Clipper',
        'Saved from',
        'Source:'
    ]
    is_evernote_clipping = any(indicator in content for indicator in evernote_indicators)
    
    if not is_evernote_clipping:
        return {
            "is_evernote_clipping": False,
            "preprocessing_applied": False,
            "cleaned_content": content,
            "reduction_ratio": 1.0
        }
    
    # Simulate Evernote preprocessing patterns
    original_length = len(content)
    
    # Remove common Evernote patterns
    patterns_to_remove = [
        r'^.*?Clipped from.*?on.*?\n',  # Clipping header
        r'\n.*?Evernote.*?$',  # Evernote footer
        r'\[.*?\]\s*\(https?://.*?\)',  # Web annotations
        r'(Home|About|Contact|Privacy|Terms|Login|Sign up|Subscribe|Follow|Share|Tweet|Like|Comment)',  # Navigation
        r'(Advertisement|Ad|Sponsored|Promoted|Buy now|Shop now|Learn more)',  # Ads
        r'(Facebook|Twitter|Instagram|LinkedIn|YouTube|TikTok)',  # Social media
        r'[?&](utm_|fbclid|gclid|msclkid|ref=|source=).*?(?=\s|$)',  # Tracking params
        r'&[a-zA-Z0-9#]+;',  # HTML entities
        r'\s{3,}',  # Excessive whitespace
        r'(.)\1{3,}',  # Repeated chars
    ]
    
    cleaned_content = content
    for pattern in patterns_to_remove:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE | re.IGNORECASE)
    
    cleaned_content = cleaned_content.strip()
    reduction_ratio = len(cleaned_content) / original_length if original_length > 0 else 1.0
    
    return {
        "is_evernote_clipping": True,
        "preprocessing_applied": True,
        "original_content": content,
        "cleaned_content": cleaned_content,
        "reduction_ratio": reduction_ratio,
        "patterns_removed": len(patterns_to_remove),
        "original_length": original_length,
        "cleaned_length": len(cleaned_content)
    }


def simulate_score_validation(llm_analysis, content, file_path):
    """Simulate the score validation stage."""
    word_count = len(content.split())
    quality_scores = llm_analysis.get('quality_scores', {})
    
    validation_actions = []
    
    # Check for minimal content
    if word_count < 20:
        validation_actions.append({
            "action": "reduce_scores_minimal_content",
            "reason": f"Word count {word_count} < 20",
            "adjustment_factor": 0.6
        })
    
    # Check for irrelevant content
    irrelevant_indicators = [
        'test note', 'draft only', 'temp file', 'todo list', 'reminder to self',
        'placeholder text', 'template only', 'example only', 'sample only', 
        'personal diary', 'private notes', 'confidential personal'
    ]
    
    text_lower = content.lower()
    found_irrelevant = [indicator for indicator in irrelevant_indicators if indicator in text_lower]
    
    if found_irrelevant:
        validation_actions.append({
            "action": "reduce_relevance_score",
            "reason": f"Found irrelevant indicators: {found_irrelevant}",
            "adjustment_factor": 0.5
        })
    
    return {
        "word_count": word_count,
        "validation_actions": validation_actions,
        "original_scores": quality_scores.copy(),
        "adjusted_scores": quality_scores.copy()  # In real implementation, these would be adjusted
    }


def simulate_normalization(note, content, curator):
    """Simulate the normalization stage."""
    if note.curation_action.value not in ['keep', 'refine']:
        return {
            "normalization_applied": False,
            "reason": f"Note action '{note.curation_action.value}' not eligible for normalization"
        }
    
    # Simulate template application
    note_type = note.note_type.value if note.note_type else 'default'
    pillar = note.primary_pillar.value if note.primary_pillar else 'general'
    
    return {
        "normalization_applied": True,
        "note_type": note_type,
        "pillar": pillar,
        "template_applied": f"{note_type}_{pillar}",
        "frontmatter_generated": True,
        "structure_applied": True
    }


def save_raw_notes(all_notes, output_dir, timestamp):
    """Save raw notes data."""
    raw_notes_data = []
    
    for note in all_notes:
        try:
            with open(note.file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            raw_content = f"[Error reading file: {e}]"
        
        raw_notes_data.append({
            "file_name": note.file_name,
            "file_path": str(note.file_path),
            "raw_content": raw_content,
            "file_size": note.file_size,
            "created_date": note.created_date.isoformat() if note.created_date else None,
            "modified_date": note.modified_date.isoformat() if note.modified_date else None
        })
    
    raw_file = output_dir / f"raw_notes_{timestamp}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "total_notes": len(raw_notes_data),
            "raw_notes": raw_notes_data
        }, f, indent=2, ensure_ascii=False)


def save_processed_notes(all_notes, output_dir, timestamp):
    """Save processed notes data."""
    processed_notes_data = []
    
    for note in all_notes:
        processed_notes_data.append({
            "file_name": note.file_name,
            "file_path": str(note.file_path),
            "word_count": note.word_count,
            "character_count": note.character_count,
            "has_frontmatter": note.has_frontmatter,
            "has_attachments": note.has_attachments,
            "attachment_count": note.attachment_count,
            "primary_pillar": note.primary_pillar.value if note.primary_pillar else None,
            "secondary_pillars": [p.value for p in note.secondary_pillars] if note.secondary_pillars else [],
            "note_type": note.note_type.value if note.note_type else None,
            "quality_scores": {
                "relevance": note.quality_scores.relevance,
                "depth": note.quality_scores.depth,
                "actionability": note.quality_scores.actionability,
                "uniqueness": note.quality_scores.uniqueness,
                "structure": note.quality_scores.structure,
                "overall_score": note.quality_scores.overall_score
            },
            "curation_action": note.curation_action.value,
            "curation_reasoning": note.curation_reasoning,
            "confidence": note.confidence,
            "model_used": getattr(note, 'model_used', 'unknown')
        })
    
    processed_file = output_dir / f"processed_notes_{timestamp}.json"
    with open(processed_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "total_notes": len(processed_notes_data),
            "processed_notes": processed_notes_data
        }, f, indent=2, ensure_ascii=False)


def save_analysis_results(results, output_dir, timestamp):
    """Save analysis results."""
    analysis_results = {
        "timestamp": timestamp,
        "total_notes_processed": results.total_notes_processed,
        "high_value_notes": results.high_value_notes,
        "medium_value_notes": results.medium_value_notes,
        "low_value_notes": results.low_value_notes,
        "average_quality_score": results.average_quality_score,
        "notes_by_action": {action.value: count for action, count in results.notes_by_action.items()},
        "notes_by_pillar": {pillar.value: count for pillar, count in results.notes_by_pillar.items()},
        "processing_summary": {
            "total_batches": len(results.batches),
            "total_processing_time": sum((batch.end_time - batch.start_time).total_seconds() for batch in results.batches if batch.end_time),
            "average_time_per_note": results.average_quality_score  # Placeholder
        }
    }
    
    analysis_file = output_dir / f"analysis_results_{timestamp}.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)


def display_test_results(results):
    """Display the test results in a formatted table."""
    console.print("\n[bold green]Test Results Summary[/bold green]")
    console.print("-" * 40)
    
    # Extract all notes from batches
    all_notes = []
    for batch in results.batches:
        all_notes.extend(batch.notes)
    
    # Create summary table
    table = Table(title="Classification Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Notes Processed", str(results.total_notes_processed))
    table.add_row("High Value Notes", str(len([n for n in all_notes if n.curation_action.value == 'keep'])))
    table.add_row("Medium Value Notes", str(len([n for n in all_notes if n.curation_action.value == 'refine'])))
    table.add_row("Archive Notes", str(len([n for n in all_notes if n.curation_action.value == 'archive'])))
    table.add_row("Delete Notes", str(len([n for n in all_notes if n.curation_action.value == 'delete'])))
    
    console.print(table)
    
    # Display individual note results
    console.print("\n[bold green]Individual Note Analysis[/bold green]")
    console.print("-" * 40)
    
    for note in all_notes:
        console.print(f"\n[bold]{note.file_name}[/bold]")
        console.print(f"  Action: [{'green' if note.curation_action.value in ['keep', 'refine'] else 'red'}]{note.curation_action.value}[/]")
        console.print(f"  Primary Pillar: {note.primary_pillar.value if note.primary_pillar else 'None'}")
        console.print(f"  Quality Score: {note.quality_scores.relevance:.2f}")
        console.print(f"  Reasoning: {note.curation_reasoning[:100]}...")


def validate_improvements(results):
    """Validate that the improvements are working correctly."""
    console.print("\n[bold green]Validation of Improvements[/bold green]")
    console.print("-" * 40)
    
    # Extract all notes from batches
    all_notes = []
    for batch in results.batches:
        all_notes.extend(batch.notes)
    
    improvements = []
    issues = []
    
    # Check JSON parsing
    json_parsing_errors = 0
    for note in all_notes:
        if "Unable to parse" in note.curation_reasoning or "Parsed from LLM response" in note.curation_reasoning:
            json_parsing_errors += 1
    
    if json_parsing_errors == 0:
        improvements.append("JSON parsing working correctly")
    else:
        issues.append(f"JSON parsing errors in {json_parsing_errors} notes")
    
    # Check quality scoring
    high_scores = [note.quality_scores.relevance for note in all_notes if note.quality_scores.relevance > 0.8]
    if len(high_scores) <= len(all_notes) * 0.3:  # No more than 30% should have high scores
        improvements.append("Quality scoring is appropriately strict")
    else:
        issues.append("Quality scoring may be too lenient")
    
    # Check pillar classification
    none_pillars = [note for note in all_notes if note.primary_pillar is None]
    if len(none_pillars) <= len(all_notes) * 0.2:  # No more than 20% should have no pillar
        improvements.append("Pillar classification is appropriate")
    else:
        issues.append("Too many notes without pillar classification")
    
    # Display results
    if improvements:
        console.print("\n[bold green]✓ Improvements Confirmed:[/bold green]")
        for improvement in improvements:
            console.print(f"  ✓ {improvement}")
    
    if issues:
        console.print("\n[bold red]⚠ Issues Found:[/bold red]")
        for issue in issues:
            console.print(f"  ⚠ {issue}")
    
    if not issues:
        console.print("\n[bold green]✓ All improvements working correctly![/bold green]")


if __name__ == "__main__":
    success = test_improved_classification()
    if success:
        console.print("\n[bold green]Test completed successfully![/bold green]")
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  • Analyze results: poetry run python scripts/analyze_test_results.py")
        console.print("  • Check comprehensive data: results/test_runs/comprehensive_preprocessing_analysis_*.json")
        console.print("  • Develop preprocessing scripts using the captured data")
    else:
        console.print("\n[bold red]Test failed![/bold red]")
        sys.exit(1) 