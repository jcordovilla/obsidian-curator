#!/usr/bin/env python3
"""
Human Validation Interface for Classification Results

This script provides an interactive interface for humans to validate
AI-generated classification results for Obsidian notes.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

@dataclass
class ClassificationValidation:
    """Human validation data for a single note classification."""
    note_id: str
    file_path: str
    ai_primary_pillar: Optional[str]
    ai_note_type: Optional[str]
    ai_curation_action: str
    ai_confidence: float
    ai_quality_scores: Dict[str, float]
    ai_reasoning: str
    
    human_primary_pillar: Optional[str]
    human_note_type: Optional[str]
    human_curation_action: str
    human_confidence: int  # 1-5 scale
    human_quality_scores: Dict[str, float]
    human_reasoning: str
    
    agreement: bool
    validation_timestamp: str

@dataclass
class ValidationSession:
    """Complete validation session data."""
    session_id: str
    start_time: str
    end_time: str
    total_notes: int
    validated_notes: int
    agreement_rate: float
    human_corrections: int
    validation_data: List[ClassificationValidation]
    session_notes: str

class ClassificationValidator:
    """Interface for human validation of AI classification results."""
    
    def __init__(self, results_dir: Path = Path("results"), vault_path: Optional[str] = None):
        self.results_dir = Path(results_dir)
        self.vault_path = vault_path
        self.console = Console()
        
        # Available options for human validation
        self.available_pillars = [
            "ppp_fundamentals",
            "operational_risk", 
            "value_for_money",
            "digital_transformation",
            "governance_transparency",
            "None"
        ]
        
        self.available_note_types = [
            "literature_research",
            "project_workflow",
            "personal_reflection", 
            "technical_code",
            "meeting_template",
            "community_event",
            "None"
        ]
        
        self.available_actions = [
            "keep",
            "refine", 
            "archive",
            "delete"
        ]
    
    def select_results_source(self) -> Path:
        """Let user select which classification results to validate."""
        test_runs_dir = self.results_dir / "test_runs"
        
        if not test_runs_dir.exists():
            self.console.print("[red]No test_runs directory found[/red]")
            return None
        
        # Find classification test results
        classification_files = list(test_runs_dir.glob("*classification_test*.json"))
        
        if not classification_files:
            self.console.print("[red]No classification test results found[/red]")
            return None
        
        if len(classification_files) == 1:
            return classification_files[0]
        
        # Let user choose
        self.console.print("\n[bold]Available classification test results:[/bold]")
        for i, file_path in enumerate(classification_files, 1):
            self.console.print(f"{i}. {file_path.name}")
        
        choice = IntPrompt.ask(
            "Select classification results to validate",
            choices=[str(i) for i in range(1, len(classification_files) + 1)]
        )
        
        return classification_files[choice - 1]
    
    def load_results(self, source_file: Path) -> Dict[str, Any]:
        """Load classification results from file."""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.console.print(f"[red]Error loading results: {e}[/red]")
            return None
    
    def read_note_content(self, file_path: str) -> Optional[str]:
        """Read the actual note content from the vault."""
        try:
            if not self.vault_path:
                self.console.print("[yellow]Warning: No vault path specified, cannot read note content[/yellow]")
                return None
            
            full_path = Path(self.vault_path) / file_path.replace(self.vault_path, "").lstrip("/")
            
            if not full_path.exists():
                self.console.print(f"[yellow]Warning: Note file not found: {full_path}[/yellow]")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "\n\n... [Content truncated for display] ..."
                
            return content
            
        except Exception as e:
            self.console.print(f"[red]Error reading note content: {e}[/red]")
            return None
    
    def start_validation_session(self, results_data: Dict[str, Any]) -> ValidationSession:
        """Start a new validation session."""
        session_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ValidationSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time="",
            total_notes=len(results_data.get('batches', [{}])[0].get('notes', [])),
            validated_notes=0,
            agreement_rate=0.0,
            human_corrections=0,
            validation_data=[],
            session_notes=""
        )
    
    def display_note_for_validation(self, note_data: Dict[str, Any], note_index: int, total_notes: int) -> ClassificationValidation:
        """Display a single note for human validation."""
        self.console.print("\n" + "="*80)
        self.console.print(f"NOTE {note_index + 1} OF {total_notes}")
        self.console.print("="*80)
        
        # Display file metadata
        file_name = note_data.get('file_name', 'Unknown')
        file_path = note_data.get('file_path', 'Unknown')
        
        self.console.print(f"\n📁 FILE: {file_name}")
        self.console.print(f"📍 PATH: {file_path}")
        
        # Display note content if available
        note_content = self.read_note_content(file_path)
        if note_content:
            self.console.print(f"\n📝 NOTE CONTENT:")
            self.console.print("-" * 40)
            self.console.print(note_content)
        else:
            self.console.print("\n❌ Note content not available")
        
        # Display AI classification results
        ai_primary_pillar = note_data.get('primary_pillar')
        ai_note_type = note_data.get('note_type')
        ai_curation_action = note_data.get('curation_action', 'Unknown')
        ai_confidence = note_data.get('confidence', 0.0)
        ai_quality_scores = note_data.get('quality_scores', {})
        ai_reasoning = note_data.get('curation_reasoning', 'No reasoning provided')
        
        self.console.print(f"\n🤖 AI CLASSIFICATION RESULTS:")
        self.console.print("-" * 40)
        self.console.print(f"Primary Pillar: {ai_primary_pillar or 'None'}")
        self.console.print(f"Note Type: {ai_note_type or 'None'}")
        self.console.print(f"Curation Action: {ai_curation_action}")
        self.console.print(f"Confidence: {ai_confidence:.3f}")
        
        if ai_quality_scores:
            self.console.print(f"\nQuality Scores:")
            for metric, score in ai_quality_scores.items():
                if metric != 'overall_score':
                    self.console.print(f"  {metric}: {score:.3f}")
            if 'overall_score' in ai_quality_scores:
                self.console.print(f"  Overall: {ai_quality_scores['overall_score']:.3f}")
        
        self.console.print(f"\nAI Reasoning: {ai_reasoning}")
        
        # Get human validation
        self.console.print(f"\n👤 [bold]HUMAN VALIDATION:[/bold]")
        
        # Primary pillar validation
        human_primary_pillar = Prompt.ask(
            "What is the primary pillar for this note?",
            choices=self.available_pillars,
            default=ai_primary_pillar if ai_primary_pillar else "None"
        )
        
        # Note type validation
        human_note_type = Prompt.ask(
            "What type of note is this?",
            choices=self.available_note_types,
            default=ai_note_type if ai_note_type else "None"
        )
        
        # Curation action validation
        human_curation_action = Prompt.ask(
            "What curation action should be taken?",
            choices=self.available_actions,
            default=ai_curation_action
        )
        
        # Confidence rating (1-5 scale)
        human_confidence = IntPrompt.ask(
            "Rate your confidence in this decision (1-5, where 5 is very confident)",
            default=5,
            show_default=True
        )
        
        # Quality scores
        self.console.print(f"\nRate the note quality (0.0-1.0):")
        human_quality_scores = {}
        for metric in ['relevance', 'depth', 'actionability', 'uniqueness', 'structure']:
            if metric in ai_quality_scores:
                default_score = ai_quality_scores[metric]
            else:
                default_score = 0.5
                
            score = float(Prompt.ask(
                f"  {metric.capitalize()}",
                default=f"{default_score:.2f}"
            ))
            human_quality_scores[metric] = score
        
        # Calculate overall score
        if human_quality_scores:
            human_quality_scores['overall_score'] = sum(human_quality_scores.values()) / len(human_quality_scores)
        
        # Reasoning
        human_reasoning = Prompt.ask(
            "Brief reasoning for your decision (optional)",
            default=""
        )
        
        # Calculate agreement
        pillar_agreement = human_primary_pillar == ai_primary_pillar
        type_agreement = human_note_type == ai_note_type
        action_agreement = human_curation_action == ai_curation_action
        
        # Score agreement (within 0.2 tolerance)
        score_agreement = True
        for metric in ['relevance', 'depth', 'actionability', 'uniqueness', 'structure']:
            if metric in ai_quality_scores and metric in human_quality_scores:
                if abs(ai_quality_scores[metric] - human_quality_scores[metric]) > 0.2:
                    score_agreement = False
                    break
        
        agreement = pillar_agreement and type_agreement and action_agreement and score_agreement
        
        # Create validation record
        validation = ClassificationValidation(
            note_id=f"note_{note_index}",
            file_path=file_path,
            ai_primary_pillar=ai_primary_pillar,
            ai_note_type=ai_note_type,
            ai_curation_action=ai_curation_action,
            ai_confidence=ai_confidence,
            ai_quality_scores=ai_quality_scores,
            ai_reasoning=ai_reasoning,
            human_primary_pillar=human_primary_pillar,
            human_note_type=human_note_type,
            human_curation_action=human_curation_action,
            human_confidence=human_confidence,
            human_quality_scores=human_quality_scores,
            human_reasoning=human_reasoning,
            agreement=agreement,
            validation_timestamp=datetime.now().isoformat()
        )
        
        # Display summary
        if agreement:
            self.console.print(f"\n[bold green]✅ Agreement: Human and AI decisions match![/bold green]")
        else:
            self.console.print(f"\n[bold yellow]⚠️  Disagreement: Human and AI decisions differ[/bold yellow]")
            self.console.print(f"  AI: {ai_curation_action} (pillar: {ai_primary_pillar}, type: {ai_note_type})")
            self.console.print(f"  Human: {human_curation_action} (pillar: {human_primary_pillar}, type: {human_note_type})")
        
        return validation
    
    def run_validation(self, results_data: Dict[str, Any]) -> ValidationSession:
        """Run the complete validation process."""
        # Start session
        session = self.start_validation_session(results_data)
        
        # Get notes to review
        notes = results_data.get('batches', [{}])[0].get('notes', [])
        if not notes:
            self.console.print("[red]No notes found in results data[/red]")
            return session
        
        # Ask user how many notes to review
        total_available = len(notes)
        if total_available > 10:
            review_count = IntPrompt.ask(
                f"How many notes would you like to validate? (1-{total_available})",
                default=min(10, total_available),
                show_default=True
            )
        else:
            review_count = total_available
        
        self.console.print(f"\n[bold]Starting validation of {review_count} notes...[/bold]")
        
        # Review each note
        for i in range(min(review_count, total_available)):
            note_data = notes[i]
            
            try:
                validation = self.display_note_for_validation(note_data, i, total_available)
                session.validation_data.append(validation)
                session.validated_notes += 1
                
                if not validation.agreement:
                    session.human_corrections += 1
                
                # Ask if user wants to continue
                if i < min(review_count, total_available) - 1:
                    if not Confirm.ask("Continue to next note?"):
                        break
                        
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Validation interrupted by user[/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[red]Error validating note {i+1}: {e}[/red]")
                continue
        
        # End session
        session.end_time = datetime.now().isoformat()
        
        # Calculate final statistics
        if session.validated_notes > 0:
            session.agreement_rate = (session.validated_notes - session.human_corrections) / session.validated_notes
        
        return session
    
    def display_validation_summary(self, session: ValidationSession):
        """Display a summary of the validation session."""
        self.console.print("\n" + "="*80)
        self.console.print("VALIDATION SESSION SUMMARY")
        self.console.print("="*80)
        
        # Basic stats
        self.console.print(f"\n📊 Session Statistics:")
        self.console.print(f"  Session ID: {session.session_id}")
        self.console.print(f"  Start Time: {session.start_time}")
        self.console.print(f"  End Time: {session.end_time}")
        self.console.print(f"  Total Notes: {session.total_notes}")
        self.console.print(f"  Validated Notes: {session.validated_notes}")
        self.console.print(f"  Agreement Rate: {session.agreement_rate:.1%}")
        self.console.print(f"  Human Corrections: {session.human_corrections}")
        
        # Agreement breakdown
        if session.validation_data:
            self.console.print(f"\n🔍 Agreement Breakdown:")
            
            # Pillar agreement
            pillar_agreements = sum(1 for v in session.validation_data 
                                  if v.ai_primary_pillar == v.human_primary_pillar)
            pillar_rate = pillar_agreements / len(session.validation_data)
            self.console.print(f"  Primary Pillar: {pillar_rate:.1%}")
            
            # Note type agreement
            type_agreements = sum(1 for v in session.validation_data 
                                if v.ai_note_type == v.human_note_type)
            type_rate = type_agreements / len(session.validation_data)
            self.console.print(f"  Note Type: {type_rate:.1%}")
            
            # Curation action agreement
            action_agreements = sum(1 for v in session.validation_data 
                                  if v.ai_curation_action == v.human_curation_action)
            action_rate = action_agreements / len(session.validation_data)
            self.console.print(f"  Curation Action: {action_rate:.1%}")
            
            # Quality score correlation
            if any(v.ai_quality_scores and v.human_quality_scores for v in session.validation_data):
                ai_scores = []
                human_scores = []
                for v in session.validation_data:
                    if v.ai_quality_scores and v.human_quality_scores:
                        if 'overall_score' in v.ai_quality_scores and 'overall_score' in v.human_quality_scores:
                            ai_scores.append(v.ai_quality_scores['overall_score'])
                            human_scores.append(v.human_quality_scores['overall_score'])
                
                if ai_scores and human_scores:
                    correlation = self._calculate_correlation(ai_scores, human_scores)
                    self.console.print(f"  Quality Score Correlation: {correlation:.3f}")
        
        # Detailed results table
        if session.validation_data:
            self.console.print(f"\n📋 Detailed Results:")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Note")
            table.add_column("AI Pillar")
            table.add_column("Human Pillar")
            table.add_column("AI Type")
            table.add_column("Human Type")
            table.add_column("AI Action")
            table.add_column("Human Action")
            table.add_column("Agreement")
            
            for validation in session.validation_data:
                note_name = Path(validation.file_path).name[:30] + "..." if len(Path(validation.file_path).name) > 30 else Path(validation.file_path).name
                
                table.add_row(
                    note_name,
                    str(validation.ai_primary_pillar or "None"),
                    str(validation.human_primary_pillar or "None"),
                    str(validation.ai_note_type or "None"),
                    str(validation.human_note_type or "None"),
                    validation.ai_curation_action,
                    validation.human_curation_action,
                    "✅" if validation.agreement else "❌"
                )
            
            self.console.print(table)
    
    def _calculate_correlation(self, scores1: List[float], scores2: List[float]) -> float:
        """Calculate correlation coefficient between two score lists."""
        if len(scores1) != len(scores2) or len(scores1) < 2:
            return 0.0
        
        n = len(scores1)
        sum1 = sum(scores1)
        sum2 = sum(scores2)
        sum1_sq = sum(x * x for x in scores1)
        sum2_sq = sum(x * x for x in scores2)
        sum_xy = sum(x * y for x, y in zip(scores1, scores2))
        
        numerator = n * sum_xy - sum1 * sum2
        denominator = ((n * sum1_sq - sum1 * sum1) * (n * sum2_sq - sum2 * sum2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def save_validation_results(self, session: ValidationSession):
        """Save validation results to file."""
        output_dir = self.results_dir / "human_validation"
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"validation_results_{session.session_id}.json"
        
        # Convert to dict for JSON serialization
        session_dict = {
            'session_id': session.session_id,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'total_notes': session.total_notes,
            'validated_notes': session.validated_notes,
            'agreement_rate': session.agreement_rate,
            'human_corrections': session.human_corrections,
            'validation_data': [
                {
                    'note_id': v.note_id,
                    'file_path': v.file_path,
                    'ai_primary_pillar': v.ai_primary_pillar,
                    'ai_note_type': v.ai_note_type,
                    'ai_curation_action': v.ai_curation_action,
                    'ai_confidence': v.ai_confidence,
                    'ai_quality_scores': v.ai_quality_scores,
                    'ai_reasoning': v.ai_reasoning,
                    'human_primary_pillar': v.human_primary_pillar,
                    'human_note_type': v.human_note_type,
                    'human_curation_action': v.human_curation_action,
                    'human_confidence': v.human_confidence,
                    'human_quality_scores': v.human_quality_scores,
                    'human_reasoning': v.human_reasoning,
                    'agreement': v.agreement,
                    'validation_timestamp': v.validation_timestamp
                }
                for v in session.validation_data
            ],
            'session_notes': session.session_notes
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)
            
            self.console.print(f"\n[green]Validation results saved to: {output_file}[/green]")
            
        except Exception as e:
            self.console.print(f"\n[red]Error saving results: {e}[/red]")
    
    def generate_improvement_recommendations(self, session: ValidationSession) -> List[str]:
        """Generate recommendations for improving the classification system."""
        recommendations = []
        
        if session.validated_notes == 0:
            return ["No validation data available for recommendations"]
        
        # Analyze agreement rates
        if session.agreement_rate < 0.7:
            recommendations.append("Overall agreement rate is low - consider retraining the model")
        
        # Analyze specific areas
        if session.validation_data:
            pillar_disagreements = sum(1 for v in session.validation_data 
                                     if v.ai_primary_pillar != v.human_primary_pillar)
            pillar_rate = 1 - (pillar_disagreements / len(session.validation_data))
            
            if pillar_rate < 0.8:
                recommendations.append("Primary pillar classification needs improvement")
            
            type_disagreements = sum(1 for v in session.validation_data 
                                   if v.ai_note_type != v.human_note_type)
            type_rate = 1 - (type_disagreements / len(session.validation_data))
            
            if type_rate < 0.8:
                recommendations.append("Note type classification needs improvement")
            
            action_disagreements = sum(1 for v in session.validation_data 
                                     if v.ai_curation_action != v.human_curation_action)
            action_rate = 1 - (action_disagreements / len(session.validation_data))
            
            if action_rate < 0.8:
                recommendations.append("Curation action classification needs improvement")
        
        if not recommendations:
            recommendations.append("Classification system is performing well")
        
        return recommendations

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Human validation interface for classification results")
    parser.add_argument("--results-dir", default="results", help="Directory containing test results")
    parser.add_argument("--vault-path", help="Path to Obsidian vault for reading note content")
    
    args = parser.parse_args()
    
    # Try to auto-detect vault path from results
    vault_path = args.vault_path
    if not vault_path:
        # Check if we can find it in the results
        results_dir = Path(args.results_dir)
        test_runs_dir = results_dir / "test_runs"
        
        if test_runs_dir.exists():
            classification_files = list(test_runs_dir.glob("*classification_test*.json"))
            if classification_files:
                try:
                    with open(classification_files[0], 'r') as f:
                        data = json.load(f)
                        vault_path = data.get('vault_path')
                except:
                    pass
    
    validator = ClassificationValidator(
        results_dir=Path(args.results_dir),
        vault_path=vault_path
    )
    
    # Select results source
    source_file = validator.select_results_source()
    if not source_file:
        console.print("[red]No valid results source found[/red]")
        return
    
    # Load results
    results_data = validator.load_results(source_file)
    if not results_data:
        console.print("[red]Failed to load results data[/red]")
        return
    
    # Run validation
    session = validator.run_validation(results_data)
    
    # Display summary
    validator.display_validation_summary(session)
    
    # Generate recommendations
    recommendations = validator.generate_improvement_recommendations(session)
    console.print(f"\n💡 [bold]Improvement Recommendations:[/bold]")
    for rec in recommendations:
        console.print(f"  • {rec}")
    
    # Save results
    if Confirm.ask("\nSave validation results?"):
        validator.save_validation_results(session)
    
    console.print(f"\n[green]Validation session completed![/green]")

if __name__ == "__main__":
    main()
