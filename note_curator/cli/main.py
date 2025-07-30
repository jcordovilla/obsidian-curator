"""Main CLI interface for the note curator."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from ..core.curator import NoteCurator

console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-dir', type=click.Path(exists=True, file_okay=False), 
              default='config', help='Configuration directory')
@click.pass_context
def cli(ctx, verbose: bool, config_dir: str):
    """Obsidian Note Curator - AI-powered note classification system."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = Path(config_dir)


@cli.command()
@click.option('--sample-size', '-s', type=int, help='Number of notes to sample')
@click.option('--vault-path', type=click.Path(exists=True, file_okay=False), 
              help='Override vault path from config')
@click.pass_context
def analyze(ctx, sample_size: Optional[int], vault_path: Optional[str]):
    """Analyze notes in the vault and generate classification report."""
    try:
        config_dir = ctx.obj['config_dir']
        
        console.print("[bold blue]Obsidian Note Curator[/bold blue]")
        console.print("Initializing curator...")
        
        curator = NoteCurator(config_dir)
        
        if vault_path:
            # Update vault path in config
            curator.vault_config['vault']['path'] = vault_path
            console.print(f"Using vault path: {vault_path}")
        
        console.print("Starting analysis...")
        results = curator.analyze_vault(sample_size=sample_size)
        
        console.print(f"\n[bold green]Analysis complete![/bold green]")
        console.print(f"Processed {results.total_notes_processed} notes")
        console.print(f"Results saved to: {curator.results_dir}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option('--file', '-f', type=click.Path(exists=True, dir_okay=False), 
              required=True, help='Path to a single note file')
@click.pass_context
def analyze_single(ctx, file: str):
    """Analyze a single note file."""
    try:
        config_dir = ctx.obj['config_dir']
        
        console.print("[bold blue]Analyzing single note...[/bold blue]")
        
        curator = NoteCurator(config_dir)
        note_path = Path(file)
        
        if not note_path.exists():
            raise FileNotFoundError(f"Note file not found: {file}")
        
        # Process the single note
        note_analysis = curator.note_processor.process_note(note_path)
        
        # Display results
        console.print(f"\n[bold]Analysis Results for {note_path.name}[/bold]")
        console.print(f"File: {note_path}")
        console.print(f"Size: {note_analysis.file_size} bytes")
        console.print(f"Words: {note_analysis.word_count}")
        console.print(f"Characters: {note_analysis.character_count}")
        
        if note_analysis.primary_pillar:
            console.print(f"Primary Pillar: {note_analysis.primary_pillar.value}")
        
        if note_analysis.note_type:
            console.print(f"Note Type: {note_analysis.note_type.value}")
        
        console.print(f"Overall Score: {note_analysis.overall_score:.2f}")
        console.print(f"Curation Action: {note_analysis.curation_action.value}")
        console.print(f"Reasoning: {note_analysis.curation_reasoning}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option('--input-file', '-i', type=click.Path(exists=True, dir_okay=False), 
              required=True, help='Path to input note file')
@click.option('--output-dir', '-o', type=click.Path(file_okay=False), 
              default='normalized', help='Output directory for normalized note')
@click.option('--note-type', type=click.Choice(['literature_research', 'project_workflow', 'personal_reflection', 'technical_code', 'meeting_template', 'community_event']), 
              help='Note type for template')
@click.option('--pillar', type=click.Choice(['ppp_fundamentals', 'operational_risk', 'value_for_money', 'digital_transformation', 'governance_transparency']), 
              help='Expert pillar for template')
@click.pass_context
def normalize(ctx, input_file: str, output_dir: str, note_type: Optional[str], pillar: Optional[str]):
    """Normalize and structure a single note."""
    try:
        config_dir = ctx.obj['config_dir']
        
        console.print("[bold blue]Normalizing Note[/bold blue]")
        
        curator = NoteCurator(config_dir)
        note_path = Path(input_file)
        output_path = Path(output_dir)
        
        if not note_path.exists():
            raise FileNotFoundError(f"Note file not found: {input_file}")
        
        # Read the note content
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect note type and pillar if not provided
        if not note_type or not pillar:
            # Analyze the note to determine type and pillar
            note_analysis = curator.note_processor.process_note(note_path)
            note_type = note_type or (note_analysis.note_type.value if note_analysis.note_type else 'default')
            pillar = pillar or (note_analysis.primary_pillar.value if note_analysis.primary_pillar else 'general')
        
        # Normalize the content
        normalized_content = curator.note_processor.content_processor.normalize_note_structure(
            content, note_type, pillar
        )
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save normalized note
        output_file = output_path / f"{note_path.stem}_normalized.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(normalized_content)
        
        console.print(f"✓ Normalized note saved to: {output_file}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    try:
        config_dir = ctx.obj['config_dir']
        
        console.print("[bold blue]Current Configuration[/bold blue]")
        
        # Load and display configs
        config_files = ['vault_config.yaml', 'classification_config.yaml', 'models_config.yaml']
        
        for config_file in config_files:
            config_path = config_dir / config_file
            if config_path.exists():
                console.print(f"\n[bold]{config_file}[/bold]")
                with open(config_path, 'r') as f:
                    content = f.read()
                    console.print(f"[dim]{content}[/dim]")
            else:
                console.print(f"\n[red]Missing: {config_file}[/red]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and model availability."""
    try:
        config_dir = ctx.obj['config_dir']
        
        console.print("[bold blue]System Status[/bold blue]")
        
        # Check config files
        config_files = ['vault_config.yaml', 'classification_config.yaml', 'models_config.yaml']
        for config_file in config_files:
            config_path = config_dir / config_file
            if config_path.exists():
                console.print(f"✓ {config_file}")
            else:
                console.print(f"✗ {config_file} (missing)")
        
        # Check models
        console.print("\n[bold]Model Status[/bold]")
        try:
            curator = NoteCurator(config_dir)
            for model_type, model in curator.llm_manager.models.items():
                console.print(f"✓ {model_type}: {type(model).__name__}")
        except Exception as e:
            console.print(f"✗ Models: {e}")
        
        # Check vault
        console.print("\n[bold]Vault Status[/bold]")
        try:
            curator = NoteCurator(config_dir)
            vault_path = Path(curator.vault_config['vault']['path'])
            if vault_path.exists():
                notes = curator.note_processor.find_notes(vault_path)
                console.print(f"✓ Vault: {vault_path} ({len(notes)} notes found)")
            else:
                console.print(f"✗ Vault: {vault_path} (not found)")
        except Exception as e:
            console.print(f"✗ Vault: {e}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main() 