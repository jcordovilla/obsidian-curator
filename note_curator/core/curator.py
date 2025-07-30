"""Main curator class for orchestrating note classification."""

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .models import (
    NoteAnalysis, ProcessingBatch, ClassificationResults, 
    CurationAction, PillarType, NoteType
)
from .note_processor import NoteProcessor
from ..models.llm_manager import LLMManager

logger = logging.getLogger(__name__)
console = Console()


class NoteCurator:
    """Main curator for processing and classifying notes."""
    
    def __init__(self, config_dir: Path = Path("config")):
        """Initialize the curator."""
        self.config_dir = config_dir
        self.vault_config = self._load_config("vault_config.yaml")
        self.classification_config = self._load_config("classification_config.yaml")
        
        # Initialize components
        self.llm_manager = LLMManager(config_dir / "models_config.yaml")
        self.note_processor = NoteProcessor(self.vault_config['vault'], self.llm_manager)
        
        # Create results directory
        self.results_dir = Path(self.vault_config['output']['results_dir'])
        self.results_dir.mkdir(exist_ok=True)
    
    def _load_config(self, filename: str) -> Dict:
        """Load configuration file."""
        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
    
    def analyze_vault(self, sample_size: Optional[int] = None) -> ClassificationResults:
        """Analyze the entire vault or a sample of notes."""
        vault_path = Path(self.vault_config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        # Find all notes
        all_notes = self.note_processor.find_notes(vault_path)
        
        # Determine if this is a test run
        is_test_run = sample_size is not None and sample_size < len(all_notes)
        
        if is_test_run:
            console.print(f"Sampling {sample_size} notes from {len(all_notes)} total notes")
            selected_notes = random.sample(all_notes, sample_size)
        else:
            # For normal processing, sort notes by folder structure to maintain thematic order
            selected_notes = self._sort_notes_by_folder_structure(all_notes, vault_path)
            console.print(f"Processing {len(selected_notes)} notes sequentially by folder structure")
            # Show folder structure before starting progress bar
            self._display_folder_structure(selected_notes, vault_path)
        
        # Process notes in batches
        max_notes_per_batch = self.vault_config['processing']['max_notes_per_batch']
        batches = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Create main task
            main_task = progress.add_task(
                f"Processing {len(selected_notes)} notes...", 
                total=len(selected_notes)
            )
            
            for i in range(0, len(selected_notes), max_notes_per_batch):
                batch_notes = selected_notes[i:i + max_notes_per_batch]
                batch = self._process_batch(batch_notes, progress, main_task)
                batches.append(batch)
        
        # Compile results
        results = self._compile_results(vault_path, batches)
        
        # Save results with appropriate subfolder
        self._save_results(results, is_test_run=is_test_run)
        
        # Normalize "keep" and "refine" notes if requested
        if self.vault_config.get('processing', {}).get('normalize_notes', False):
            self._normalize_passed_notes(results)
        
        # Display summary
        self._display_summary(results)
        
        return results
    
    def _sort_notes_by_folder_structure(self, notes: List[Path], vault_path: Path) -> List[Path]:
        """Sort notes by folder structure to maintain thematic organization."""
        def get_folder_depth_and_path(note_path: Path) -> tuple:
            """Get folder depth and path for sorting."""
            relative_path = note_path.relative_to(vault_path)
            parts = relative_path.parts
            # Sort by folder depth first, then by folder name, then by filename
            return (len(parts) - 1, str(relative_path.parent), note_path.name)
        
        # Sort notes by folder structure
        sorted_notes = sorted(notes, key=lambda x: get_folder_depth_and_path(x))
        
        return sorted_notes
    
    def _display_folder_structure(self, notes: List[Path], vault_path: Path):
        """Display folder structure information."""
        # Group notes by folder
        folder_groups = {}
        for note in notes:
            relative_path = note.relative_to(vault_path)
            folder = str(relative_path.parent)
            if folder not in folder_groups:
                folder_groups[folder] = 0
            folder_groups[folder] += 1
        
        console.print(f"📁 Processing order by folders:")
        for folder, count in sorted(folder_groups.items()):
            if folder == '.':
                console.print(f"  • Root folder: {count} notes")
            else:
                console.print(f"  • {folder}: {count} notes")
    
    def _process_batch(
        self, 
        note_paths: List[Path], 
        progress: Progress, 
        main_task: int
    ) -> ProcessingBatch:
        """Process a batch of notes."""
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch = ProcessingBatch(
            batch_id=batch_id,
            start_time=datetime.now(),
            total_notes=len(note_paths)
        )
        
        max_chars = self.vault_config['processing']['max_note_chars']
        
        for note_path in note_paths:
            try:
                # Process note
                note_analysis = self.note_processor.process_note(note_path, max_chars)
                batch.notes.append(note_analysis)
                batch.processed_notes += 1
                
                # Update progress
                progress.update(main_task, advance=1)
                progress.update(
                    main_task, 
                    description=f"Processed: {note_path.name}"
                )
                
            except Exception as e:
                logger.error(f"Failed to process {note_path}: {e}")
                batch.failed_notes += 1
                batch.processed_notes += 1
                progress.update(main_task, advance=1)
        
        batch.end_time = datetime.now()
        return batch
    
    def _compile_results(self, vault_path: Path, batches: List[ProcessingBatch]) -> ClassificationResults:
        """Compile results from all batches."""
        all_notes = []
        for batch in batches:
            all_notes.extend(batch.notes)
        
        # Count by action
        notes_by_action = {}
        for action in CurationAction:
            notes_by_action[action] = len([n for n in all_notes if n.curation_action == action])
        
        # Count by pillar
        notes_by_pillar = {}
        for pillar in PillarType:
            notes_by_pillar[pillar] = len([n for n in all_notes if n.primary_pillar == pillar])
        
        # Count by note type
        notes_by_type = {}
        for note_type in NoteType:
            notes_by_type[note_type] = len([n for n in all_notes if n.note_type == note_type])
        
        # Quality distribution
        high_value = len([n for n in all_notes if n.is_high_value])
        medium_value = len([n for n in all_notes if n.needs_refinement])
        low_value = len([n for n in all_notes if not n.is_high_value and not n.needs_refinement])
        
        return ClassificationResults(
            vault_path=vault_path,
            total_notes_processed=len(all_notes),
            batches=batches,
            notes_by_action=notes_by_action,
            notes_by_pillar=notes_by_pillar,
            notes_by_type=notes_by_type,
            high_value_notes=high_value,
            medium_value_notes=medium_value,
            low_value_notes=low_value
        )
    
    def _save_results(self, results: ClassificationResults, is_test_run: bool = False):
        """Save results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine subfolder based on run type
        if is_test_run:
            subfolder = "test_runs"
            run_type = "test"
        else:
            subfolder = "full_runs"
            run_type = "full"
        
        # Create subfolder
        output_dir = self.results_dir / subfolder
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON results
        json_path = output_dir / f"classification_{run_type}_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results.model_dump(), f, indent=2, default=str)
        
        # Save markdown report
        md_path = output_dir / f"analysis_report_{run_type}_{timestamp}.md"
        self._generate_markdown_report(results, md_path)
        
        # Save curation actions
        actions_path = output_dir / f"curation_actions_{run_type}_{timestamp}.md"
        self._generate_curation_actions(results, actions_path)
        
        console.print(f"Results saved to {output_dir}")
        return output_dir
    
    def _generate_markdown_report(self, results: ClassificationResults, output_path: Path):
        """Generate a markdown report."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Note Classification Report\n\n")
            f.write(f"**Vault:** {results.vault_path}\n")
            f.write(f"**Processing Date:** {results.processing_date}\n")
            f.write(f"**Total Notes Processed:** {results.total_notes_processed}\n\n")
            
            # Summary statistics
            f.write("## Summary Statistics\n\n")
            f.write(f"- **High Value Notes:** {results.high_value_notes}\n")
            f.write(f"- **Medium Value Notes:** {results.medium_value_notes}\n")
            f.write(f"- **Low Value Notes:** {results.low_value_notes}\n")
            f.write(f"- **Average Quality Score:** {results.average_quality_score:.2f}\n\n")
            
            # Curation actions
            f.write("## Curation Actions\n\n")
            for action, count in results.notes_by_action.items():
                f.write(f"- **{action.value.title()}:** {count} notes\n")
            f.write("\n")
            
            # Pillar distribution
            f.write("## Notes by Expert Pillar\n\n")
            for pillar, count in results.notes_by_pillar.items():
                f.write(f"- **{pillar.value.replace('_', ' ').title()}:** {count} notes\n")
            f.write("\n")
            
            # Note types
            f.write("## Notes by Type\n\n")
            for note_type, count in results.notes_by_type.items():
                f.write(f"- **{note_type.value.replace('_', ' ').title()}:** {count} notes\n")
    
    def _generate_curation_actions(self, results: ClassificationResults, output_path: Path):
        """Generate curation actions file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Curation Actions\n\n")
            f.write("This file contains recommended actions for each note.\n\n")
            
            # Group notes by action
            for action in CurationAction:
                action_notes = []
                for batch in results.batches:
                    for note in batch.notes:
                        if note.curation_action == action:
                            action_notes.append(note)
                
                if action_notes:
                    f.write(f"## {action.value.title()}\n\n")
                    f.write(f"**{len(action_notes)} notes**\n\n")
                    
                    for note in sorted(action_notes, key=lambda n: n.overall_score, reverse=True):
                        f.write(f"### {note.file_name}\n")
                        f.write(f"- **Score:** {note.overall_score:.2f}\n")
                        f.write(f"- **Primary Pillar:** {note.primary_pillar.value if note.primary_pillar else 'None'}\n")
                        f.write(f"- **Note Type:** {note.note_type.value if note.note_type else 'None'}\n")
                        f.write(f"- **Reasoning:** {note.curation_reasoning}\n")
                        f.write(f"- **Path:** {note.file_path}\n\n")
    
    def _display_summary(self, results: ClassificationResults):
        """Display a summary table."""
        table = Table(title="Classification Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Notes", str(results.total_notes_processed))
        table.add_row("High Value", str(results.high_value_notes))
        table.add_row("Medium Value", str(results.medium_value_notes))
        table.add_row("Low Value", str(results.low_value_notes))
        table.add_row("Average Score", f"{results.average_quality_score:.2f}")
        
        console.print(table)
        
        # Show top actions
        action_table = Table(title="Curation Actions")
        action_table.add_column("Action", style="cyan")
        action_table.add_column("Count", style="magenta")
        
        for action, count in results.notes_by_action.items():
            action_table.add_row(action.value.title(), str(count))
        
        console.print(action_table)
    
    def _normalize_passed_notes(self, results: ClassificationResults):
        """Normalize notes that passed classification (keep/refine)."""
        console.print("\n[bold blue]Normalizing Passed Notes[/bold blue]")
        
        # Create normalized notes directory
        normalized_dir = self.results_dir / "normalized_notes"
        normalized_dir.mkdir(exist_ok=True)
        
        # Group notes by action
        keep_notes = []
        refine_notes = []
        
        for batch in results.batches:
            for note in batch.notes:
                if note.curation_action.value == 'keep':
                    keep_notes.append(note)
                elif note.curation_action.value == 'refine':
                    refine_notes.append(note)
        
        # Normalize keep notes
        if keep_notes:
            keep_dir = normalized_dir / "keep"
            console.print(f"Normalizing {len(keep_notes)} 'keep' notes...")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Normalizing keep notes...", total=len(keep_notes))
                
                for note in keep_notes:
                    self.note_processor.normalize_note(note, keep_dir)
                    progress.update(task, advance=1)
        
        # Normalize refine notes
        if refine_notes:
            refine_dir = normalized_dir / "refine"
            console.print(f"Normalizing {len(refine_notes)} 'refine' notes...")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Normalizing refine notes...", total=len(refine_notes))
                
                for note in refine_notes:
                    self.note_processor.normalize_note(note, refine_dir)
                    progress.update(task, advance=1)
        
        console.print(f"✓ Normalized notes saved to {normalized_dir}") 