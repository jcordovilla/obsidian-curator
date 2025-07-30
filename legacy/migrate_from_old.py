#!/usr/bin/env python3
"""
Migration script from the old note classification system to the new one.

This script helps migrate from the old filter_notes.py to the new Poetry-based system.
"""

import json
import shutil
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def migrate_config():
    """Migrate configuration from old system to new YAML configs."""
    console.print("[bold blue]Migrating Configuration[/bold blue]")
    
    # Check if old config exists
    old_config = {
        'NOTES_DIR': '/Users/jose/Documents/Evermd',
        'MODEL_PATH': 'models/llama-3.1-8b-instruct-q6_k.gguf',
        'MAX_NOTES': 10,
        'MAX_NOTE_CHARS': 2000
    }
    
    # Create new config directory
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Update vault config with old settings
    vault_config = {
        'vault': {
            'path': old_config['NOTES_DIR'],
            'include_patterns': ['*.md'],
            'exclude_patterns': [
                '**/node_modules/**',
                '**/.git/**',
                '**/attachments/**',
                '**/temp/**'
            ]
        },
        'processing': {
            'max_notes_per_batch': old_config['MAX_NOTES'],
            'max_note_chars': old_config['MAX_NOTE_CHARS'],
            'process_attachments': False,
            'include_frontmatter': True
        },
        'output': {
            'results_dir': 'results',
            'formats': ['json', 'markdown', 'csv'],
            'detailed_logging': True
        }
    }
    
    # Write vault config
    import yaml
    with open(config_dir / "vault_config.yaml", 'w') as f:
        yaml.dump(vault_config, f, default_flow_style=False, indent=2)
    
    console.print("✓ Created vault_config.yaml")
    
    # Create models config
    models_config = {
        'models': {
            'analysis': {
                'path': old_config['MODEL_PATH'],
                'context_window': 8192,
                'max_tokens': 1024,
                'temperature': 0.1,
                'top_p': 0.9,
                'n_gpu_layers': -1,
                'n_threads': 8
            },
            'classification': {
                'path': old_config['MODEL_PATH'],
                'context_window': 4096,
                'max_tokens': 512,
                'temperature': 0.05,
                'top_p': 0.95,
                'n_gpu_layers': -1,
                'n_threads': 4
            },
            'summary': {
                'path': old_config['MODEL_PATH'],
                'context_window': 4096,
                'max_tokens': 256,
                'temperature': 0.1,
                'top_p': 0.9,
                'n_gpu_layers': -1,
                'n_threads': 4
            }
        },
        'fallback': {
            'model_path': old_config['MODEL_PATH'],
            'context_window': 4096,
            'max_tokens': 512,
            'temperature': 0.1,
            'n_gpu_layers': 0,
            'n_threads': 4
        }
    }
    
    with open(config_dir / "models_config.yaml", 'w') as f:
        yaml.dump(models_config, f, default_flow_style=False, indent=2)
    
    console.print("✓ Created models_config.yaml")


def migrate_results():
    """Migrate old results to new format."""
    console.print("\n[bold blue]Migrating Results[/bold blue]")
    
    old_results_file = Path("note_classification.json")
    if not old_results_file.exists():
        console.print("No old results found to migrate")
        return
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Read old results
    with open(old_results_file, 'r') as f:
        old_results = json.load(f)
    
    # Convert to new format
    new_results = {
        'vault_path': '/Users/jose/Documents/Evermd',
        'processing_date': '2024-01-01T00:00:00',  # Placeholder
        'total_notes_processed': len(old_results),
        'batches': [
            {
                'batch_id': 'migrated_batch',
                'start_time': '2024-01-01T00:00:00',
                'end_time': '2024-01-01T00:00:00',
                'notes': [],
                'total_notes': len(old_results),
                'processed_notes': len(old_results),
                'failed_notes': 0
            }
        ],
        'notes_by_action': {},
        'notes_by_pillar': {},
        'notes_by_type': {},
        'high_value_notes': 0,
        'medium_value_notes': 0,
        'low_value_notes': 0
    }
    
    # Convert old results to new format
    for old_result in old_results:
        # Map old verdict to new action
        verdict_map = {
            'useful': 'keep',
            'not useful': 'delete',
            'undecided': 'archive'
        }
        
        action = verdict_map.get(old_result.get('verdict', 'undecided'), 'archive')
        
        # Create new note analysis
        note_analysis = {
            'file_path': old_result['path'],
            'file_name': Path(old_result['path']).name,
            'file_size': 0,  # Unknown
            'created_date': None,
            'modified_date': None,
            'word_count': 0,  # Unknown
            'character_count': 0,  # Unknown
            'has_frontmatter': False,
            'has_attachments': False,
            'attachment_count': 0,
            'primary_pillar': None,
            'secondary_pillars': [],
            'note_type': None,
            'quality_scores': {
                'relevance': 0.5,
                'depth': 0.5,
                'actionability': 0.5,
                'uniqueness': 0.5,
                'structure': 0.5
            },
            'pillar_analyses': [],
            'curation_action': action,
            'curation_reasoning': old_result.get('reason', 'Migrated from old system'),
            'confidence': 0.5,
            'processing_timestamp': '2024-01-01T00:00:00',
            'model_used': 'llama-3.1-8b-instruct'
        }
        
        new_results['batches'][0]['notes'].append(note_analysis)
        
        # Count actions
        if action not in new_results['notes_by_action']:
            new_results['notes_by_action'][action] = 0
        new_results['notes_by_action'][action] += 1
    
    # Save migrated results
    with open(results_dir / "migrated_classification.json", 'w') as f:
        json.dump(new_results, f, indent=2)
    
    console.print("✓ Migrated old results to results/migrated_classification.json")


def backup_old_files():
    """Backup old files before migration."""
    console.print("\n[bold blue]Backing Up Old Files[/bold blue]")
    
    backup_dir = Path("backup_old_system")
    backup_dir.mkdir(exist_ok=True)
    
    old_files = [
        "filter_notes.py",
        "loading_notes.py", 
        "note_classification.json"
    ]
    
    for file_name in old_files:
        old_file = Path(file_name)
        if old_file.exists():
            shutil.copy2(old_file, backup_dir / file_name)
            console.print(f"✓ Backed up {file_name}")
    
    console.print(f"✓ Old files backed up to {backup_dir}")


def main():
    """Run the migration process."""
    console.print("[bold green]Obsidian Note Curator Migration[/bold green]")
    console.print("This will migrate your old system to the new Poetry-based system.\n")
    
    try:
        # Backup old files
        backup_old_files()
        
        # Migrate configuration
        migrate_config()
        
        # Migrate results
        migrate_results()
        
        console.print("\n[bold green]Migration Complete![/bold green]")
        console.print("\nNext steps:")
        console.print("1. Install Poetry: curl -sSL https://install.python-poetry.org | python3 -")
        console.print("2. Install dependencies: poetry install")
        console.print("3. Test the new system: poetry run curate-notes status")
        console.print("4. Run analysis: poetry run curate-notes analyze --sample-size 5")
        
    except Exception as e:
        console.print(f"\n[red]Migration failed: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main()) 