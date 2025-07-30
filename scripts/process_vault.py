#!/usr/bin/env python3
"""
Normal Vault Processing Script for Obsidian Note Curator

This script processes ALL notes in your vault sequentially by folder structure,
preserving the thematic organization of your knowledge base.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from note_curator.core.curator import NoteCurator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def main():
    """Process the entire vault sequentially by folder structure."""
    console.print(Panel.fit(
        Text("📚 Obsidian Note Curator - Full Vault Processing", style="bold blue"),
        subtitle="Processing ALL notes sequentially by folder structure",
        box=box.ROUNDED
    ))
    
    try:
        # Initialize the curator
        console.print("\n[yellow]Initializing Note Curator...[/yellow]")
        curator = NoteCurator()
        
        # Process ALL notes sequentially (no sampling)
        console.print("\n[green]🔄 NORMAL MODE: Processing entire vault...[/green]")
        console.print("[cyan]Notes will be processed sequentially by folder structure[/cyan]")
        console.print("[cyan]This preserves your thematic organization and processes all content[/cyan]")
        console.print("[cyan]Folder context will be considered in classification decisions[/cyan]")
        
        # Process all notes (no sample_size parameter = process all)
        results = curator.analyze_vault()
        
        console.print(f"\n[green]✅ Processing complete![/green]")
        console.print(f"Processed {results.total_notes_processed} notes from your entire vault")
        
        # Show processing summary
        console.print("\n[bold]📊 Processing Summary:[/bold]")
        console.print(f"  • Total notes processed: {results.total_notes_processed}")
        console.print(f"  • High-value notes: {results.high_value_notes}")
        console.print(f"  • Medium-value notes: {results.medium_value_notes}")
        console.print(f"  • Low-value notes: {results.low_value_notes}")
        
        # Show action distribution
        console.print(f"\n[bold]🎯 Curation Actions:[/bold]")
        for action, count in results.notes_by_action.items():
            if count > 0:
                percentage = (count / results.total_notes_processed) * 100
                console.print(f"  • {action.value.title()}: {count} notes ({percentage:.1f}%)")
        
        # Show pillar distribution
        console.print(f"\n[bold]🏛️ Primary Pillars:[/bold]")
        for pillar, count in results.notes_by_pillar.items():
            if count > 0:
                percentage = (count / results.total_notes_processed) * 100
                console.print(f"  • {pillar.value.replace('_', ' ').title()}: {count} notes ({percentage:.1f}%)")
        
        console.print(f"\n📄 Results saved to: results/")
        console.print("\n💡 Next steps:")
        console.print("1. Review the generated reports in the results/ directory")
        console.print("2. Check the curation actions file for specific recommendations")
        console.print("3. Use the review script to validate specific classifications")
        console.print("4. Consider running the test script first for validation")
        
    except Exception as e:
        console.print(f"[red]❌ Error during processing: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 