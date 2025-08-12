"""Command-line interface for Obsidian Curator."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from .core import ObsidianCurator
from .models import CurationConfig, CurationStats


console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable verbose logging
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger with appropriate level
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )


def validate_paths(input_path: Path, output_path: Path) -> None:
    """Validate input and output paths.
    
    Args:
        input_path: Input vault path
        output_path: Output vault path
        
    Raises:
        click.ClickException: If paths are invalid
    """
    if not input_path.exists():
        raise click.ClickException(f"Input path does not exist: {input_path}")
    
    if not input_path.is_dir():
        raise click.ClickException(f"Input path is not a directory: {input_path}")
    
    if output_path.exists() and any(output_path.iterdir()):
        if not click.confirm(f"Output directory {output_path} is not empty. Continue?"):
            raise click.ClickException("Operation cancelled by user")


def display_config(config: CurationConfig) -> None:
    """Display configuration in a nice table.
    
    Args:
        config: Curation configuration
    """
    table = Table(title="Curation Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("AI Model", config.ai_model)
    table.add_row("Reasoning Level", config.reasoning_level.upper())
    table.add_row("Quality Threshold", f"{config.quality_threshold:.2f}")
    table.add_row("Relevance Threshold", f"{config.relevance_threshold:.2f}")
    table.add_row("Max Tokens", str(config.max_tokens))
    table.add_row("Sample Size", str(config.sample_size) if config.sample_size else "All notes")
    table.add_row("Target Themes", ", ".join(config.target_themes) if config.target_themes else "All themes")
    table.add_row("Clean HTML", "Yes" if config.clean_html else "No")
    table.add_row("Preserve Metadata", "Yes" if config.preserve_metadata else "No")
    
    console.print(table)


def display_stats(stats: CurationStats) -> None:
    """Display curation statistics.
    
    Args:
        stats: Curation statistics
    """
    # Summary panel
    summary_text = f"""
[bold green]Total Notes:[/bold green] {stats.total_notes}
[bold blue]Curated:[/bold blue] {stats.curated_notes} ({stats.curation_rate:.1f}%)
[bold red]Rejected:[/bold red] {stats.rejected_notes}
[bold yellow]Processing Time:[/bold yellow] {stats.processing_time:.1f}s
"""
    
    console.print(Panel(summary_text, title="Curation Results", border_style="green"))
    
    # Theme distribution
    if stats.themes_distribution:
        theme_table = Table(title="Theme Distribution")
        theme_table.add_column("Theme", style="cyan")
        theme_table.add_column("Count", style="green")
        theme_table.add_column("Percentage", style="yellow")
        
        total_themed = sum(stats.themes_distribution.values())
        for theme, count in sorted(stats.themes_distribution.items()):
            percentage = (count / total_themed * 100) if total_themed > 0 else 0
            theme_table.add_row(theme.replace('_', ' ').title(), str(count), f"{percentage:.1f}%")
        
        console.print(theme_table)
    
    # Quality distribution
    if stats.quality_distribution:
        quality_table = Table(title="Quality Score Distribution")
        quality_table.add_column("Score Range", style="cyan")
        quality_table.add_column("Count", style="green")
        
        for range_name, count in stats.quality_distribution.items():
            quality_table.add_row(range_name, str(count))
        
        console.print(quality_table)


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Obsidian Curator - AI-powered curation system for Obsidian vaults."""
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.argument('output_path', type=click.Path(file_okay=False, dir_okay=True, path_type=Path))
@click.option('--model', default="gpt-oss:20b", help="Ollama model to use for analysis")
@click.option('--reasoning-level', default="low", type=click.Choice(['low', 'medium', 'high']), help="AI reasoning level")
@click.option('--quality-threshold', default=0.7, type=float, help="Minimum quality score for curation (0.0-1.0)")
@click.option('--relevance-threshold', default=0.6, type=float, help="Minimum relevance score for curation (0.0-1.0)")
@click.option('--max-tokens', default=2000, type=int, help="Maximum tokens for AI analysis")
@click.option('--sample-size', type=int, help="Number of notes to process (random sample for testing)")
@click.option('--target-themes', help="Comma-separated list of target themes to focus on")
@click.option('--no-clean-html', is_flag=True, help="Skip HTML cleaning")
@click.option('--no-preserve-metadata', is_flag=True, help="Don't preserve original metadata")
@click.option('--dry-run', is_flag=True, help="Show what would be done without doing it")
@click.option('--verbose', is_flag=True, help="Enable verbose logging")
def curate(input_path: Path, 
           output_path: Path,
           model: str,
           reasoning_level: str,
           quality_threshold: float,
           relevance_threshold: float,
           max_tokens: int,
           sample_size: Optional[int],
           target_themes: Optional[str],
           no_clean_html: bool,
           no_preserve_metadata: bool,
           dry_run: bool,
           verbose: bool) -> None:
    """Curate an Obsidian vault using AI analysis.
    
    INPUT_PATH: Path to the source Obsidian vault
    OUTPUT_PATH: Path for the curated output vault
    """
    # Setup logging
    setup_logging(verbose)
    
    try:
        # Validate paths
        if not dry_run:
            validate_paths(input_path, output_path)
        
        # Parse target themes
        target_themes_list = []
        if target_themes:
            target_themes_list = [theme.strip() for theme in target_themes.split(',')]
        
        # Create configuration
        config = CurationConfig(
            ai_model=model,
            reasoning_level=reasoning_level,
            quality_threshold=quality_threshold,
            relevance_threshold=relevance_threshold,
            max_tokens=max_tokens,
            sample_size=sample_size,
            target_themes=target_themes_list,
            preserve_metadata=not no_preserve_metadata,
            clean_html=not no_clean_html
        )
        
        # Display configuration
        console.print(f"\n[bold blue]Obsidian Curator[/bold blue] - Processing vault: [green]{input_path}[/green]")
        display_config(config)
        
        if dry_run:
            console.print(Panel("[yellow]DRY RUN MODE - No files will be modified[/yellow]", border_style="yellow"))
            
            # Initialize curator to validate configuration
            curator = ObsidianCurator(config)
            
            # Discover notes
            with console.status("[bold green]Discovering notes..."):
                notes = curator._discover_notes(input_path)
            
            console.print(f"\n[green]Found {len(notes)} notes in vault[/green]")
            
            if config.sample_size and len(notes) > config.sample_size:
                console.print(f"[yellow]Would process {config.sample_size} notes (sample mode)[/yellow]")
            else:
                console.print(f"[yellow]Would process all {len(notes)} notes[/yellow]")
            
            # Show some example notes
            if notes:
                console.print("\n[bold]Example notes that would be processed:[/bold]")
                for i, note in enumerate(notes[:5]):
                    console.print(f"  {i+1}. {note.title} ({note.content_type.value})")
                if len(notes) > 5:
                    console.print(f"  ... and {len(notes) - 5} more")
            
            return
        
        # Initialize curator
        curator = ObsidianCurator(config)
        
        # Run curation with progress tracking
        console.print(f"\n[bold green]Starting curation process...[/bold green]")
        
        stats = curator.curate_vault(input_path, output_path)
        
        # Display results
        console.print(f"\n[bold green]✓ Curation completed successfully![/bold green]")
        display_stats(stats)
        
        console.print(f"\n[bold blue]Curated vault saved to:[/bold blue] [green]{output_path}[/green]")
        console.print(f"[dim]Check the metadata folder for detailed logs and analysis[/dim]")
        
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.argument('vault_path', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--verbose', is_flag=True, help="Show detailed information")
def analyze(vault_path: Path, verbose: bool) -> None:
    """Analyze an Obsidian vault without curation.
    
    VAULT_PATH: Path to the Obsidian vault to analyze
    """
    setup_logging(verbose)
    
    try:
        console.print(f"\n[bold blue]Analyzing vault:[/bold blue] [green]{vault_path}[/green]")
        
        # Default config for analysis
        config = CurationConfig()
        curator = ObsidianCurator(config)
        
        with console.status("[bold green]Discovering notes..."):
            notes = curator._discover_notes(vault_path)
        
        if not notes:
            console.print("[red]No notes found in vault[/red]")
            return
        
        console.print(f"\n[green]Found {len(notes)} notes[/green]")
        
        # Analyze content types
        content_types = {}
        for note in notes:
            content_type = note.content_type.value
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        # Display content type distribution
        type_table = Table(title="Content Type Distribution")
        type_table.add_column("Content Type", style="cyan")
        type_table.add_column("Count", style="green")
        type_table.add_column("Percentage", style="yellow")
        
        for content_type, count in sorted(content_types.items()):
            percentage = (count / len(notes)) * 100
            type_table.add_row(content_type.replace('_', ' ').title(), str(count), f"{percentage:.1f}%")
        
        console.print(type_table)
        
        if verbose:
            # Show sample notes for each type
            for content_type in content_types:
                sample_notes = [n for n in notes if n.content_type.value == content_type][:3]
                if sample_notes:
                    console.print(f"\n[bold]{content_type.replace('_', ' ').title()} Examples:[/bold]")
                    for note in sample_notes:
                        console.print(f"  • {note.title}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise click.ClickException(str(e))


@cli.command()
def models() -> None:
    """List available Ollama models."""
    try:
        import ollama
        
        with console.status("[bold green]Fetching available models..."):
            models = ollama.list()
        
        if not models.get('models'):
            console.print("[red]No models found. Install models with: ollama pull <model-name>[/red]")
            return
        
        model_table = Table(title="Available Ollama Models")
        model_table.add_column("Name", style="cyan")
        model_table.add_column("Size", style="green")
        model_table.add_column("Modified", style="yellow")
        
        for model in models['models']:
            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            modified = model.get('modified_at', 'Unknown')
            
            # Format size
            size_str = f"{size / (1024**3):.1f} GB" if size else "Unknown"
            
            # Format date
            if modified != 'Unknown':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    modified = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            model_table.add_row(name, size_str, modified)
        
        console.print(model_table)
        
    except ImportError:
        console.print("[red]Ollama not available. Install with: pip install ollama[/red]")
    except Exception as e:
        console.print(f"[red]Failed to fetch models: {e}[/red]")


@cli.command()
@click.argument('config_path', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
def validate_config(config_path: Path) -> None:
    """Validate a configuration file.
    
    CONFIG_PATH: Path to the configuration file to validate
    """
    try:
        import json
        import yaml
        
        console.print(f"[bold blue]Validating configuration:[/bold blue] [green]{config_path}[/green]")
        
        # Try to load as JSON or YAML
        content = config_path.read_text()
        
        try:
            if config_path.suffix.lower() == '.json':
                config_data = json.loads(content)
            else:
                config_data = yaml.safe_load(content)
        except Exception as e:
            raise click.ClickException(f"Failed to parse configuration file: {e}")
        
        # Validate with Pydantic
        try:
            config = CurationConfig(**config_data)
            console.print("[green]✓ Configuration is valid[/green]")
            display_config(config)
        except Exception as e:
            raise click.ClickException(f"Configuration validation failed: {e}")
            
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise click.ClickException(str(e))


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()