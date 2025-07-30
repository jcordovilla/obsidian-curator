#!/usr/bin/env python3
"""
Test script for the improved classification pipeline with preprocessing.

This script tests the complete pipeline including preprocessing, LLM analysis,
and classification to validate the improvements.
"""

import json
import sys
import time
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

from note_curator.core.curator import NoteCurator
from note_curator.utils.preprocessor import ContentPreprocessor
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


def find_sample_notes(vault_path: Path, sample_size: int = 20) -> List[Path]:
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


def test_preprocessing_only(notes: List[Path]) -> dict:
    """Test preprocessing module only."""
    console.print("\n[bold blue]🔍 Testing Preprocessing Module[/bold blue]")
    
    preprocessor = ContentPreprocessor()
    notes_data = []
    
    # Load note content
    for note_path in notes:
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            notes_data.append((note_path, content))
        except Exception as e:
            console.print(f"[red]Error loading {note_path}: {e}[/red]")
    
    # Test preprocessing
    start_time = time.time()
    results = preprocessor.batch_preprocess(notes_data)
    preprocessing_time = time.time() - start_time
    
    # Get statistics
    stats = preprocessor.get_preprocessing_stats(results)
    stats['processing_time'] = preprocessing_time
    stats['time_per_note'] = preprocessing_time / len(results) if results else 0
    
    return {
        'results': results,
        'stats': stats
    }


def test_full_pipeline(notes: List[Path]) -> dict:
    """Test the full classification pipeline."""
    console.print("\n[bold blue]🚀 Testing Full Classification Pipeline[/bold blue]")
    
    # Initialize curator
    curator = NoteCurator()
    
    # Test with sample notes
    start_time = time.time()
    
    # Create a temporary curator that only processes our sample notes
    class TestCurator(NoteCurator):
        def analyze_vault(self, sample_size=None):
            # Override to use our specific notes
            vault_path = Path(self.vault_config['vault']['path'])
            
            # Process only our sample notes
            batches = []
            max_notes_per_batch = self.vault_config['processing']['max_notes_per_batch']
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:
                main_task = progress.add_task(
                    f"Processing {len(notes)} notes...", 
                    total=len(notes)
                )
                
                for i in range(0, len(notes), max_notes_per_batch):
                    batch_notes = notes[i:i + max_notes_per_batch]
                    batch = self._process_batch(batch_notes, progress, main_task)
                    batches.append(batch)
            
            # Compile results
            results = self._compile_results(vault_path, batches)
            return results
    
    test_curator = TestCurator()
    results = test_curator.analyze_vault()
    
    pipeline_time = time.time() - start_time
    
    return {
        'results': results,
        'processing_time': pipeline_time,
        'time_per_note': pipeline_time / len(notes) if notes else 0
    }


def display_comparison_results(preprocessing_results: dict, pipeline_results: dict):
    """Display comparison of preprocessing vs full pipeline results."""
    console.print(Panel.fit(
        Text("📊 Pipeline Performance Comparison", style="bold blue"),
        subtitle="Preprocessing vs Full Pipeline"
    ))
    
    # Preprocessing statistics
    pre_stats = preprocessing_results['stats']
    pipe_stats = pipeline_results
    
    console.print("\n[bold]⚡ Performance Metrics:[/bold]")
    perf_table = Table()
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Preprocessing Only", style="magenta")
    perf_table.add_column("Full Pipeline", style="green")
    perf_table.add_column("Improvement", style="yellow")
    
    # Calculate improvements
    pre_time_per_note = pre_stats['time_per_note']
    pipe_time_per_note = pipe_stats['time_per_note']
    time_improvement = ((pre_time_per_note - pipe_time_per_note) / pre_time_per_note * 100) if pre_time_per_note > 0 else 0
    
    perf_table.add_row(
        "Time per Note",
        f"{pre_time_per_note:.3f}s",
        f"{pipe_time_per_note:.3f}s",
        f"{time_improvement:+.1f}%"
    )
    
    pre_total_time = pre_stats['processing_time']
    pipe_total_time = pipe_stats['processing_time']
    total_improvement = ((pre_total_time - pipe_total_time) / pre_total_time * 100) if pre_total_time > 0 else 0
    
    perf_table.add_row(
        "Total Time",
        f"{pre_total_time:.2f}s",
        f"{pipe_total_time:.2f}s",
        f"{total_improvement:+.1f}%"
    )
    
    console.print(perf_table)
    
    # Preprocessing statistics
    console.print("\n[bold]🔍 Preprocessing Results:[/bold]")
    pre_table = Table()
    pre_table.add_column("Metric", style="cyan")
    pre_table.add_column("Value", style="magenta")
    
    pre_table.add_row("Total Notes", str(pre_stats['total_notes']))
    pre_table.add_row("Processed Notes", str(pre_stats['processed_notes']))
    pre_table.add_row("Rejected Notes", str(pre_stats['rejected_notes']))
    pre_table.add_row("Processing Rate", f"{pre_stats['processing_rate']:.1%}")
    pre_table.add_row("Average Quality Score", f"{pre_stats['quality_scores']['mean']:.3f}")
    
    console.print(pre_table)
    
    # Content type distribution
    console.print("\n[bold]📝 Content Type Distribution:[/bold]")
    type_table = Table()
    type_table.add_column("Content Type", style="cyan")
    type_table.add_column("Count", style="magenta")
    type_table.add_column("Percentage", style="green")
    
    total = pre_stats['total_notes']
    for content_type, count in pre_stats['content_types'].items():
        percentage = (count / total) * 100
        type_table.add_row(
            content_type.replace('_', ' ').title(),
            str(count),
            f"{percentage:.1f}%"
        )
    
    console.print(type_table)
    
    # Issues found
    console.print("\n[bold]⚠️  Issues Found:[/bold]")
    if pre_stats['issues']:
        issue_table = Table()
        issue_table.add_column("Issue", style="cyan")
        issue_table.add_column("Count", style="magenta")
        issue_table.add_column("Percentage", style="red")
        
        for issue, count in pre_stats['issues'].items():
            percentage = (count / total) * 100
            issue_table.add_row(
                issue.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(issue_table)
    else:
        console.print("[green]No issues found![/green]")


def save_test_results(preprocessing_results: dict, pipeline_results: dict):
    """Save comprehensive test results."""
    output_dir = Path("results/pipeline_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save preprocessing results
    pre_file = output_dir / f"preprocessing_results_{timestamp}.json"
    with open(pre_file, 'w', encoding='utf-8') as f:
        json.dump(preprocessing_results['stats'], f, indent=2, default=str)
    
    # Save pipeline results
    pipe_file = output_dir / f"pipeline_results_{timestamp}.json"
    with open(pipe_file, 'w', encoding='utf-8') as f:
        json.dump({
            'processing_time': pipeline_results['processing_time'],
            'time_per_note': pipeline_results['time_per_note'],
            'total_notes': len(pipeline_results['results'].batches[0].notes) if pipeline_results['results'].batches else 0
        }, f, indent=2, default=str)
    
    # Save comparison summary
    comparison_file = output_dir / f"comparison_summary_{timestamp}.json"
    comparison_data = {
        'timestamp': timestamp,
        'preprocessing': preprocessing_results['stats'],
        'pipeline': {
            'processing_time': pipeline_results['processing_time'],
            'time_per_note': pipeline_results['time_per_note']
        },
        'improvements': {
            'time_per_note_improvement': ((preprocessing_results['stats']['time_per_note'] - pipeline_results['time_per_note']) / preprocessing_results['stats']['time_per_note'] * 100) if preprocessing_results['stats']['time_per_note'] > 0 else 0,
            'total_time_improvement': ((preprocessing_results['stats']['processing_time'] - pipeline_results['processing_time']) / preprocessing_results['stats']['processing_time'] * 100) if preprocessing_results['stats']['processing_time'] > 0 else 0
        }
    }
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Test results saved![/green]")
    console.print(f"📄 Preprocessing results: {pre_file}")
    console.print(f"📄 Pipeline results: {pipe_file}")
    console.print(f"📄 Comparison summary: {comparison_file}")


def main():
    """Main test function."""
    console.print(Panel.fit(
        Text("🧪 Improved Pipeline Test", style="bold blue"),
        subtitle="Testing preprocessing integration and performance improvements"
    ))
    
    try:
        # Load configuration
        config = load_config()
        vault_path = Path(config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[blue]Vault path: {vault_path}[/blue]")
        
        # Find sample notes
        sample_size = 20  # Smaller sample for faster testing
        console.print(f"\n[yellow]Finding {sample_size} sample notes...[/yellow]")
        
        notes = find_sample_notes(vault_path, sample_size)
        console.print(f"Found {len(notes)} notes for testing")
        
        # Test preprocessing only
        preprocessing_results = test_preprocessing_only(notes)
        
        # Test full pipeline
        pipeline_results = test_full_pipeline(notes)
        
        # Display comparison
        display_comparison_results(preprocessing_results, pipeline_results)
        
        # Save results
        save_test_results(preprocessing_results, pipeline_results)
        
        # Performance analysis
        console.print("\n[bold]📈 Performance Analysis:[/bold]")
        
        pre_time = preprocessing_results['stats']['time_per_note']
        pipe_time = pipeline_results['time_per_note']
        
        if pipe_time < pre_time:
            improvement = ((pre_time - pipe_time) / pre_time) * 100
            console.print(f"[green]✅ Pipeline is {improvement:.1f}% faster than preprocessing alone[/green]")
        else:
            degradation = ((pipe_time - pre_time) / pre_time) * 100
            console.print(f"[yellow]⚠️  Pipeline is {degradation:.1f}% slower than preprocessing alone[/yellow]")
        
        # Recommendations
        console.print("\n[bold]💡 Recommendations:[/bold]")
        
        pre_stats = preprocessing_results['stats']
        if pre_stats['processing_rate'] < 0.8:
            console.print("• Consider adjusting preprocessing thresholds to increase processing rate")
        
        if pre_stats['issues']:
            top_issues = sorted(pre_stats['issues'].items(), key=lambda x: x[1], reverse=True)[:3]
            for issue, count in top_issues:
                console.print(f"• Address {issue.replace('_', ' ')} issue ({count} occurrences)")
        
        if pre_stats['content_types'].get('evernote_clipping', 0) > 0:
            console.print("• Implement Evernote clipping cleanup in preprocessing")
        
        console.print("• Consider implementing preprocessing caching for repeated content")
        console.print("• Add preprocessing configuration options for different vaults")
        console.print("• Monitor preprocessing performance over time")
        
    except Exception as e:
        console.print(f"[red]❌ Error during testing: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 