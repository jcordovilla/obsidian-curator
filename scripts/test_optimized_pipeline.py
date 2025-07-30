#!/usr/bin/env python3
"""
Test script for the optimized pipeline with Evernote cleaning and LLM optimizations.

This script tests the complete improved pipeline including:
1. Evernote clipping cleanup
2. Preprocessing optimizations
3. LLM pipeline improvements
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

from note_curator.utils.evernote_cleaner import EvernoteClippingCleaner
from note_curator.utils.preprocessor import ContentPreprocessor
from note_curator.models.llm_manager import LLMManager
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


def find_sample_notes(vault_path: Path, sample_size: int = 10) -> List[Path]:
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


def test_evernote_cleaning(notes_data: List[Tuple[Path, str]]) -> dict:
    """Test Evernote clipping cleaning."""
    console.print("\n[bold blue]🧹 Testing Evernote Clipping Cleaner[/bold blue]")
    
    cleaner = EvernoteClippingCleaner()
    
    start_time = time.time()
    results = cleaner.batch_clean_clippings(notes_data)
    cleaning_time = time.time() - start_time
    
    # Get statistics
    stats = cleaner.get_cleaning_stats(results)
    stats['cleaning_time'] = cleaning_time
    stats['time_per_note'] = cleaning_time / len(results) if results else 0
    
    return {
        'results': results,
        'stats': stats
    }


def test_preprocessing(notes_data: List[Tuple[Path, str]]) -> dict:
    """Test preprocessing module."""
    console.print("\n[bold blue]🔍 Testing Preprocessing Module[/bold blue]")
    
    preprocessor = ContentPreprocessor()
    
    start_time = time.time()
    results = preprocessor.batch_preprocess(notes_data)
    preprocessing_time = time.time() - start_time
    
    # Get statistics
    stats = preprocessor.get_preprocessing_stats(results)
    stats['preprocessing_time'] = preprocessing_time
    stats['time_per_note'] = preprocessing_time / len(results) if results else 0
    
    return {
        'results': results,
        'stats': stats
    }


def test_llm_pipeline(notes_data: List[Tuple[Path, str]]) -> dict:
    """Test LLM pipeline optimizations."""
    console.print("\n[bold blue]🤖 Testing LLM Pipeline[/bold blue]")
    
    llm_manager = LLMManager()
    
    # Test with a subset to avoid long processing times
    test_notes = notes_data[:3]  # Only test first 3 notes
    
    start_time = time.time()
    results = []
    
    for file_path, content in test_notes:
        try:
            # Use the optimized combined analysis
            result = llm_manager.analyze_and_classify_note(content, file_path)
            results.append({
                'file_path': str(file_path),
                'result': result
            })
        except Exception as e:
            console.print(f"[red]Error processing {file_path}: {e}[/red]")
            results.append({
                'file_path': str(file_path),
                'error': str(e)
            })
    
    llm_time = time.time() - start_time
    
    return {
        'results': results,
        'llm_time': llm_time,
        'time_per_note': llm_time / len(test_notes) if test_notes else 0,
        'notes_processed': len(test_notes)
    }


def display_optimization_results(evernote_results: dict, preprocessing_results: dict, llm_results: dict):
    """Display comprehensive optimization results."""
    console.print(Panel.fit(
        Text("🚀 Optimized Pipeline Test Results", style="bold blue"),
        subtitle="Evernote Cleaning + Preprocessing + LLM Optimizations"
    ))
    
    # Evernote cleaning results
    evernote_stats = evernote_results['stats']
    console.print("\n[bold]🧹 Evernote Cleaning Results:[/bold]")
    evernote_table = Table()
    evernote_table.add_column("Metric", style="cyan")
    evernote_table.add_column("Value", style="magenta")
    
    evernote_table.add_row("Total Notes", str(evernote_stats['total_notes']))
    evernote_table.add_row("Evernote Clippings", str(evernote_stats['evernote_clippings']))
    evernote_table.add_row("Clipping Percentage", f"{evernote_stats['clipping_percentage']:.1%}")
    evernote_table.add_row("Average Reduction", f"{evernote_stats['average_reduction_ratio']:.1%}")
    evernote_table.add_row("Total Bytes Saved", f"{evernote_stats['total_bytes_saved']:,}")
    evernote_table.add_row("Cleaning Time", f"{evernote_stats['cleaning_time']:.2f}s")
    evernote_table.add_row("Time per Note", f"{evernote_stats['time_per_note']:.3f}s")
    
    console.print(evernote_table)
    
    # Preprocessing results
    pre_stats = preprocessing_results['stats']
    console.print("\n[bold]🔍 Preprocessing Results:[/bold]")
    pre_table = Table()
    pre_table.add_column("Metric", style="cyan")
    pre_table.add_column("Value", style="magenta")
    
    pre_table.add_row("Total Notes", str(pre_stats['total_notes']))
    pre_table.add_row("Processed Notes", str(pre_stats['processed_notes']))
    pre_table.add_row("Rejected Notes", str(pre_stats['rejected_notes']))
    pre_table.add_row("Processing Rate", f"{pre_stats['processing_rate']:.1%}")
    pre_table.add_row("Average Quality Score", f"{pre_stats['quality_scores']['mean']:.3f}")
    pre_table.add_row("Preprocessing Time", f"{pre_stats['preprocessing_time']:.2f}s")
    pre_table.add_row("Time per Note", f"{pre_stats['time_per_note']:.3f}s")
    
    console.print(pre_table)
    
    # LLM results
    console.print("\n[bold]🤖 LLM Pipeline Results:[/bold]")
    llm_table = Table()
    llm_table.add_column("Metric", style="cyan")
    llm_table.add_column("Value", style="magenta")
    
    llm_table.add_row("Notes Processed", str(llm_results['notes_processed']))
    llm_table.add_row("LLM Processing Time", f"{llm_results['llm_time']:.2f}s")
    llm_table.add_row("Time per Note", f"{llm_results['time_per_note']:.2f}s")
    
    console.print(llm_table)
    
    # Performance summary
    console.print("\n[bold]📊 Performance Summary:[/bold]")
    summary_table = Table()
    summary_table.add_column("Stage", style="cyan")
    summary_table.add_column("Time per Note", style="magenta")
    summary_table.add_column("Total Time", style="green")
    summary_table.add_column("Efficiency", style="yellow")
    
    total_time = evernote_stats['cleaning_time'] + pre_stats['preprocessing_time'] + llm_results['llm_time']
    total_notes = evernote_stats['total_notes']
    
    summary_table.add_row(
        "Evernote Cleaning",
        f"{evernote_stats['time_per_note']:.3f}s",
        f"{evernote_stats['cleaning_time']:.2f}s",
        f"{(evernote_stats['total_bytes_saved'] / total_time):.0f} bytes/s"
    )
    
    summary_table.add_row(
        "Preprocessing",
        f"{pre_stats['time_per_note']:.3f}s",
        f"{pre_stats['preprocessing_time']:.2f}s",
        f"{pre_stats['processing_rate']:.1%} success rate"
    )
    
    summary_table.add_row(
        "LLM Analysis",
        f"{llm_results['time_per_note']:.2f}s",
        f"{llm_results['llm_time']:.2f}s",
        f"{llm_results['notes_processed']} notes processed"
    )
    
    summary_table.add_row(
        "Total Pipeline",
        f"{total_time / total_notes:.2f}s",
        f"{total_time:.2f}s",
        f"{total_notes} notes total"
    )
    
    console.print(summary_table)
    
    # Sample results
    console.print("\n[bold]🔍 Sample Results:[/bold]")
    sample_table = Table()
    sample_table.add_column("File", style="cyan")
    sample_table.add_column("Evernote", style="magenta")
    sample_table.add_column("Preprocessing", style="green")
    sample_table.add_column("LLM Result", style="yellow")
    
    # Get sample results from the processed data
    evernote_results_list = evernote_results.get('results', [])
    pre_results_list = preprocessing_results.get('results', [])
    llm_results_list = llm_results.get('results', [])
    
    for i in range(min(5, len(evernote_results_list))):
        if i < len(evernote_results_list):
            evernote_result = evernote_results_list[i]
            evernote_status = "✓" if evernote_result.is_evernote_clipping else "✗"
        else:
            evernote_status = "N/A"
            
        if i < len(pre_results_list):
            pre_result = pre_results_list[i]
            pre_status = "✓" if pre_result.should_process else "✗"
        else:
            pre_status = "N/A"
        
        llm_status = "N/A"
        if i < len(llm_results_list):
            llm_result = llm_results_list[i]
            if 'result' in llm_result:
                llm_status = llm_result['result'].get('curation_action', 'unknown')
            else:
                llm_status = "Error"
        
        # Get filename from the result data if available
        filename = f"Note {i+1}"
        if i < len(evernote_results_list) and hasattr(evernote_result, 'file_path'):
            filename = evernote_result.file_path.name[:30] + "..." if len(evernote_result.file_path.name) > 30 else evernote_result.file_path.name
        
        sample_table.add_row(
            filename,
            evernote_status,
            pre_status,
            llm_status
        )
    
    console.print(sample_table)


def save_optimization_results(evernote_results: dict, preprocessing_results: dict, llm_results: dict):
    """Save comprehensive optimization results."""
    output_dir = Path("results/optimization_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save Evernote cleaning results
    evernote_file = output_dir / f"evernote_cleaning_{timestamp}.json"
    with open(evernote_file, 'w', encoding='utf-8') as f:
        json.dump(evernote_results['stats'], f, indent=2, default=str)
    
    # Save preprocessing results
    pre_file = output_dir / f"preprocessing_{timestamp}.json"
    with open(pre_file, 'w', encoding='utf-8') as f:
        json.dump(preprocessing_results['stats'], f, indent=2, default=str)
    
    # Save LLM results
    llm_file = output_dir / f"llm_pipeline_{timestamp}.json"
    with open(llm_file, 'w', encoding='utf-8') as f:
        json.dump({
            'llm_time': llm_results['llm_time'],
            'time_per_note': llm_results['time_per_note'],
            'notes_processed': llm_results['notes_processed'],
            'results': llm_results['results']
        }, f, indent=2, default=str)
    
    # Save combined summary
    summary_file = output_dir / f"optimization_summary_{timestamp}.json"
    summary_data = {
        'timestamp': timestamp,
        'evernote_cleaning': evernote_results['stats'],
        'preprocessing': preprocessing_results['stats'],
        'llm_pipeline': {
            'llm_time': llm_results['llm_time'],
            'time_per_note': llm_results['time_per_note'],
            'notes_processed': llm_results['notes_processed']
        },
        'total_performance': {
            'total_time': evernote_results['stats']['cleaning_time'] + 
                         preprocessing_results['stats']['preprocessing_time'] + 
                         llm_results['llm_time'],
            'total_notes': evernote_results['stats']['total_notes'],
            'average_time_per_note': (evernote_results['stats']['cleaning_time'] + 
                                     preprocessing_results['stats']['preprocessing_time'] + 
                                     llm_results['llm_time']) / evernote_results['stats']['total_notes']
        }
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Optimization test results saved![/green]")
    console.print(f"📄 Evernote cleaning: {evernote_file}")
    console.print(f"📄 Preprocessing: {pre_file}")
    console.print(f"📄 LLM pipeline: {llm_file}")
    console.print(f"📄 Summary: {summary_file}")


def main():
    """Main test function."""
    console.print(Panel.fit(
        Text("🚀 Optimized Pipeline Test", style="bold blue"),
        subtitle="Testing Evernote cleaning, preprocessing, and LLM optimizations"
    ))
    
    try:
        # Load configuration
        config = load_config()
        vault_path = Path(config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[blue]Vault path: {vault_path}[/blue]")
        
        # Find sample notes
        sample_size = 10  # Small sample for quick testing
        console.print(f"\n[yellow]Finding {sample_size} sample notes...[/yellow]")
        
        notes = find_sample_notes(vault_path, sample_size)
        console.print(f"Found {len(notes)} notes for testing")
        
        # Load note content
        console.print("\n[yellow]Loading note content...[/yellow]")
        notes_data = load_notes_content(notes)
        console.print(f"Loaded {len(notes_data)} notes")
        
        # Test Evernote cleaning
        evernote_results = test_evernote_cleaning(notes_data)
        
        # Test preprocessing
        preprocessing_results = test_preprocessing(notes_data)
        
        # Test LLM pipeline
        llm_results = test_llm_pipeline(notes_data)
        
        # Display results
        display_optimization_results(evernote_results, preprocessing_results, llm_results)
        
        # Save results
        save_optimization_results(evernote_results, preprocessing_results, llm_results)
        
        # Performance analysis
        console.print("\n[bold]📈 Performance Analysis:[/bold]")
        
        total_time = (evernote_results['stats']['cleaning_time'] + 
                     preprocessing_results['stats']['preprocessing_time'] + 
                     llm_results['llm_time'])
        
        avg_time_per_note = total_time / len(notes_data)
        
        console.print(f"[green]✅ Total pipeline time: {total_time:.2f}s[/green]")
        console.print(f"[green]✅ Average time per note: {avg_time_per_note:.2f}s[/green]")
        
        # Evernote cleaning impact
        if evernote_results['stats']['evernote_clippings'] > 0:
            reduction = evernote_results['stats']['average_reduction_ratio']
            bytes_saved = evernote_results['stats']['total_bytes_saved']
            console.print(f"[green]✅ Evernote cleaning: {reduction:.1%} average reduction, {bytes_saved:,} bytes saved[/green]")
        
        # Preprocessing impact
        processing_rate = preprocessing_results['stats']['processing_rate']
        console.print(f"[green]✅ Preprocessing: {processing_rate:.1%} of notes passed quality checks[/green]")
        
        # Recommendations
        console.print("\n[bold]💡 Optimization Recommendations:[/bold]")
        
        if avg_time_per_note > 2.0:
            console.print("• Consider increasing batch sizes for better throughput")
            console.print("• Implement parallel processing for preprocessing")
        
        if evernote_results['stats']['clipping_percentage'] > 0.5:
            console.print("• Evernote cleaning is highly effective - consider expanding patterns")
        
        if preprocessing_results['stats']['processing_rate'] < 0.7:
            console.print("• Consider adjusting preprocessing thresholds")
        
        console.print("• Monitor performance over larger datasets")
        console.print("• Consider implementing caching for repeated content")
        
    except Exception as e:
        console.print(f"[red]❌ Error during testing: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 