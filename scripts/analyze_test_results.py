#!/usr/bin/env python3
"""
Enhanced analysis script for test classification results with preprocessing pipeline analysis.

This script reads the comprehensive preprocessing analysis files from test runs and provides
detailed analysis of the classification system's performance, including all preprocessing stages.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

console = Console()


class ComprehensiveTestAnalyzer:
    """Analyzes comprehensive test results including preprocessing pipeline."""
    
    def __init__(self, results_dir: Path = Path("results/test_runs")):
        """Initialize the analyzer with results directory."""
        self.results_dir = results_dir
        self.latest_comprehensive_file = self._find_latest_comprehensive_file()
        self.data = self._load_comprehensive_data()
    
    def _find_latest_comprehensive_file(self) -> Path:
        """Find the most recent comprehensive preprocessing analysis file."""
        if not self.results_dir.exists():
            console.print(f"[red]Results directory not found: {self.results_dir}[/red]")
            sys.exit(1)
        
        comprehensive_files = list(self.results_dir.glob("comprehensive_preprocessing_analysis_*.json"))
        if not comprehensive_files:
            console.print(f"[red]No comprehensive analysis files found in {self.results_dir}[/red]")
            console.print("[yellow]Falling back to legacy detailed review files...[/yellow]")
            return self._find_latest_legacy_file()
        
        # Sort by modification time and get the latest
        latest_file = max(comprehensive_files, key=lambda f: f.stat().st_mtime)
        console.print(f"[green]Found latest comprehensive analysis: {latest_file.name}[/green]")
        return latest_file
    
    def _find_latest_legacy_file(self) -> Path:
        """Find the most recent legacy detailed review file."""
        review_files = list(self.results_dir.glob("detailed_notes_review_*.json"))
        if not review_files:
            console.print(f"[red]No analysis files found in {self.results_dir}[/red]")
            sys.exit(1)
        
        latest_file = max(review_files, key=lambda f: f.stat().st_mtime)
        console.print(f"[yellow]Using legacy format: {latest_file.name}[/yellow]")
        return latest_file
    
    def _load_comprehensive_data(self) -> Dict[str, Any]:
        """Load comprehensive analysis data."""
        try:
            with open(self.latest_comprehensive_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if this is comprehensive format or legacy format
            if "preprocessing_pipeline" in data:
                console.print("[green]✓ Loaded comprehensive preprocessing analysis data[/green]")
                return data
            else:
                console.print("[yellow]✓ Loaded legacy detailed review data[/yellow]")
                return self._convert_legacy_to_comprehensive(data)
                
        except Exception as e:
            console.print(f"[red]Error loading data: {e}[/red]")
            sys.exit(1)
    
    def _convert_legacy_to_comprehensive(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy format to comprehensive format for analysis."""
        return {
            "test_metadata": {
                "timestamp": legacy_data.get("test_timestamp", "unknown"),
                "total_notes": legacy_data.get("total_notes", 0),
                "test_type": "legacy_converted",
                "system_version": "1.0_legacy"
            },
            "preprocessing_pipeline": {
                "stages": ["legacy_format"],
                "config": {}
            },
            "notes_data": legacy_data.get("notes", [])
        }
    
    def analyze_comprehensive_results(self):
        """Analyze comprehensive test results."""
        console.print("\n[bold blue]🔬 COMPREHENSIVE PREPROCESSING ANALYSIS[/bold blue]")
        console.print("=" * 80)
        
        # Display test metadata
        self._display_test_metadata()
        
        # Analyze preprocessing pipeline
        if "preprocessing_pipeline" in self.data and self.data["preprocessing_pipeline"]["stages"] != ["legacy_format"]:
            self._analyze_preprocessing_pipeline()
        
        # Analyze classification performance
        self._analyze_classification_performance()
        
        # Analyze content quality
        self._analyze_content_quality()
        
        # Analyze preprocessing effectiveness
        if "preprocessing_pipeline" in self.data and self.data["preprocessing_pipeline"]["stages"] != ["legacy_format"]:
            self._analyze_preprocessing_effectiveness()
        
        # Generate recommendations
        self._generate_recommendations()
    
    def _display_test_metadata(self):
        """Display test metadata."""
        metadata = self.data.get("test_metadata", {})
        
        console.print(f"\n[bold cyan]📊 Test Information[/bold cyan]")
        console.print("-" * 40)
        console.print(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
        console.print(f"Total Notes: {metadata.get('total_notes', 0)}")
        console.print(f"Test Type: {metadata.get('test_type', 'Unknown')}")
        console.print(f"System Version: {metadata.get('system_version', 'Unknown')}")
    
    def _analyze_preprocessing_pipeline(self):
        """Analyze the preprocessing pipeline stages."""
        pipeline = self.data.get("preprocessing_pipeline", {})
        stages = pipeline.get("stages", [])
        config = pipeline.get("config", {})
        
        console.print(f"\n[bold cyan]⚙️ Preprocessing Pipeline Analysis[/bold cyan]")
        console.print("-" * 40)
        
        # Display pipeline stages
        console.print(f"Pipeline Stages ({len(stages)}):")
        for i, stage in enumerate(stages, 1):
            console.print(f"  {i}. {stage}")
        
        # Display configuration
        if config:
            console.print(f"\nConfiguration:")
            for key, value in config.items():
                console.print(f"  • {key}: {value}")
    
    def _analyze_classification_performance(self):
        """Analyze classification performance."""
        notes_data = self.data.get("notes_data", [])
        
        if not notes_data:
            console.print("[red]No notes data found[/red]")
            return
        
        console.print(f"\n[bold cyan]🎯 Classification Performance Analysis[/bold cyan]")
        console.print("-" * 40)
        
        # Extract classification data
        total_notes = len(notes_data)
        actions = {}
        pillars = {}
        quality_scores = []
        
        for note in notes_data:
            # Handle both comprehensive and legacy formats
            if "preprocessing_stages" in note:
                # Comprehensive format
                llm_analysis = note["preprocessing_stages"].get("stage_5_llm_analysis", {})
                action = llm_analysis.get("curation_action", "unknown")
                pillar = llm_analysis.get("primary_pillar", "none")
                scores = llm_analysis.get("quality_scores", {})
            else:
                # Legacy format
                action = note.get("curation_action", "unknown")
                pillar = note.get("primary_pillar", "none")
                scores = note.get("quality_scores", {})
            
            actions[action] = actions.get(action, 0) + 1
            pillars[pillar] = pillars.get(pillar, 0) + 1
            
            if scores:
                quality_scores.append(scores.get("relevance", 0))
        
        # Display action distribution
        action_table = Table(title="Curation Actions Distribution")
        action_table.add_column("Action", style="cyan")
        action_table.add_column("Count", style="magenta")
        action_table.add_column("Percentage", style="green")
        
        for action, count in sorted(actions.items()):
            percentage = (count / total_notes) * 100
            action_table.add_row(action, str(count), f"{percentage:.1f}%")
        
        console.print(action_table)
        
        # Display pillar distribution
        pillar_table = Table(title="Primary Pillar Distribution")
        pillar_table.add_column("Pillar", style="cyan")
        pillar_table.add_column("Count", style="magenta")
        pillar_table.add_column("Percentage", style="green")
        
        for pillar, count in sorted(pillars.items()):
            percentage = (count / total_notes) * 100
            pillar_table.add_row(pillar, str(count), f"{percentage:.1f}%")
        
        console.print(pillar_table)
        
        # Display quality score statistics
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            high_scores = len([s for s in quality_scores if s > 0.8])
            low_scores = len([s for s in quality_scores if s < 0.3])
            
            score_table = Table(title="Quality Score Analysis")
            score_table.add_column("Metric", style="cyan")
            score_table.add_column("Value", style="magenta")
            
            score_table.add_row("Average Relevance Score", f"{avg_score:.3f}")
            score_table.add_row("High Scores (>0.8)", f"{high_scores} ({high_scores/total_notes*100:.1f}%)")
            score_table.add_row("Low Scores (<0.3)", f"{low_scores} ({low_scores/total_notes*100:.1f}%)")
            
            console.print(score_table)
    
    def _analyze_content_quality(self):
        """Analyze content quality and characteristics."""
        notes_data = self.data.get("notes_data", [])
        
        if not notes_data:
            return
        
        console.print(f"\n[bold cyan]📝 Content Quality Analysis[/bold cyan]")
        console.print("-" * 40)
        
        # Analyze content characteristics
        content_stats = {
            "total_files": len(notes_data),
            "has_frontmatter": 0,
            "has_attachments": 0,
            "evernote_clippings": 0,
            "truncated_content": 0,
            "avg_file_size": 0,
            "avg_word_count": 0
        }
        
        file_sizes = []
        word_counts = []
        
        for note in notes_data:
            # Handle both formats
            if "preprocessing_stages" in note:
                # Comprehensive format
                stage_1 = note["preprocessing_stages"].get("stage_1_raw_reading", {})
                stage_2 = note["preprocessing_stages"].get("stage_2_content_extraction", {})
                stage_3 = note["preprocessing_stages"].get("stage_3_evernote_preprocessing", {})
                stage_4 = note["preprocessing_stages"].get("stage_4_content_truncation", {})
                
                file_size = note["file_metadata"].get("file_size", 0)
                has_frontmatter = stage_2.get("has_frontmatter", False)
                has_attachments = stage_2.get("has_attachments", False)
                is_evernote = stage_3.get("is_evernote_clipping", False)
                was_truncated = stage_4.get("truncation_info", {}).get("was_truncated", False)
                word_count = stage_2.get("extracted_length", 0) // 5  # Rough estimate
            else:
                # Legacy format
                file_size = note.get("file_size", 0)
                has_frontmatter = note.get("has_frontmatter", False)
                has_attachments = note.get("has_attachments", False)
                is_evernote = False  # Not available in legacy format
                was_truncated = False  # Not available in legacy format
                word_count = note.get("word_count", 0)
            
            file_sizes.append(file_size)
            word_counts.append(word_count)
            
            if has_frontmatter:
                content_stats["has_frontmatter"] += 1
            if has_attachments:
                content_stats["has_attachments"] += 1
            if is_evernote:
                content_stats["evernote_clippings"] += 1
            if was_truncated:
                content_stats["truncated_content"] += 1
        
        content_stats["avg_file_size"] = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        content_stats["avg_word_count"] = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Display content statistics
        content_table = Table(title="Content Characteristics")
        content_table.add_column("Characteristic", style="cyan")
        content_table.add_column("Count", style="magenta")
        content_table.add_column("Percentage", style="green")
        
        for key, count in content_stats.items():
            if key in ["total_files", "avg_file_size", "avg_word_count"]:
                continue
            
            percentage = (count / content_stats["total_files"]) * 100
            content_table.add_row(key.replace("_", " ").title(), str(count), f"{percentage:.1f}%")
        
        console.print(content_table)
        
        # Display averages
        avg_table = Table(title="Average Metrics")
        avg_table.add_column("Metric", style="cyan")
        avg_table.add_column("Value", style="magenta")
        
        avg_table.add_row("Average File Size", f"{content_stats['avg_file_size']:.0f} bytes")
        avg_table.add_row("Average Word Count", f"{content_stats['avg_word_count']:.0f} words")
        
        console.print(avg_table)
    
    def _analyze_preprocessing_effectiveness(self):
        """Analyze the effectiveness of preprocessing stages."""
        notes_data = self.data.get("notes_data", [])
        
        if not notes_data:
            return
        
        console.print(f"\n[bold cyan]🔧 Preprocessing Effectiveness Analysis[/bold cyan]")
        console.print("-" * 40)
        
        preprocessing_stats = {
            "evernote_preprocessing_applied": 0,
            "content_truncation_applied": 0,
            "avg_reduction_ratio": 0,
            "avg_truncation_ratio": 0
        }
        
        reduction_ratios = []
        truncation_ratios = []
        
        for note in notes_data:
            if "preprocessing_stages" not in note:
                continue
            
            # Evernote preprocessing
            stage_3 = note["preprocessing_stages"].get("stage_3_evernote_preprocessing", {})
            if stage_3.get("preprocessing_applied", False):
                preprocessing_stats["evernote_preprocessing_applied"] += 1
                reduction_ratios.append(stage_3.get("reduction_ratio", 1.0))
            
            # Content truncation
            stage_4 = note["preprocessing_stages"].get("stage_4_content_truncation", {})
            truncation_info = stage_4.get("truncation_info", {})
            if truncation_info.get("was_truncated", False):
                preprocessing_stats["content_truncation_applied"] += 1
                truncation_ratios.append(truncation_info.get("truncation_ratio", 1.0))
        
        if reduction_ratios:
            preprocessing_stats["avg_reduction_ratio"] = sum(reduction_ratios) / len(reduction_ratios)
        if truncation_ratios:
            preprocessing_stats["avg_truncation_ratio"] = sum(truncation_ratios) / len(truncation_ratios)
        
        # Display preprocessing statistics
        preprocessing_table = Table(title="Preprocessing Statistics")
        preprocessing_table.add_column("Stage", style="cyan")
        preprocessing_table.add_column("Applied", style="magenta")
        preprocessing_table.add_column("Percentage", style="green")
        preprocessing_table.add_column("Effectiveness", style="yellow")
        
        total_notes = len(notes_data)
        
        evernote_pct = (preprocessing_stats["evernote_preprocessing_applied"] / total_notes) * 100
        truncation_pct = (preprocessing_stats["content_truncation_applied"] / total_notes) * 100
        
        preprocessing_table.add_row(
            "Evernote Preprocessing",
            str(preprocessing_stats["evernote_preprocessing_applied"]),
            f"{evernote_pct:.1f}%",
            f"Avg reduction: {(1-preprocessing_stats['avg_reduction_ratio'])*100:.1f}%"
        )
        
        preprocessing_table.add_row(
            "Content Truncation",
            str(preprocessing_stats["content_truncation_applied"]),
            f"{truncation_pct:.1f}%",
            f"Avg truncation: {(1-preprocessing_stats['avg_truncation_ratio'])*100:.1f}%"
        )
        
        console.print(preprocessing_table)
    
    def _generate_recommendations(self):
        """Generate recommendations based on analysis."""
        console.print(f"\n[bold cyan]💡 Recommendations[/bold cyan]")
        console.print("-" * 40)
        
        notes_data = self.data.get("notes_data", [])
        if not notes_data:
            return
        
        recommendations = []
        
        # Analyze classification distribution
        actions = {}
        for note in notes_data:
            if "preprocessing_stages" in note:
                action = note["preprocessing_stages"].get("stage_5_llm_analysis", {}).get("curation_action", "unknown")
            else:
                action = note.get("curation_action", "unknown")
            actions[action] = actions.get(action, 0) + 1
        
        total_notes = len(notes_data)
        
        # Check for overly lenient classification
        keep_count = actions.get("keep", 0)
        keep_percentage = (keep_count / total_notes) * 100
        
        if keep_percentage > 80:
            recommendations.append("⚠️ Classification may be too lenient - consider adjusting quality thresholds")
        elif keep_percentage < 20:
            recommendations.append("⚠️ Classification may be too strict - consider relaxing quality thresholds")
        else:
            recommendations.append("✅ Classification distribution looks balanced")
        
        # Check for preprocessing opportunities
        evernote_count = 0
        truncation_count = 0
        
        for note in notes_data:
            if "preprocessing_stages" in note:
                stage_3 = note["preprocessing_stages"].get("stage_3_evernote_preprocessing", {})
                stage_4 = note["preprocessing_stages"].get("stage_4_content_truncation", {})
                
                if stage_3.get("preprocessing_applied", False):
                    evernote_count += 1
                if stage_4.get("truncation_info", {}).get("was_truncated", False):
                    truncation_count += 1
        
        if evernote_count > 0:
            recommendations.append(f"📝 {evernote_count} Evernote clippings detected - preprocessing is working")
        
        if truncation_count > 0:
            recommendations.append(f"✂️ {truncation_count} notes were truncated - consider increasing max_note_chars")
        
        # Check for quality score distribution
        quality_scores = []
        for note in notes_data:
            if "preprocessing_stages" in note:
                scores = note["preprocessing_stages"].get("stage_5_llm_analysis", {}).get("quality_scores", {})
            else:
                scores = note.get("quality_scores", {})
            
            if scores:
                quality_scores.append(scores.get("relevance", 0))
        
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            if avg_score > 0.7:
                recommendations.append("🎯 Average quality score is high - consider if scoring is too lenient")
            elif avg_score < 0.3:
                recommendations.append("🎯 Average quality score is low - consider if scoring is too strict")
            else:
                recommendations.append("✅ Quality score distribution looks appropriate")
        
        # Display recommendations
        for i, recommendation in enumerate(recommendations, 1):
            console.print(f"{i}. {recommendation}")
        
        # Additional suggestions
        console.print(f"\n[bold yellow]🚀 Next Steps:[/bold yellow]")
        console.print("• Review individual note preprocessing stages in the comprehensive data")
        console.print("• Develop custom preprocessing scripts based on the analysis")
        console.print("• Adjust classification thresholds based on recommendations")
        console.print("• Consider implementing additional preprocessing stages")


def main():
    """Main analysis function."""
    console.print("[bold blue]🔬 Enhanced Test Results Analyzer[/bold blue]")
    console.print("=" * 60)
    
    try:
        analyzer = ComprehensiveTestAnalyzer()
        analyzer.analyze_comprehensive_results()
        
    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main() 