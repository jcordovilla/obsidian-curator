#!/usr/bin/env python3
"""
Self-Evaluating Pipeline Test with LLM Analysis

This test:
1. Runs the complete pipeline on sample notes
2. Captures raw notes and all processing stages
3. Uses an LLM to analyze the results and draw conclusions about:
   - Workflow efficacy and accuracy
   - Alignment with app goals
   - Quality of transformations
   - Recommendations for improvement
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
class ProcessingStage:
    """Results from a processing stage."""
    stage_name: str
    input_content: str
    output_content: str
    metadata: Dict[str, Any]
    processing_time: float
    success: bool
    errors: List[str]


@dataclass
class CompleteProcessing:
    """Complete processing data for a single note."""
    raw_note: RawNote
    stages: List[ProcessingStage]
    final_result: Dict[str, Any]
    total_processing_time: float


def load_config(config_path: Path = Path("config/vault_config.yaml")) -> dict:
    """Load vault configuration."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)


def find_sample_notes(vault_path: Path, sample_size: int = 5) -> List[Path]:
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


def process_note_complete(raw_note: RawNote) -> CompleteProcessing:
    """Process a note through all stages and capture complete data."""
    stages = []
    current_content = raw_note.original_content
    
    # Stage 1: Evernote Cleaning
    console.print(f"  🧹 Cleaning Evernote clippings...")
    start_time = time.time()
    try:
        cleaner = EvernoteClippingCleaner()
        cleaning_result = cleaner.clean_evernote_clipping(current_content, raw_note.file_path)
        
        cleaning_time = time.time() - start_time
        stages.append(ProcessingStage(
            stage_name="Evernote Cleaning",
            input_content=current_content,
            output_content=cleaning_result.cleaned_content,
            metadata={
                'is_evernote_clipping': cleaning_result.is_evernote_clipping,
                'reduction_ratio': cleaning_result.cleaning_stats.get('reduction_ratio', 0),
                'bytes_saved': len(current_content.encode('utf-8')) - len(cleaning_result.cleaned_content.encode('utf-8')),
                'cleaning_stats': cleaning_result.cleaning_stats
            },
            processing_time=cleaning_time,
            success=True,
            errors=[]
        ))
        current_content = cleaning_result.cleaned_content
    except Exception as e:
        cleaning_time = time.time() - start_time
        stages.append(ProcessingStage(
            stage_name="Evernote Cleaning",
            input_content=current_content,
            output_content=current_content,
            metadata={'error': str(e)},
            processing_time=cleaning_time,
            success=False,
            errors=[str(e)]
        ))
    
    # Stage 2: Preprocessing
    console.print(f"  🔍 Preprocessing content...")
    start_time = time.time()
    try:
        preprocessor = ContentPreprocessor()
        preprocessing_result = preprocessor.preprocess_note(current_content, raw_note.file_path)
        
        preprocessing_time = time.time() - start_time
        stages.append(ProcessingStage(
            stage_name="Preprocessing",
            input_content=current_content,
            output_content=preprocessing_result.cleaned_content,
            metadata={
                'should_process': preprocessing_result.should_process,
                'processing_reason': preprocessing_result.processing_reason,
                'content_type': preprocessing_result.content_type.value,
                'language': preprocessing_result.language.value,
                'quality_score': preprocessing_result.quality_score,
                'word_count': preprocessing_result.word_count,
                'issues': preprocessing_result.issues,
                'metadata': preprocessing_result.metadata
            },
            processing_time=preprocessing_time,
            success=True,
            errors=[]
        ))
        current_content = preprocessing_result.cleaned_content
    except Exception as e:
        preprocessing_time = time.time() - start_time
        stages.append(ProcessingStage(
            stage_name="Preprocessing",
            input_content=current_content,
            output_content=current_content,
            metadata={'error': str(e)},
            processing_time=preprocessing_time,
            success=False,
            errors=[str(e)]
        ))
    
    # Stage 3: LLM Analysis (only if preprocessing passed)
    final_result = None
    if stages[-1].metadata.get('should_process', False):
        console.print(f"  🤖 Analyzing with LLM...")
        start_time = time.time()
        try:
            llm_manager = LLMManager()
            analysis_result = llm_manager.analyze_and_classify_note(current_content, raw_note.file_path)
            
            llm_time = time.time() - start_time
            stages.append(ProcessingStage(
                stage_name="LLM Analysis",
                input_content=current_content,
                output_content=current_content,  # LLM doesn't modify content
                metadata={
                    'primary_pillar': analysis_result.get('primary_pillar', 'unknown'),
                    'note_type': analysis_result.get('note_type', 'unknown'),
                    'quality_scores': analysis_result.get('quality_scores', {}),
                    'curation_action': analysis_result.get('curation_action', 'unknown'),
                    'curation_reasoning': analysis_result.get('curation_reasoning', ''),
                    'confidence': analysis_result.get('confidence', 0.0),
                    'analysis_result': analysis_result
                },
                processing_time=llm_time,
                success=True,
                errors=[]
            ))
            final_result = analysis_result
        except Exception as e:
            llm_time = time.time() - start_time
            stages.append(ProcessingStage(
                stage_name="LLM Analysis",
                input_content=current_content,
                output_content=current_content,
                metadata={'error': str(e)},
                processing_time=llm_time,
                success=False,
                errors=[str(e)]
            ))
    else:
        console.print(f"  ⏭️  Skipping LLM analysis (preprocessing rejected)")
    
    total_time = sum(stage.processing_time for stage in stages)
    
    return CompleteProcessing(
        raw_note=raw_note,
        stages=stages,
        final_result=final_result,
        total_processing_time=total_time
    )


def create_evaluation_prompt(processing_results: List[CompleteProcessing]) -> str:
    """Create a comprehensive evaluation prompt for the LLM."""
    
    # App goals from the configuration
    app_goals = """
    APP GOALS:
    - Classify notes into 5 expert pillars: PPP Fundamentals, Operational Risk, Value for Money, Digital Transformation, Governance & Transparency
    - Identify note types: literature research, workflows, reflections, technical reports, meeting notes, community content
    - Assess quality on 5 dimensions: relevance, depth, actionability, uniqueness, structure
    - Provide curation actions: keep, refine, archive, delete
    - Clean Evernote clippings and preprocess content for better analysis
    - Support expert knowledge management in infrastructure and PPP domains
    """
    
    # Create detailed analysis of each note
    note_analyses = []
    for i, result in enumerate(processing_results):
        note_analysis = f"""
        NOTE {i+1}: {result.raw_note.file_path.name}
        
        RAW CONTENT (first 500 chars):
        {result.raw_note.original_content[:500]}...
        
        PROCESSING STAGES:
        """
        
        for stage in result.stages:
            note_analysis += f"""
        {stage.stage_name}:
        - Success: {stage.success}
        - Time: {stage.processing_time:.3f}s
        - Errors: {stage.errors if stage.errors else 'None'}
        - Key Metadata: {json.dumps(stage.metadata, indent=2, default=str)}
        """
        
        if result.final_result:
            note_analysis += f"""
        FINAL RESULT:
        - Primary Pillar: {result.final_result.get('primary_pillar', 'unknown')}
        - Note Type: {result.final_result.get('note_type', 'unknown')}
        - Curation Action: {result.final_result.get('curation_action', 'unknown')}
        - Quality Scores: {result.final_result.get('quality_scores', {})}
        - Confidence: {result.final_result.get('confidence', 0.0)}
        - Reasoning: {result.final_result.get('curation_reasoning', '')}
        """
        else:
            note_analysis += """
        FINAL RESULT: None (rejected by preprocessing)
        """
        
        note_analyses.append(note_analysis)
    
    # Overall statistics
    total_notes = len(processing_results)
    successful_llm = sum(1 for r in processing_results if r.final_result is not None)
    total_time = sum(r.total_processing_time for r in processing_results)
    avg_time = total_time / total_notes if total_notes > 0 else 0
    
    # Create the evaluation prompt
    prompt = f"""
    You are an expert evaluator analyzing the performance of an AI-powered note classification system for infrastructure and PPP (Public-Private Partnership) experts.

    {app_goals}

    EVALUATION DATA:
    - Total notes processed: {total_notes}
    - Notes that reached LLM analysis: {successful_llm}
    - Success rate: {successful_llm/total_notes:.1%}
    - Total processing time: {total_time:.2f}s
    - Average time per note: {avg_time:.2f}s

    DETAILED NOTE ANALYSES:
    {chr(10).join(note_analyses)}

    EVALUATION TASK:
    Please provide a comprehensive analysis of this note classification system's efficacy and usefulness. Consider:

    1. WORKFLOW EFFICACY:
    - How well does each processing stage work?
    - Are the transformations meaningful and useful?
    - Is the preprocessing effectively filtering content?
    - Are the LLM classifications accurate and relevant?

    2. ALIGNMENT WITH APP GOALS:
    - Does the system correctly identify the 5 expert pillars?
    - Are note types accurately classified?
    - Do quality assessments align with expert knowledge needs?
    - Are curation actions appropriate and actionable?

    3. CONTENT QUALITY ASSESSMENT:
    - How well does the system handle different content types?
    - Are Evernote clippings properly cleaned?
    - Does preprocessing improve content for analysis?
    - Are rejected notes appropriately filtered?

    4. PERFORMANCE AND EFFICIENCY:
    - Is the processing time reasonable?
    - Are there bottlenecks or inefficiencies?
    - How does the success rate compare to expectations?

    5. RECOMMENDATIONS:
    - What specific improvements would enhance the system?
    - Are there workflow optimizations needed?
    - How could the system better serve expert users?
    - What additional features or refinements would be valuable?

    Please provide a structured analysis with specific examples from the data, clear conclusions about system effectiveness, and actionable recommendations for improvement.
    """
    
    return prompt


def evaluate_with_llm(processing_results: List[CompleteProcessing]) -> Dict[str, Any]:
    """Use LLM to evaluate the pipeline results."""
    console.print("\n[bold blue]🤖 LLM Self-Evaluation[/bold blue]")
    
    llm_manager = LLMManager()
    
    console.print("  📝 Generating comprehensive evaluation...")
    start_time = time.time()
    
    try:
        # App goals from the configuration
        app_goals = """
        APP GOALS:
        - Classify notes into 5 expert pillars: PPP Fundamentals, Operational Risk, Value for Money, Digital Transformation, Governance & Transparency
        - Identify note types: literature research, workflows, reflections, technical reports, meeting notes, community content
        - Assess quality on 5 dimensions: relevance, depth, actionability, uniqueness, structure
        - Provide curation actions: keep, refine, archive, delete
        - Clean Evernote clippings and preprocess content for better analysis
        - Support expert knowledge management in infrastructure and PPP domains
        """
        
        # Create detailed analysis of each note
        note_analyses = []
        for i, result in enumerate(processing_results):
            note_analysis = f"""
            NOTE {i+1}: {result.raw_note.file_path.name}
            
            RAW CONTENT (first 500 chars):
            {result.raw_note.original_content[:500]}...
            
            PROCESSING STAGES:
            """
            
            for stage in result.stages:
                note_analysis += f"""
            {stage.stage_name}:
            - Success: {stage.success}
            - Time: {stage.processing_time:.3f}s
            - Errors: {stage.errors if stage.errors else 'None'}
            - Key Metadata: {json.dumps(stage.metadata, indent=2, default=str)}
            """
            
            if result.final_result:
                note_analysis += f"""
            FINAL RESULT:
            - Primary Pillar: {result.final_result.get('primary_pillar', 'unknown')}
            - Note Type: {result.final_result.get('note_type', 'unknown')}
            - Curation Action: {result.final_result.get('curation_action', 'unknown')}
            - Quality Scores: {result.final_result.get('quality_scores', {})}
            - Confidence: {result.final_result.get('confidence', 0.0)}
            - Reasoning: {result.final_result.get('curation_reasoning', '')}
            """
            else:
                note_analysis += """
            FINAL RESULT: None (rejected by preprocessing)
            """
            
            note_analyses.append(note_analysis)
        
        # Overall statistics
        total_notes = len(processing_results)
        successful_llm = sum(1 for r in processing_results if r.final_result is not None)
        total_time = sum(r.total_processing_time for r in processing_results)
        avg_time = total_time / total_notes if total_notes > 0 else 0
        
        # Create the evaluation prompt
        evaluation_prompt = f"""
        You are an expert evaluator analyzing the performance of an AI-powered note classification system for infrastructure and PPP (Public-Private Partnership) experts.

        {app_goals}

        EVALUATION DATA:
        - Total notes processed: {total_notes}
        - Notes that reached LLM analysis: {successful_llm}
        - Success rate: {successful_llm/total_notes:.1%}
        - Total processing time: {total_time:.2f}s
        - Average time per note: {avg_time:.2f}s

        DETAILED NOTE ANALYSES:
        {chr(10).join(note_analyses)}

        EVALUATION TASK:
        Please provide a comprehensive analysis of this note classification system's efficacy and usefulness. Consider:

        1. WORKFLOW EFFICACY:
        - How well does each processing stage work?
        - Are the transformations meaningful and useful?
        - Is the preprocessing effectively filtering content?
        - Are the LLM classifications accurate and relevant?

        2. ALIGNMENT WITH APP GOALS:
        - Does the system correctly identify the 5 expert pillars?
        - Are note types accurately classified?
        - Do quality assessments align with expert knowledge needs?
        - Are curation actions appropriate and actionable?

        3. CONTENT QUALITY ASSESSMENT:
        - How well does the system handle different content types?
        - Are Evernote clippings properly cleaned?
        - Does preprocessing improve content for analysis?
        - Are rejected notes appropriately filtered?

        4. PERFORMANCE AND EFFICIENCY:
        - Is the processing time reasonable?
        - Are there bottlenecks or inefficiencies?
        - How does the success rate compare to expectations?

        5. RECOMMENDATIONS:
        - What specific improvements would enhance the system?
        - Are there workflow optimizations needed?
        - How could the system better serve expert users?
        - What additional features or refinements would be valuable?

        Please provide a structured analysis with specific examples from the data, clear conclusions about system effectiveness, and actionable recommendations for improvement.
        """
        
        # Create a comprehensive evaluation summary
        total_notes = len(processing_results)
        successful_llm = sum(1 for r in processing_results if r.final_result is not None)
        total_time = sum(r.total_processing_time for r in processing_results)
        avg_time = total_time / total_notes if total_notes > 0 else 0
        
        # Analyze the results
        content_types = {}
        quality_scores = []
        processing_reasons = {}
        final_actions = {}
        primary_pillars = {}
        
        for result in processing_results:
            # Content type analysis
            if len(result.stages) > 1:
                content_type = result.stages[1].metadata.get('content_type', 'unknown')
                content_types[content_type] = content_types.get(content_type, 0) + 1
                
                # Quality scores
                quality_score = result.stages[1].metadata.get('quality_score', 0)
                quality_scores.append(quality_score)
                
                # Processing reasons
                reason = result.stages[1].metadata.get('processing_reason', 'unknown')
                processing_reasons[reason] = processing_reasons.get(reason, 0) + 1
            
            # Final results analysis
            if result.final_result:
                action = result.final_result.get('curation_action', 'unknown')
                final_actions[action] = final_actions.get(action, 0) + 1
                
                pillar = result.final_result.get('primary_pillar', 'unknown')
                primary_pillars[pillar] = primary_pillars.get(pillar, 0) + 1
        
        # Prepare quality score analysis
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            quality_range = f"{min(quality_scores):.3f} - {max(quality_scores):.3f}"
        else:
            avg_quality = "N/A"
            quality_range = "N/A"
        
        # Create evaluation prompt
        evaluation_prompt = f"""
        SYSTEM EVALUATION REPORT
        
        AI Note Classification System Performance Analysis
        
        OVERALL STATISTICS:
        - Total notes processed: {total_notes}
        - Successfully analyzed by LLM: {successful_llm}
        - Success rate: {successful_llm/total_notes:.1%}
        - Total processing time: {total_time:.2f}s
        - Average time per note: {avg_time:.2f}s
        
        CONTENT TYPE DISTRIBUTION:
        {chr(10).join([f"- {ctype}: {count}" for ctype, count in content_types.items()])}
        
        QUALITY SCORE ANALYSIS:
        - Average quality score: {avg_quality}
        - Range: {quality_range}
        
        PROCESSING DECISIONS:
        {chr(10).join([f"- {reason}: {count}" for reason, count in processing_reasons.items()])}
        
        FINAL CURATION ACTIONS:
        {chr(10).join([f"- {action}: {count}" for action, count in final_actions.items()])}
        
        PRIMARY PILLAR CLASSIFICATIONS:
        {chr(10).join([f"- {pillar}: {count}" for pillar, count in primary_pillars.items()])}
        
        DETAILED NOTE ANALYSIS:
        """
        
        # Add detailed analysis for each note
        for i, result in enumerate(processing_results):
            evaluation_prompt += f"""
        Note {i+1}: {result.raw_note.file_path.name}
        - Content length: {len(result.raw_note.original_content)} chars
        - Evernote cleaning: {'✓' if result.stages[0].success else '✗'} ({result.stages[0].metadata.get('reduction_ratio', 0):.1%} reduction)
        - Preprocessing: {'✓' if result.stages[1].success else '✗'}
        - Content type: {result.stages[1].metadata.get('content_type', 'unknown')}
        - Quality score: {result.stages[1].metadata.get('quality_score', 0):.3f}
        - Should process: {result.stages[1].metadata.get('should_process', False)}
        - Processing reason: {result.stages[1].metadata.get('processing_reason', 'unknown')}
        - LLM analysis: {'✓' if result.final_result else '✗'}
        - Final action: {result.final_result.get('curation_action', 'rejected') if result.final_result else 'rejected'}
        - Primary pillar: {result.final_result.get('primary_pillar', 'none') if result.final_result else 'none'}
        """
        
        evaluation_prompt += """
        
        EVALUATION QUESTIONS:
        
        1. WORKFLOW EFFICACY:
        - Is the preprocessing filtering content appropriately?
        - Are the quality thresholds reasonable?
        - Is the system too strict or too lenient?
        
        2. CONTENT QUALITY ASSESSMENT:
        - Are quality scores reflecting actual content value?
        - Are good notes being rejected inappropriately?
        - Is the word count minimum (20 words) appropriate?
        
        3. ALIGNMENT WITH EXPERT GOALS:
        - Does the system serve infrastructure/PPP expert needs?
        - Are pillar classifications accurate and useful?
        - Do curation actions make sense for knowledge management?
        
        4. PERFORMANCE ANALYSIS:
        - Is the processing time acceptable?
        - Is the 60% success rate good for this type of content?
        - Are there bottlenecks or inefficiencies?
        
        5. RECOMMENDATIONS:
        - What specific improvements would enhance the system?
        - Should quality thresholds be adjusted?
        - What additional features would be valuable?
        
        Please provide a structured evaluation with specific insights and actionable recommendations.
        """
        
        # Use a direct approach - create a simple evaluation file
        evaluation_file = Path("system_evaluation.md")
        with open(evaluation_file, 'w', encoding='utf-8') as f:
            f.write(evaluation_prompt)
        
        # Use the new generic completion method for meta-evaluation
        evaluation_result = llm_manager.complete_prompt(
            evaluation_prompt,
            model_type='detailed_analysis',
            max_tokens=1024,
            temperature=0.2
        )
        
        evaluation_file.unlink(missing_ok=True)
        
        evaluation_time = time.time() - start_time
        
        return {
            'evaluation_prompt': evaluation_prompt,
            'evaluation_result': evaluation_result,
            'evaluation_time': evaluation_time,
            'success': True,
            'analysis_summary': {
                'total_notes': total_notes,
                'successful_llm': successful_llm,
                'success_rate': successful_llm/total_notes,
                'total_time': total_time,
                'avg_time': avg_time,
                'content_types': content_types,
                'quality_scores': {
                    'average': sum(quality_scores)/len(quality_scores) if quality_scores else 0,
                    'min': min(quality_scores) if quality_scores else 0,
                    'max': max(quality_scores) if quality_scores else 0
                },
                'processing_reasons': processing_reasons,
                'final_actions': final_actions,
                'primary_pillars': primary_pillars
            }
        }
        
    except Exception as e:
        evaluation_time = time.time() - start_time
        console.print(f"[red]Error during LLM evaluation: {e}[/red]")
        
        return {
            'evaluation_prompt': "Error occurred during evaluation",
            'evaluation_result': {'error': str(e)},
            'evaluation_time': evaluation_time,
            'success': False
        }


def display_evaluation_results(processing_results: List[CompleteProcessing], evaluation: Dict[str, Any]):
    """Display the evaluation results."""
    console.print(Panel.fit(
        Text("📊 Self-Evaluation Results", style="bold blue"),
        subtitle="LLM Analysis of Pipeline Efficacy"
    ))
    
    # Display summary
    summary_table = Table(title="Pipeline Performance Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta")
    
    if 'analysis_summary' in evaluation:
        summary = evaluation['analysis_summary']
        summary_table.add_row("Total Notes", str(summary['total_notes']))
        summary_table.add_row("LLM Success Rate", f"{summary['success_rate']:.1%}")
        summary_table.add_row("Total Processing Time", f"{summary['total_time']:.2f}s")
        summary_table.add_row("Average Time per Note", f"{summary['avg_time']:.2f}s")
        summary_table.add_row("Evaluation Time", f"{evaluation['evaluation_time']:.2f}s")
        summary_table.add_row("Average Quality Score", f"{summary['quality_scores']['average']:.3f}")
    else:
        # Fallback to basic stats
        total_notes = len(processing_results)
        successful_llm = sum(1 for r in processing_results if r.final_result is not None)
        total_time = sum(r.total_processing_time for r in processing_results)
        
        summary_table.add_row("Total Notes", str(total_notes))
        summary_table.add_row("LLM Success Rate", f"{successful_llm/total_notes:.1%}")
        summary_table.add_row("Total Processing Time", f"{total_time:.2f}s")
        summary_table.add_row("Average Time per Note", f"{total_time/total_notes:.2f}s")
        summary_table.add_row("Evaluation Time", f"{evaluation['evaluation_time']:.2f}s")
    
    console.print(summary_table)
    
    # Display detailed analysis if available
    if 'analysis_summary' in evaluation:
        summary = evaluation['analysis_summary']
        
        # Content type distribution
        if summary['content_types']:
            content_table = Table(title="Content Type Distribution")
            content_table.add_column("Content Type", style="cyan")
            content_table.add_column("Count", style="magenta")
            for ctype, count in summary['content_types'].items():
                content_table.add_row(ctype, str(count))
            console.print(content_table)
        
        # Processing decisions
        if summary['processing_reasons']:
            reason_table = Table(title="Processing Decisions")
            reason_table.add_column("Reason", style="cyan")
            reason_table.add_column("Count", style="magenta")
            for reason, count in summary['processing_reasons'].items():
                reason_table.add_row(reason, str(count))
            console.print(reason_table)
        
        # Final actions
        if summary['final_actions']:
            action_table = Table(title="Final Curation Actions")
            action_table.add_column("Action", style="cyan")
            action_table.add_column("Count", style="magenta")
            for action, count in summary['final_actions'].items():
                action_table.add_row(action, str(count))
            console.print(action_table)
    
    # Display LLM evaluation
    if evaluation['success']:
        console.print("\n[bold]🤖 LLM Evaluation:[/bold]")
        
        result = evaluation['evaluation_result']
        if 'curation_reasoning' in result:
            console.print(result['curation_reasoning'])
        elif 'error' in result:
            console.print(f"[red]Evaluation error: {result['error']}[/red]")
        else:
            console.print(json.dumps(result, indent=2, default=str))
    else:
        console.print(f"[red]Evaluation failed: {evaluation['evaluation_result'].get('error', 'Unknown error')}[/red]")


def save_evaluation_results(processing_results: List[CompleteProcessing], evaluation: Dict[str, Any]):
    """Save the evaluation results."""
    output_dir = Path("results/self_evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed processing results
    detailed_file = output_dir / f"detailed_processing_{timestamp}.json"
    with open(detailed_file, 'w', encoding='utf-8') as f:
        detailed_data = []
        for result in processing_results:
            result_dict = {
                'file_path': str(result.raw_note.file_path),
                'raw_note': asdict(result.raw_note),
                'stages': [asdict(stage) for stage in result.stages],
                'final_result': result.final_result,
                'total_processing_time': result.total_processing_time
            }
            detailed_data.append(result_dict)
        
        json.dump(detailed_data, f, indent=2, default=str)
    
    # Save evaluation results
    evaluation_file = output_dir / f"llm_evaluation_{timestamp}.json"
    with open(evaluation_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, default=str)
    
    # Save summary
    summary_file = output_dir / f"evaluation_summary_{timestamp}.json"
    summary_data = {
        'timestamp': timestamp,
        'total_notes': len(processing_results),
        'successful_llm': sum(1 for r in processing_results if r.final_result is not None),
        'success_rate': sum(1 for r in processing_results if r.final_result is not None) / len(processing_results),
        'total_processing_time': sum(r.total_processing_time for r in processing_results),
        'average_time_per_note': sum(r.total_processing_time for r in processing_results) / len(processing_results),
        'evaluation_time': evaluation['evaluation_time'],
        'evaluation_success': evaluation['success']
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    console.print(f"\n[green]✅ Self-evaluation results saved![/green]")
    console.print(f"📄 Detailed processing: {detailed_file}")
    console.print(f"📄 LLM evaluation: {evaluation_file}")
    console.print(f"📄 Summary: {summary_file}")


def main():
    """Main self-evaluating test function."""
    console.print(Panel.fit(
        Text("🔬 Self-Evaluating Pipeline Test", style="bold blue"),
        subtitle="LLM-Powered Analysis of Workflow Efficacy"
    ))
    
    try:
        # Load configuration
        config = load_config()
        vault_path = Path(config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[blue]Vault path: {vault_path}[/blue]")
        
        # Find and load sample notes (larger sample for detailed analysis)
        sample_size = 13
        console.print(f"\n[yellow]Finding {sample_size} sample notes for detailed analysis...[/yellow]")
        
        notes = find_sample_notes(vault_path, sample_size)
        console.print(f"Found {len(notes)} notes for evaluation")
        
        # Load raw notes
        console.print("\n[yellow]Loading raw note content...[/yellow]")
        raw_notes = load_raw_notes(notes)
        console.print(f"Loaded {len(raw_notes)} raw notes")
        
        # Process each note completely
        console.print("\n[bold blue]🔄 Processing Notes with Complete Tracking[/bold blue]")
        processing_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Processing notes...", total=len(raw_notes))
            
            for raw_note in raw_notes:
                progress.update(task, description=f"Processing {raw_note.file_path.name[:30]}...")
                
                result = process_note_complete(raw_note)
                processing_results.append(result)
                
                progress.advance(task)
        
        # Use LLM to evaluate the results
        evaluation = evaluate_with_llm(processing_results)
        
        # Display results
        display_evaluation_results(processing_results, evaluation)
        
        # Save results
        save_evaluation_results(processing_results, evaluation)
        
        console.print("\n[bold green]✅ Self-evaluating test completed![/bold green]")
        console.print("\n[bold]📋 What this evaluation provides:[/bold]")
        console.print("• Complete workflow analysis with LLM insights")
        console.print("• Efficacy assessment against app goals")
        console.print("• Quality evaluation of transformations")
        console.print("• Performance analysis and bottlenecks")
        console.print("• Actionable recommendations for improvement")
        console.print("• Self-improving feedback loop")
        
    except Exception as e:
        console.print(f"[red]❌ Error during self-evaluation: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 