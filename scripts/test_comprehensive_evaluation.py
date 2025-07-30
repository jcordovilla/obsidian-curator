#!/usr/bin/env python3
"""
Comprehensive evaluation test that compares raw notes with processed results.

This test properly evaluates the pipeline by:
1. Capturing raw note content before any processing
2. Tracking transformations at each stage (Evernote cleaning, preprocessing, LLM)
3. Providing before/after comparisons for validation
4. Enabling manual review of transformations
5. Calculating accuracy metrics and quality assessments
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, asdict

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from note_curator.utils.evernote_cleaner import EvernoteClippingCleaner
from note_curator.utils.preprocessor import ContentPreprocessor
from note_curator.models.llm_manager import LLMManager
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

console = Console()


@dataclass
class RawNote:
    """Raw note data before any processing."""
    file_path: Path
    original_content: str
    file_size: int
    created_date: str
    modified_date: str


@dataclass
class EvernoteCleaningResult:
    """Results after Evernote cleaning."""
    file_path: Path
    original_content: str
    cleaned_content: str
    is_evernote_clipping: bool
    reduction_ratio: float
    bytes_saved: int
    cleaning_time: float
    cleaning_stats: Dict[str, Any]


@dataclass
class PreprocessingResult:
    """Results after preprocessing."""
    file_path: Path
    original_content: str
    cleaned_content: str
    should_process: bool
    processing_reason: str
    content_type: str
    language: str
    quality_score: float
    word_count: int
    issues: List[str]
    preprocessing_time: float
    metadata: Dict[str, Any]


@dataclass
class LLMAnalysisResult:
    """Results after LLM analysis."""
    file_path: Path
    original_content: str
    processed_content: str
    primary_pillar: str
    note_type: str
    quality_scores: Dict[str, float]
    curation_action: str
    curation_reasoning: str
    confidence: float
    llm_time: float
    analysis_result: Dict[str, Any]


@dataclass
class ComprehensiveEvaluation:
    """Complete evaluation data for a single note."""
    raw_note: RawNote
    evernote_cleaning: EvernoteCleaningResult
    preprocessing: PreprocessingResult
    llm_analysis: LLMAnalysisResult
    total_processing_time: float


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


def load_raw_notes(notes: List[Path]) -> List[RawNote]:
    """Load raw note content and metadata."""
    raw_notes = []
    
    for note_path in notes:
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            stat = note_path.stat()
            raw_notes.append(RawNote(
                file_path=note_path,
                original_content=content,
                file_size=stat.st_size,
                created_date=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified_date=datetime.fromtimestamp(stat.st_mtime).isoformat()
            ))
        except Exception as e:
            console.print(f"[red]Error loading {note_path}: {e}[/red]")
    
    return raw_notes


def evaluate_evernote_cleaning(raw_notes: List[RawNote]) -> List[EvernoteCleaningResult]:
    """Evaluate Evernote cleaning on raw notes."""
    console.print("\n[bold blue]🧹 Evaluating Evernote Cleaning[/bold blue]")
    
    cleaner = EvernoteClippingCleaner()
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Cleaning Evernote clippings...", total=len(raw_notes))
        
        for raw_note in raw_notes:
            start_time = time.time()
            
            try:
                # Clean the note
                cleaning_result = cleaner.clean_evernote_clipping(
                    raw_note.original_content, 
                    raw_note.file_path
                )
                
                cleaning_time = time.time() - start_time
                
                # Calculate bytes saved
                original_bytes = len(raw_note.original_content.encode('utf-8'))
                cleaned_bytes = len(cleaning_result.cleaned_content.encode('utf-8'))
                bytes_saved = original_bytes - cleaned_bytes
                
                results.append(EvernoteCleaningResult(
                    file_path=raw_note.file_path,
                    original_content=raw_note.original_content,
                    cleaned_content=cleaning_result.cleaned_content,
                    is_evernote_clipping=cleaning_result.is_evernote_clipping,
                    reduction_ratio=cleaning_result.cleaning_stats.get('reduction_ratio', 0),
                    bytes_saved=bytes_saved,
                    cleaning_time=cleaning_time,
                    cleaning_stats=cleaning_result.cleaning_stats
                ))
                
            except Exception as e:
                console.print(f"[red]Error cleaning {raw_note.file_path}: {e}[/red]")
                # Create a result with original content
                results.append(EvernoteCleaningResult(
                    file_path=raw_note.file_path,
                    original_content=raw_note.original_content,
                    cleaned_content=raw_note.original_content,
                    is_evernote_clipping=False,
                    reduction_ratio=0,
                    bytes_saved=0,
                    cleaning_time=0,
                    cleaning_stats={'error': str(e)}
                ))
            
            progress.advance(task)
    
    return results


def evaluate_preprocessing(evernote_results: List[EvernoteCleaningResult]) -> List[PreprocessingResult]:
    """Evaluate preprocessing on cleaned notes."""
    console.print("\n[bold blue]🔍 Evaluating Preprocessing[/bold blue]")
    
    preprocessor = ContentPreprocessor()
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Preprocessing notes...", total=len(evernote_results))
        
        for evernote_result in evernote_results:
            start_time = time.time()
            
            try:
                # Use cleaned content from Evernote cleaning
                preprocessing_result = preprocessor.preprocess_note(
                    evernote_result.cleaned_content,
                    evernote_result.file_path
                )
                
                preprocessing_time = time.time() - start_time
                
                results.append(PreprocessingResult(
                    file_path=evernote_result.file_path,
                    original_content=evernote_result.original_content,
                    cleaned_content=preprocessing_result.cleaned_content,
                    should_process=preprocessing_result.should_process,
                    processing_reason=preprocessing_result.processing_reason,
                    content_type=preprocessing_result.content_type.value,
                    language=preprocessing_result.language.value,
                    quality_score=preprocessing_result.quality_score,
                    word_count=preprocessing_result.word_count,
                    issues=preprocessing_result.issues,
                    preprocessing_time=preprocessing_time,
                    metadata=preprocessing_result.metadata
                ))
                
            except Exception as e:
                console.print(f"[red]Error preprocessing {evernote_result.file_path}: {e}[/red]")
                # Create a result with error
                results.append(PreprocessingResult(
                    file_path=evernote_result.file_path,
                    original_content=evernote_result.original_content,
                    cleaned_content=evernote_result.cleaned_content,
                    should_process=False,
                    processing_reason=f"Error: {e}",
                    content_type="error",
                    language="unknown",
                    quality_score=0.0,
                    word_count=0,
                    issues=[f"preprocessing_error: {e}"],
                    preprocessing_time=0,
                    metadata={'error': str(e)}
                ))
            
            progress.advance(task)
    
    return results


def evaluate_llm_analysis(preprocessing_results: List[PreprocessingResult]) -> List[LLMAnalysisResult]:
    """Evaluate LLM analysis on preprocessed notes."""
    console.print("\n[bold blue]🤖 Evaluating LLM Analysis[/bold blue]")
    
    llm_manager = LLMManager()
    results = []
    
    # Only process notes that passed preprocessing
    processable_notes = [r for r in preprocessing_results if r.should_process]
    
    if not processable_notes:
        console.print("[yellow]No notes passed preprocessing - skipping LLM analysis[/yellow]")
        return []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing with LLM...", total=len(processable_notes))
        
        for preprocessing_result in processable_notes:
            start_time = time.time()
            
            try:
                # Analyze with LLM
                analysis_result = llm_manager.analyze_and_classify_note(
                    preprocessing_result.cleaned_content,
                    preprocessing_result.file_path
                )
                
                llm_time = time.time() - start_time
                
                results.append(LLMAnalysisResult(
                    file_path=preprocessing_result.file_path,
                    original_content=preprocessing_result.original_content,
                    processed_content=preprocessing_result.cleaned_content,
                    primary_pillar=analysis_result.get('primary_pillar', 'unknown'),
                    note_type=analysis_result.get('note_type', 'unknown'),
                    quality_scores=analysis_result.get('quality_scores', {}),
                    curation_action=analysis_result.get('curation_action', 'unknown'),
                    curation_reasoning=analysis_result.get('curation_reasoning', ''),
                    confidence=analysis_result.get('confidence', 0.0),
                    llm_time=llm_time,
                    analysis_result=analysis_result
                ))
                
            except Exception as e:
                console.print(f"[red]Error analyzing {preprocessing_result.file_path}: {e}[/red]")
                # Create a result with error
                results.append(LLMAnalysisResult(
                    file_path=preprocessing_result.file_path,
                    original_content=preprocessing_result.original_content,
                    processed_content=preprocessing_result.cleaned_content,
                    primary_pillar="error",
                    note_type="error",
                    quality_scores={},
                    curation_action="error",
                    curation_reasoning=f"Error: {e}",
                    confidence=0.0,
                    llm_time=0,
                    analysis_result={'error': str(e)}
                ))
            
            progress.advance(task)
    
    return results


def create_comprehensive_evaluations(
    raw_notes: List[RawNote],
    evernote_results: List[EvernoteCleaningResult],
    preprocessing_results: List[PreprocessingResult],
    llm_results: List[LLMAnalysisResult]
) -> List[ComprehensiveEvaluation]:
    """Create comprehensive evaluation objects."""
    evaluations = []
    
    # Create lookup dictionaries
    evernote_lookup = {r.file_path: r for r in evernote_results}
    preprocessing_lookup = {r.file_path: r for r in preprocessing_results}
    llm_lookup = {r.file_path: r for r in llm_results}
    
    for raw_note in raw_notes:
        evernote_result = evernote_lookup.get(raw_note.file_path)
        preprocessing_result = preprocessing_lookup.get(raw_note.file_path)
        llm_result = llm_lookup.get(raw_note.file_path)
        
        # Calculate total processing time
        total_time = 0
        if evernote_result:
            total_time += evernote_result.cleaning_time
        if preprocessing_result:
            total_time += preprocessing_result.preprocessing_time
        if llm_result:
            total_time += llm_result.llm_time
        
        evaluations.append(ComprehensiveEvaluation(
            raw_note=raw_note,
            evernote_cleaning=evernote_result,
            preprocessing=preprocessing_result,
            llm_analysis=llm_result,
            total_processing_time=total_time
        ))
    
    return evaluations


def display_evaluation_summary(evaluations: List[ComprehensiveEvaluation]):
    """Display comprehensive evaluation summary."""
    console.print(Panel.fit(
        Text("📊 Comprehensive Evaluation Summary", style="bold blue"),
        subtitle="Before/After Analysis of Complete Pipeline"
    ))
    
    # Overall statistics
    total_notes = len(evaluations)
    evernote_clippings = sum(1 for e in evaluations if e.evernote_cleaning and e.evernote_cleaning.is_evernote_clipping)
    processed_notes = sum(1 for e in evaluations if e.preprocessing and e.preprocessing.should_process)
    llm_analyzed = sum(1 for e in evaluations if e.llm_analysis)
    
    # Time statistics
    total_evernote_time = sum(e.evernote_cleaning.cleaning_time for e in evaluations if e.evernote_cleaning)
    total_preprocessing_time = sum(e.preprocessing.preprocessing_time for e in evaluations if e.preprocessing)
    total_llm_time = sum(e.llm_analysis.llm_time for e in evaluations if e.llm_analysis)
    total_time = sum(e.total_processing_time for e in evaluations)
    
    # Quality statistics
    quality_scores = [e.preprocessing.quality_score for e in evaluations if e.preprocessing and e.preprocessing.quality_score > 0]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    # Display summary table
    summary_table = Table(title="Pipeline Performance Summary")
    summary_table.add_column("Stage", style="cyan")
    summary_table.add_column("Notes Processed", style="magenta")
    summary_table.add_column("Success Rate", style="green")
    summary_table.add_column("Time", style="yellow")
    summary_table.add_column("Time per Note", style="blue")
    
    summary_table.add_row(
        "Raw Notes",
        str(total_notes),
        "100%",
        "N/A",
        "N/A"
    )
    
    summary_table.add_row(
        "Evernote Cleaning",
        str(evernote_clippings),
        f"{evernote_clippings/total_notes:.1%}",
        f"{total_evernote_time:.2f}s",
        f"{total_evernote_time/total_notes:.3f}s"
    )
    
    summary_table.add_row(
        "Preprocessing",
        str(processed_notes),
        f"{processed_notes/total_notes:.1%}",
        f"{total_preprocessing_time:.2f}s",
        f"{total_preprocessing_time/total_notes:.3f}s"
    )
    
    summary_table.add_row(
        "LLM Analysis",
        str(llm_analyzed),
        f"{llm_analyzed/total_notes:.1%}",
        f"{total_llm_time:.2f}s",
        f"{total_llm_time/llm_analyzed:.2f}s" if llm_analyzed > 0 else "N/A"
    )
    
    summary_table.add_row(
        "Total Pipeline",
        str(total_notes),
        "100%",
        f"{total_time:.2f}s",
        f"{total_time/total_notes:.2f}s"
    )
    
    console.print(summary_table)
    
    # Quality analysis
    if quality_scores:
        console.print(f"\n[bold]📈 Quality Analysis:[/bold]")
        console.print(f"Average Quality Score: {avg_quality:.3f}")
        console.print(f"Quality Score Range: {min(quality_scores):.3f} - {max(quality_scores):.3f}")
    
    # Curation actions
    if llm_analyzed > 0:
        curation_actions = {}
        for e in evaluations:
            if e.llm_analysis:
                action = e.llm_analysis.curation_action
                curation_actions[action] = curation_actions.get(action, 0) + 1
        
        console.print(f"\n[bold]🎯 Curation Actions:[/bold]")
        for action, count in curation_actions.items():
            console.print(f"{action}: {count} notes ({count/llm_analyzed:.1%})")


def save_comprehensive_results(evaluations: List[ComprehensiveEvaluation]):
    """Save comprehensive evaluation results."""
    output_dir = Path("results/comprehensive_evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    detailed_file = output_dir / f"detailed_evaluation_{timestamp}.json"
    with open(detailed_file, 'w', encoding='utf-8') as f:
        # Convert dataclasses to dictionaries
        detailed_data = []
        for evaluation in evaluations:
            eval_dict = {
                'file_path': str(evaluation.raw_note.file_path),
                'raw_note': asdict(evaluation.raw_note),
                'evernote_cleaning': asdict(evaluation.evernote_cleaning) if evaluation.evernote_cleaning else None,
                'preprocessing': asdict(evaluation.preprocessing) if evaluation.preprocessing else None,
                'llm_analysis': asdict(evaluation.llm_analysis) if evaluation.llm_analysis else None,
                'total_processing_time': evaluation.total_processing_time
            }
            detailed_data.append(eval_dict)
        
        json.dump(detailed_data, f, indent=2, default=str)
    
    # Save summary statistics
    summary_file = output_dir / f"evaluation_summary_{timestamp}.json"
    summary_data = {
        'timestamp': timestamp,
        'total_notes': len(evaluations),
        'evernote_clippings': sum(1 for e in evaluations if e.evernote_cleaning and e.evernote_cleaning.is_evernote_clipping),
        'processed_notes': sum(1 for e in evaluations if e.preprocessing and e.preprocessing.should_process),
        'llm_analyzed': sum(1 for e in evaluations if e.llm_analysis),
        'total_processing_time': sum(e.total_processing_time for e in evaluations),
        'average_quality_score': sum(e.preprocessing.quality_score for e in evaluations if e.preprocessing and e.preprocessing.quality_score > 0) / max(1, sum(1 for e in evaluations if e.preprocessing and e.preprocessing.quality_score > 0)),
        'curation_actions': {}
    }
    
    # Calculate curation action distribution
    for evaluation in evaluations:
        if evaluation.llm_analysis:
            action = evaluation.llm_analysis.curation_action
            summary_data['curation_actions'][action] = summary_data['curation_actions'].get(action, 0) + 1
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Comprehensive evaluation results saved![/green]")
    console.print(f"📄 Detailed results: {detailed_file}")
    console.print(f"📄 Summary: {summary_file}")


def main():
    """Main evaluation function."""
    console.print(Panel.fit(
        Text("🔬 Comprehensive Pipeline Evaluation", style="bold blue"),
        subtitle="Before/After Analysis with Full Content Tracking"
    ))
    
    try:
        # Load configuration
        config = load_config()
        vault_path = Path(config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[blue]Vault path: {vault_path}[/blue]")
        
        # Find and load sample notes
        sample_size = 10
        console.print(f"\n[yellow]Finding {sample_size} sample notes...[/yellow]")
        
        notes = find_sample_notes(vault_path, sample_size)
        console.print(f"Found {len(notes)} notes for evaluation")
        
        # Load raw notes
        console.print("\n[yellow]Loading raw note content...[/yellow]")
        raw_notes = load_raw_notes(notes)
        console.print(f"Loaded {len(raw_notes)} raw notes")
        
        # Evaluate each stage
        evernote_results = evaluate_evernote_cleaning(raw_notes)
        preprocessing_results = evaluate_preprocessing(evernote_results)
        llm_results = evaluate_llm_analysis(preprocessing_results)
        
        # Create comprehensive evaluations
        evaluations = create_comprehensive_evaluations(
            raw_notes, evernote_results, preprocessing_results, llm_results
        )
        
        # Display results
        display_evaluation_summary(evaluations)
        
        # Save results
        save_comprehensive_results(evaluations)
        
        console.print("\n[bold green]✅ Comprehensive evaluation completed![/bold green]")
        console.print("\n[bold]📋 What this evaluation provides:[/bold]")
        console.print("• Raw content preserved for comparison")
        console.print("• Step-by-step transformation tracking")
        console.print("• Before/after content analysis")
        console.print("• Quality assessment validation")
        console.print("• Processing time breakdown")
        console.print("• Curation action distribution")
        console.print("• Detailed results for manual review")
        
    except Exception as e:
        console.print(f"[red]❌ Error during evaluation: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 