#!/usr/bin/env python3
"""
Performance analysis script to identify bottlenecks in note processing.
"""

import sys
import time
import cProfile
import pstats
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from note_curator.core.curator import NoteCurator
from note_curator.models.llm_manager import LLMManager

console = Console()


def analyze_performance_bottlenecks():
    """Analyze performance bottlenecks in the note processing system."""
    console.print("[bold blue]Performance Analysis - Identifying Bottlenecks[/bold blue]")
    console.print("=" * 70)
    
    try:
        # Initialize components
        console.print("\n[yellow]Initializing components...[/yellow]")
        curator = NoteCurator()
        llm_manager = curator.llm_manager
        
        # Test with a small sample
        console.print("\n[yellow]Testing with 3 notes for detailed analysis...[/yellow]")
        
        # Profile the processing
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        results = curator.analyze_vault(sample_size=3)
        end_time = time.time()
        
        profiler.disable()
        
        total_time = end_time - start_time
        notes_processed = results.total_notes_processed
        time_per_note = total_time / notes_processed if notes_processed > 0 else 0
        
        # Display basic performance metrics
        display_basic_metrics(total_time, notes_processed, time_per_note)
        
        # Analyze profiler results
        analyze_profiler_results(profiler)
        
        # Analyze LLM manager performance
        analyze_llm_performance(llm_manager)
        
        # Provide recommendations
        provide_performance_recommendations(time_per_note)
        
    except Exception as e:
        console.print(f"[bold red]Error during performance analysis: {e}[/bold red]")
        return False
    
    return True


def display_basic_metrics(total_time, notes_processed, time_per_note):
    """Display basic performance metrics."""
    console.print("\n[bold green]Basic Performance Metrics[/bold green]")
    console.print("-" * 40)
    
    table = Table(title="Performance Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Processing Time", f"{total_time:.2f} seconds")
    table.add_row("Notes Processed", str(notes_processed))
    table.add_row("Time per Note", f"{time_per_note:.2f} seconds")
    table.add_row("Notes per Minute", f"{(notes_processed / total_time) * 60:.1f}")
    
    console.print(table)


def analyze_profiler_results(profiler):
    """Analyze profiler results to identify bottlenecks."""
    console.print("\n[bold green]Profiler Analysis - Top 10 Time Consumers[/bold green]")
    console.print("-" * 50)
    
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    
    # Create a table for the top functions
    table = Table(title="Top Time-Consuming Functions")
    table.add_column("Function", style="cyan")
    table.add_column("Calls", style="yellow")
    table.add_column("Time (s)", style="magenta")
    table.add_column("Time per Call (ms)", style="green")
    
    # Get the top 10 functions
    top_functions = []
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        if tt > 0:  # Only include functions that took time
            filename, line_num, func_name = func
            top_functions.append((func_name, nc, tt, ct))
    
    # Sort by total time and take top 10
    top_functions.sort(key=lambda x: x[2], reverse=True)
    
    for func_name, calls, total_time, cum_time in top_functions[:10]:
        time_per_call = (total_time / calls * 1000) if calls > 0 else 0
        table.add_row(
            func_name,
            str(calls),
            f"{total_time:.3f}",
            f"{time_per_call:.1f}"
        )
    
    console.print(table)


def analyze_llm_performance(llm_manager):
    """Analyze LLM manager performance."""
    console.print("\n[bold green]LLM Manager Performance Analysis[/bold green]")
    console.print("-" * 50)
    
    # Check which models are loaded
    table = Table(title="Model Status")
    table.add_column("Model Type", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Context Window", style="magenta")
    table.add_column("Threads", style="green")
    
    for model_type, model in llm_manager.models.items():
        if model:
            # Try to get model parameters
            try:
                context_window = getattr(model, 'n_ctx', 'Unknown')
                threads = getattr(model, 'n_threads', 'Unknown')
                status = "✅ Loaded"
            except:
                context_window = "Unknown"
                threads = "Unknown"
                status = "✅ Loaded"
        else:
            status = "❌ Failed"
            context_window = "N/A"
            threads = "N/A"
        
        table.add_row(model_type, status, str(context_window), str(threads))
    
    console.print(table)
    
    # Performance stats
    stats = llm_manager.get_performance_stats()
    console.print(f"\n[bold yellow]LLM Manager Stats:[/bold yellow]")
    console.print(f"  • Cache Size: {stats.get('cache_size', 0)}")
    console.print(f"  • Models Loaded: {stats.get('models_loaded', 0)}")
    console.print(f"  • Cache Hit Rate: {stats.get('cache_hit_rate', 0):.2%}")


def provide_performance_recommendations(time_per_note):
    """Provide performance improvement recommendations."""
    console.print("\n[bold green]Performance Recommendations[/bold green]")
    console.print("-" * 40)
    
    recommendations = []
    
    if time_per_note > 10:
        recommendations.append("🚨 **CRITICAL**: Processing time > 10s per note")
        recommendations.append("   - Implement true parallel processing")
        recommendations.append("   - Use smaller models for initial filtering")
        recommendations.append("   - Reduce prompt length and complexity")
    
    elif time_per_note > 5:
        recommendations.append("⚠️ **HIGH**: Processing time > 5s per note")
        recommendations.append("   - Consider using smaller models")
        recommendations.append("   - Implement caching for repeated content")
        recommendations.append("   - Optimize prompt engineering")
    
    elif time_per_note > 2:
        recommendations.append("📊 **MEDIUM**: Processing time > 2s per note")
        recommendations.append("   - Fine-tune model parameters")
        recommendations.append("   - Implement batch processing")
        recommendations.append("   - Consider model quantization")
    
    else:
        recommendations.append("✅ **GOOD**: Processing time < 2s per note")
        recommendations.append("   - Performance is acceptable")
        recommendations.append("   - Consider minor optimizations")
    
    # General recommendations
    recommendations.extend([
        "",
        "🔧 **General Optimizations**:",
        "   - Use Phi-2 model for quick filtering",
        "   - Implement content-based caching",
        "   - Reduce context window for simple tasks",
        "   - Use parallel processing for batch operations",
        "   - Optimize thread allocation for your system"
    ])
    
    for rec in recommendations:
        console.print(rec)


def main():
    """Main function."""
    success = analyze_performance_bottlenecks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 