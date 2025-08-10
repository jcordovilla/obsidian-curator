#!/usr/bin/env python3
"""
Validation Results Analyzer for Human-in-the-Loop Feedback

This script analyzes multiple human validation sessions to:
1. Track system performance over time
2. Identify patterns in human-AI disagreements
3. Generate actionable improvement recommendations
4. Provide validation metrics and trends
5. Support iterative system improvement

Usage:
    poetry run python scripts/analyze_validation_results.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
# from rich.chart import BarChart  # Optional chart functionality
from rich.layout import Layout

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

console = Console()


@dataclass
class ValidationMetrics:
    """Aggregated validation metrics."""
    total_sessions: int
    total_notes: int
    overall_agreement_rate: float
    average_confidence: float
    score_correlation: float
    most_common_disagreements: List[tuple]
    improvement_trend: str
    session_dates: List[str]


class ValidationAnalyzer:
    """Analyzer for human validation results."""
    
    def __init__(self, results_dir: Path = Path("results")):
        """Initialize the analyzer."""
        self.results_dir = results_dir
        self.validation_dir = results_dir / "human_validation"
        
        if not self.validation_dir.exists():
            console.print(f"[red]Validation directory not found: {self.validation_dir}[/red]")
            console.print("Run the review tool first to generate validation data.")
            sys.exit(1)
    
    def find_validation_files(self) -> List[Path]:
        """Find all validation result files."""
        pattern = "human_validation_*.json"
        validation_files = list(self.validation_dir.glob(pattern))
        
        if not validation_files:
            console.print(f"[red]No validation files found in {self.validation_dir}[/red]")
            console.print("Run the review tool first to generate validation data.")
            sys.exit(1)
        
        # Sort by modification time (newest first)
        validation_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        console.print(f"Found {len(validation_files)} validation sessions")
        return validation_files
    
    def load_validation_session(self, filepath: Path) -> Dict[str, Any]:
        """Load a single validation session."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            console.print(f"[red]Error loading {filepath.name}: {e}[/red]")
            return {}
    
    def load_all_sessions(self, filepaths: List[Path]) -> List[Dict[str, Any]]:
        """Load all validation sessions."""
        sessions = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading validation sessions...", total=len(filepaths))
            
            for filepath in filepaths:
                session_data = self.load_validation_session(filepath)
                if session_data:
                    sessions.append(session_data)
                progress.update(task, advance=1)
        
        console.print(f"✓ Loaded {len(sessions)} valid sessions")
        return sessions
    
    def calculate_aggregate_metrics(self, sessions: List[Dict[str, Any]]) -> ValidationMetrics:
        """Calculate aggregate metrics across all sessions."""
        total_sessions = len(sessions)
        total_notes = sum(len(s.get('validation_data', [])) for s in sessions)
        
        # Agreement rates
        agreement_rates = []
        confidence_scores = []
        score_correlations = []
        session_dates = []
        
        # Track disagreements
        all_disagreements = []
        
        for session in sessions:
            validation_data = session.get('validation_data', [])
            if not validation_data:
                continue
            
            # Agreement rate
            agreements = sum(1 for v in validation_data if v.get('agreement', False))
            agreement_rate = agreements / len(validation_data)
            agreement_rates.append(agreement_rate)
            
            # Confidence scores
            human_confidences = [v.get('human_confidence', 0) for v in validation_data]
            if human_confidences:
                confidence_scores.extend(human_confidences)
            
            # Score correlation
            ai_scores = [v.get('ai_score', 0) for v in validation_data]
            human_scores = [v.get('human_score', 0) for v in validation_data]
            if len(ai_scores) > 1:
                correlation = self._calculate_correlation(ai_scores, human_scores)
                score_correlations.append(correlation)
            
            # Session date
            start_time = session.get('start_time', '')
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    session_dates.append(dt.strftime('%Y-%m-%d'))
                except:
                    pass
            
            # Track disagreements
            for v in validation_data:
                if not v.get('agreement', True):
                    ai_action = v.get('ai_action', 'unknown')
                    human_action = v.get('human_action', 'unknown')
                    if ai_action != human_action:
                        all_disagreements.append((ai_action, human_action))
        
        # Calculate aggregate metrics
        overall_agreement_rate = sum(agreement_rates) / len(agreement_rates) if agreement_rates else 0.0
        average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        score_correlation = sum(score_correlations) / len(score_correlations) if score_correlations else 0.0
        
        # Most common disagreements
        disagreement_counts = Counter(all_disagreements)
        most_common_disagreements = disagreement_counts.most_common(5)
        
        # Improvement trend
        if len(agreement_rates) >= 2:
            recent_rate = agreement_rates[0]
            older_rate = agreement_rates[-1]
            if recent_rate > older_rate + 0.1:
                improvement_trend = "Improving"
            elif recent_rate < older_rate - 0.1:
                improvement_trend = "Declining"
            else:
                improvement_trend = "Stable"
        else:
            improvement_trend = "Insufficient data"
        
        return ValidationMetrics(
            total_sessions=total_sessions,
            total_notes=total_notes,
            overall_agreement_rate=overall_agreement_rate,
            average_confidence=average_confidence,
            score_correlation=score_correlation,
            most_common_disagreements=most_common_disagreements,
            improvement_trend=improvement_trend,
            session_dates=session_dates
        )
    
    def _calculate_correlation(self, scores1: List[float], scores2: List[float]) -> float:
        """Calculate correlation between two score lists."""
        if len(scores1) != len(scores2) or len(scores1) < 2:
            return 0.0
        
        n = len(scores1)
        sum1, sum2, sum1_sq, sum2_sq, sum_prod = 0, 0, 0, 0, 0
        
        for s1, s2 in zip(scores1, scores2):
            sum1 += s1
            sum2 += s2
            sum1_sq += s1 * s1
            sum2_sq += s2 * s2
            sum_prod += s1 * s2
        
        numerator = n * sum_prod - sum1 * sum2
        denominator = ((n * sum1_sq - sum1 * sum1) * (n * sum2_sq - sum2 * sum2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def display_overview(self, metrics: ValidationMetrics):
        """Display overview of validation metrics."""
        console.print(f"\n[bold blue]📊 Validation Overview[/bold blue]")
        console.print("=" * 60)
        
        # Basic metrics
        console.print(f"Total Sessions: {metrics.total_sessions}")
        console.print(f"Total Notes Validated: {metrics.total_notes}")
        console.print(f"Overall Agreement Rate: {metrics.overall_agreement_rate:.1%}")
        console.print(f"Average Human Confidence: {metrics.average_confidence:.1f}/5.0")
        console.print(f"Score Correlation: {metrics.score_correlation:.3f}")
        console.print(f"Improvement Trend: {metrics.improvement_trend}")
        
        # Session timeline
        if metrics.session_dates:
            console.print(f"\n[bold]📅 Session Timeline:[/bold]")
            unique_dates = sorted(list(set(metrics.session_dates)))
            for date in unique_dates:
                count = metrics.session_dates.count(date)
                console.print(f"  {date}: {count} session(s)")
    
    def display_disagreement_analysis(self, metrics: ValidationMetrics):
        """Display analysis of human-AI disagreements."""
        console.print(f"\n[bold blue]⚠️  Disagreement Analysis[/bold blue]")
        console.print("=" * 60)
        
        if not metrics.most_common_disagreements:
            console.print("✅ No disagreements found in validation data")
            return
        
        console.print("Most Common Action Disagreements:")
        table = Table(title="Action Transition Disagreements")
        table.add_column("AI Action", style="cyan")
        table.add_column("Human Action", style="green")
        table.add_column("Count", style="yellow")
        table.add_column("Percentage", style="magenta")
        
        total_disagreements = sum(count for _, count in metrics.most_common_disagreements)
        
        for (ai_action, human_action), count in metrics.most_common_disagreements:
            percentage = (count / total_disagreements) * 100
            table.add_row(ai_action, human_action, str(count), f"{percentage:.1f}%")
        
        console.print(table)
        
        # Provide insights
        console.print(f"\n[bold]💡 Insights:[/bold]")
        for (ai_action, human_action), count in metrics.most_common_disagreements[:3]:
            if ai_action == "archive" and human_action == "keep":
                console.print(f"  • AI is archiving notes that humans want to keep - consider relaxing thresholds")
            elif ai_action == "keep" and human_action == "archive":
                console.print(f"  • AI is keeping notes that humans want to archive - consider tightening thresholds")
            elif ai_action == "delete" and human_action in ["keep", "refine"]:
                console.print(f"  • AI is deleting notes that humans want to preserve - review deletion criteria")
            else:
                console.print(f"  • Review {ai_action}→{human_action} transitions ({count} cases)")
    
    def display_session_comparison(self, sessions: List[Dict[str, Any]]):
        """Display comparison between sessions."""
        console.print(f"\n[bold blue]📈 Session Comparison[/bold blue]")
        console.print("=" * 60)
        
        if len(sessions) < 2:
            console.print("Need at least 2 sessions for comparison")
            return
        
        # Create comparison table
        table = Table(title="Session Performance Comparison")
        table.add_column("Session", style="cyan")
        table.add_column("Date", style="green")
        table.add_column("Notes", style="yellow")
        table.add_column("Agreement", style="magenta")
        table.add_column("Avg Confidence", style="blue")
        
        for i, session in enumerate(sessions[:5]):  # Show last 5 sessions
            session_id = session.get('session_id', f'Session {i+1}')
            start_time = session.get('start_time', 'Unknown')
            notes_count = len(session.get('validation_data', []))
            
            # Calculate agreement rate
            validation_data = session.get('validation_data', [])
            if validation_data:
                agreements = sum(1 for v in validation_data if v.get('agreement', False))
                agreement_rate = agreements / len(validation_data)
                
                # Calculate average confidence
                confidences = [v.get('human_confidence', 0) for v in validation_data]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            else:
                agreement_rate = 0.0
                avg_confidence = 0.0
            
            # Format date
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = start_time[:16]
            
            table.add_row(
                session_id,
                date_str,
                str(notes_count),
                f"{agreement_rate:.1%}",
                f"{avg_confidence:.1f}"
            )
        
        console.print(table)
    
    def generate_improvement_recommendations(self, metrics: ValidationMetrics, sessions: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable improvement recommendations."""
        recommendations = []
        
        # Agreement rate recommendations
        if metrics.overall_agreement_rate < 0.6:
            recommendations.append("🚨 CRITICAL: Overall agreement rate below 60% - fundamental system review needed")
        elif metrics.overall_agreement_rate < 0.8:
            recommendations.append("⚠️  WARNING: Agreement rate below 80% - consider threshold adjustments")
        
        # Score correlation recommendations
        if metrics.score_correlation < 0.3:
            recommendations.append("📊 Poor score correlation - review quality scoring algorithm")
        elif metrics.score_correlation < 0.6:
            recommendations.append("📊 Moderate score correlation - consider improving scoring criteria")
        
        # Confidence recommendations
        if metrics.average_confidence < 3.0:
            recommendations.append("🤔 Low human confidence - review decision criteria clarity")
        
        # Trend recommendations
        if metrics.improvement_trend == "Declining":
            recommendations.append("📉 Performance declining - investigate recent changes")
        elif metrics.improvement_trend == "Improving":
            recommendations.append("📈 Performance improving - continue current approach")
        
        # Specific disagreement recommendations
        if metrics.most_common_disagreements:
            top_disagreement = metrics.most_common_disagreements[0]
            ai_action, human_action = top_disagreement[0]
            count = top_disagreement[1]
            
            if count > 2:  # If this happens in multiple sessions
                if ai_action == "archive" and human_action == "keep":
                    recommendations.append("🔧 Relax archive thresholds - AI too aggressive")
                elif ai_action == "keep" and human_action == "archive":
                    recommendations.append("🔧 Tighten keep thresholds - AI too lenient")
                elif ai_action == "delete" and human_action in ["keep", "refine"]:
                    recommendations.append("🔧 Review deletion criteria - AI too aggressive")
        
        # Data quality recommendations
        if metrics.total_notes < 20:
            recommendations.append("📊 Limited validation data - consider more validation sessions")
        
        if metrics.total_sessions < 3:
            recommendations.append("📊 Limited session history - continue validation to establish trends")
        
        if not recommendations:
            recommendations.append("✅ System performing well - continue monitoring and validation")
        
        return recommendations
    
    def save_analysis_report(self, metrics: ValidationMetrics, sessions: List[Dict[str, Any]], recommendations: List[str]):
        """Save analysis report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_analysis_{timestamp}.json"
        filepath = self.validation_dir / filename
        
        report = {
            "analysis_metadata": {
                "timestamp": timestamp,
                "total_sessions": metrics.total_sessions,
                "total_notes": metrics.total_notes,
                "analysis_version": "1.0"
            },
            "metrics": {
                "overall_agreement_rate": metrics.overall_agreement_rate,
                "average_confidence": metrics.average_confidence,
                "score_correlation": metrics.score_correlation,
                "improvement_trend": metrics.improvement_trend
            },
            "disagreements": [
                {"ai_action": ai, "human_action": human, "count": count}
                for (ai, human), count in metrics.most_common_disagreements
            ],
            "session_summary": [
                {
                    "session_id": s.get("session_id"),
                    "start_time": s.get("start_time"),
                    "notes_count": len(s.get("validation_data", [])),
                    "agreement_rate": self._calculate_session_agreement(s)
                }
                for s in sessions[:10]  # Last 10 sessions
            ],
            "recommendations": recommendations
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            console.print(f"\n[green]✅ Analysis report saved to: {filepath}[/green]")
            
        except Exception as e:
            console.print(f"[red]Error saving report: {e}[/red]")
    
    def _calculate_session_agreement(self, session: Dict[str, Any]) -> float:
        """Calculate agreement rate for a single session."""
        validation_data = session.get('validation_data', [])
        if not validation_data:
            return 0.0
        
        agreements = sum(1 for v in validation_data if v.get('agreement', False))
        return agreements / len(validation_data)


def main():
    """Main function to run the validation analyzer."""
    try:
        analyzer = ValidationAnalyzer()
        
        console.print("[bold blue]🔬 Validation Results Analyzer[/bold blue]")
        console.print("=" * 50)
        
        # Find validation files
        validation_files = analyzer.find_validation_files()
        
        # Load all sessions
        sessions = analyzer.load_all_sessions(validation_files)
        
        if not sessions:
            console.print("[red]No valid sessions found[/red]")
            sys.exit(1)
        
        # Calculate metrics
        console.print("\n[green]Calculating aggregate metrics...[/green]")
        metrics = analyzer.calculate_aggregate_metrics(sessions)
        
        # Display analysis
        analyzer.display_overview(metrics)
        analyzer.display_disagreement_analysis(metrics)
        analyzer.display_session_comparison(sessions)
        
        # Generate recommendations
        recommendations = analyzer.generate_improvement_recommendations(metrics, sessions)
        console.print(f"\n[bold]💡 Improvement Recommendations:[/bold]")
        for i, rec in enumerate(recommendations, 1):
            console.print(f"  {i}. {rec}")
        
        # Save report
        if Confirm.ask("\nSave analysis report?", default=True):
            analyzer.save_analysis_report(metrics, sessions, recommendations)
        
        console.print(f"\n[bold green]🎉 Analysis completed![/bold green]")
        console.print(f"Analyzed {len(sessions)} validation sessions")
        console.print(f"Total notes: {metrics.total_notes}")
        console.print(f"Overall agreement: {metrics.overall_agreement_rate:.1%}")
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Analysis interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error during analysis: {e}[/red]")
        if Confirm.ask("Show full error details?", default=False):
            console.print_exception()


if __name__ == "__main__":
    main()
