#!/usr/bin/env python3
"""
Test script for the preprocessing module.

This script tests the preprocessing functionality with a sample of notes
to validate content cleaning, quality assessment, and filtering.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from note_curator.utils.preprocessor import ContentPreprocessor, PreprocessingResult
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

console = Console()


def load_config(config_path: Path = Path("config/vault_config.yaml")) -> dict:
    """Load vault configuration."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)


def find_sample_notes(vault_path: Path, sample_size: int = 50) -> List[Path]:
    """Find a sample of notes for testing."""
    config = load_config()
    
    # Create pathspec for file filtering
    include_patterns = config.get('vault', {}).get('include_patterns', ['*.md'])
    exclude_patterns = config.get('vault', {}).get('exclude_patterns', [])
    
    include_spec = PathSpec.from_lines(GitWildMatchPattern, include_patterns)
    exclude_spec = PathSpec.from_lines(GitWildMatchPattern, exclude_patterns)
    
    # Find all markdown files
    notes = []
    for file_path in vault_path.rglob('*'):
        if file_path.is_file():
            relative_path = file_path.relative_to(vault_path)
            
            if include_spec.match_file(str(relative_path)) and \
               not exclude_spec.match_file(str(relative_path)):
                notes.append(file_path)
    
    # Sample if requested
    if sample_size and len(notes) > sample_size:
        import random
        notes = random.sample(notes, sample_size)
    
    return notes


def load_notes_content(notes: List[Path]) -> List[Tuple[Path, str]]:
    """Load content for a list of notes."""
    notes_data = []
    
    for note_path in notes:
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            notes_data.append((note_path, content))
        except Exception as e:
            console.print(f"[red]Error loading {note_path}: {e}[/red]")
    
    return notes_data


def test_preprocessing(notes_data: List[Tuple[Path, str]]) -> List[PreprocessingResult]:
    """Test the preprocessing module with sample notes."""
    preprocessor = ContentPreprocessor()
    
    console.print("[yellow]Testing preprocessing module...[/yellow]")
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Preprocessing notes...", total=len(notes_data))
        
        for file_path, content in notes_data:
            try:
                result = preprocessor.preprocess_note(content, file_path)
                results.append(result)
                progress.update(task, advance=1)
            except Exception as e:
                console.print(f"[red]Error preprocessing {file_path}: {e}[/red]")
                progress.update(task, advance=1)
    
    return results


def display_preprocessing_results(results: List[PreprocessingResult]):
    """Display comprehensive preprocessing results."""
    if not results:
        console.print("[red]No results to display[/red]")
        return
    
    # Get statistics
    preprocessor = ContentPreprocessor()
    stats = preprocessor.get_preprocessing_stats(results)
    
    console.print(Panel.fit(
        Text("🧪 Preprocessing Test Results", style="bold blue"),
        subtitle=f"Tested {len(results)} notes"
    ))
    
    # Basic statistics
    console.print("\n[bold]📊 Processing Statistics:[/bold]")
    basic_table = Table()
    basic_table.add_column("Metric", style="cyan")
    basic_table.add_column("Value", style="magenta")
    
    basic_table.add_row("Total Notes", str(stats['total_notes']))
    basic_table.add_row("Processed Notes", str(stats['processed_notes']))
    basic_table.add_row("Rejected Notes", str(stats['rejected_notes']))
    basic_table.add_row("Processing Rate", f"{stats['processing_rate']:.1%}")
    
    console.print(basic_table)
    
    # Content type distribution
    console.print("\n[bold]📝 Content Types:[/bold]")
    type_table = Table()
    type_table.add_column("Content Type", style="cyan")
    type_table.add_column("Count", style="magenta")
    type_table.add_column("Percentage", style="green")
    
    total = stats['total_notes']
    for content_type, count in stats['content_types'].items():
        percentage = (count / total) * 100
        type_table.add_row(
            content_type.replace('_', ' ').title(),
            str(count),
            f"{percentage:.1f}%"
        )
    
    console.print(type_table)
    
    # Language distribution
    console.print("\n[bold]🌍 Languages:[/bold]")
    lang_table = Table()
    lang_table.add_column("Language", style="cyan")
    lang_table.add_column("Count", style="magenta")
    lang_table.add_column("Percentage", style="green")
    
    for language, count in stats['languages'].items():
        percentage = (count / total) * 100
        lang_table.add_row(
            language.title(),
            str(count),
            f"{percentage:.1f}%"
        )
    
    console.print(lang_table)
    
    # Quality score distribution
    console.print("\n[bold]🎯 Quality Scores:[/bold]")
    quality_table = Table()
    quality_table.add_column("Metric", style="cyan")
    quality_table.add_column("Value", style="magenta")
    
    quality_scores = stats['quality_scores']
    quality_table.add_row("Mean", f"{quality_scores['mean']:.3f}")
    quality_table.add_row("Median", f"{quality_scores['median']:.3f}")
    quality_table.add_row("Min", f"{quality_scores['min']:.3f}")
    quality_table.add_row("Max", f"{quality_scores['max']:.3f}")
    
    console.print(quality_table)
    
    # Word count distribution
    console.print("\n[bold]📏 Word Counts:[/bold]")
    word_table = Table()
    word_table.add_column("Metric", style="cyan")
    word_table.add_column("Value", style="magenta")
    
    word_counts = stats['word_counts']
    word_table.add_row("Mean", f"{word_counts['mean']:.0f}")
    word_table.add_row("Median", f"{word_counts['median']:.0f}")
    word_table.add_row("Min", str(word_counts['min']))
    word_table.add_row("Max", str(word_counts['max']))
    
    console.print(word_table)
    
    # Issues found
    console.print("\n[bold]⚠️  Issues Found:[/bold]")
    if stats['issues']:
        issue_table = Table()
        issue_table.add_column("Issue", style="cyan")
        issue_table.add_column("Count", style="magenta")
        issue_table.add_column("Percentage", style="red")
        
        for issue, count in stats['issues'].items():
            percentage = (count / total) * 100
            issue_table.add_row(
                issue.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(issue_table)
    else:
        console.print("[green]No issues found![/green]")
    
    # Sample results
    console.print("\n[bold]🔍 Sample Results:[/bold]")
    sample_table = Table()
    sample_table.add_column("File", style="cyan")
    sample_table.add_column("Type", style="magenta")
    sample_table.add_column("Language", style="green")
    sample_table.add_column("Quality", style="yellow")
    sample_table.add_column("Process", style="red")
    sample_table.add_column("Reason", style="blue")
    
    # Show first 10 results
    for result in results[:10]:
        sample_table.add_row(
            result.original_content[:30] + "..." if len(result.original_content) > 30 else result.original_content,
            result.content_type.value,
            result.language.value,
            f"{result.quality_score:.2f}",
            "✓" if result.should_process else "✗",
            result.processing_reason[:30] + "..." if len(result.processing_reason) > 30 else result.processing_reason
        )
    
    console.print(sample_table)


def save_test_results(results: List[PreprocessingResult], stats: dict):
    """Save test results to files."""
    output_dir = Path("results/preprocessing_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    detailed_results = []
    for result in results:
        detailed_results.append({
            'file_path': str(Path(result.original_content[:100])),  # Use first 100 chars as identifier
            'content_type': result.content_type.value,
            'language': result.language.value,
            'quality_score': result.quality_score,
            'word_count': result.word_count,
            'character_count': result.character_count,
            'structure_score': result.structure_score,
            'has_meaningful_content': result.has_meaningful_content,
            'issues': result.issues,
            'should_process': result.should_process,
            'processing_reason': result.processing_reason,
            'metadata': result.metadata
        })
    
    # Save detailed results
    detailed_file = output_dir / f"preprocessing_detailed_{timestamp}.json"
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, default=str)
    
    # Save statistics
    stats_file = output_dir / f"preprocessing_stats_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Test results saved![/green]")
    console.print(f"📄 Detailed results: {detailed_file}")
    console.print(f"📊 Statistics: {stats_file}")


def main():
    """Main test function."""
    console.print(Panel.fit(
        Text("🧪 Preprocessing Module Test", style="bold blue"),
        subtitle="Testing content cleaning, quality assessment, and filtering"
    ))
    
    try:
        # Load configuration
        config = load_config()
        vault_path = Path(config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[blue]Vault path: {vault_path}[/blue]")
        
        # Find sample notes
        sample_size = 50
        console.print(f"\n[yellow]Finding {sample_size} sample notes...[/yellow]")
        
        notes = find_sample_notes(vault_path, sample_size)
        console.print(f"Found {len(notes)} notes for testing")
        
        # Load note content
        console.print("\n[yellow]Loading note content...[/yellow]")
        notes_data = load_notes_content(notes)
        console.print(f"Loaded {len(notes_data)} notes")
        
        # Test preprocessing
        results = test_preprocessing(notes_data)
        
        # Display results
        display_preprocessing_results(results)
        
        # Save results
        preprocessor = ContentPreprocessor()
        stats = preprocessor.get_preprocessing_stats(results)
        save_test_results(results, stats)
        
        # Recommendations
        console.print("\n[bold]💡 Recommendations:[/bold]")
        
        if stats['processing_rate'] < 0.7:
            console.print("• Consider adjusting quality thresholds to increase processing rate")
        
        if stats['issues']:
            top_issues = sorted(stats['issues'].items(), key=lambda x: x[1], reverse=True)[:3]
            for issue, count in top_issues:
                console.print(f"• Address {issue.replace('_', ' ')} issue ({count} occurrences)")
        
        if stats['content_types'].get('evernote_clipping', 0) > 0:
            console.print("• Implement Evernote clipping cleanup")
        
        if stats['content_types'].get('template', 0) > 0:
            console.print("• Add template filtering")
        
        if stats['content_types'].get('draft', 0) > 0:
            console.print("• Add draft content filtering")
        
        console.print("• Integrate preprocessing into main classification pipeline")
        console.print("• Add preprocessing configuration options")
        console.print("• Implement preprocessing caching for performance")
        
    except Exception as e:
        console.print(f"[red]❌ Error during testing: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 