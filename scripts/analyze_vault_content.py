#!/usr/bin/env python3
"""
Vault Content Analysis Script

This script analyzes the structure and content patterns of notes in the Obsidian vault
to understand the data before implementing preprocessing improvements.
"""

import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import statistics

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import markdown_it
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

console = Console()


class VaultContentAnalyzer:
    """Analyzes vault content structure and patterns."""
    
    def __init__(self, config_path: Path = Path("config/vault_config.yaml")):
        """Initialize the analyzer."""
        self.config_path = config_path
        self.config = self._load_config()
        self.md_parser = markdown_it.MarkdownIt()
        
        # Analysis results
        self.content_stats = {}
        self.structure_patterns = {}
        self.content_patterns = {}
        self.quality_indicators = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load vault configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[red]Config file not found: {self.config_path}[/red]")
            sys.exit(1)
    
    def find_notes(self, vault_path: Path, sample_size: int = 300) -> List[Path]:
        """Find notes in the vault, optionally sampling."""
        notes = []
        
        # Create pathspec for file filtering
        include_patterns = self.config.get('vault', {}).get('include_patterns', ['*.md'])
        exclude_patterns = self.config.get('vault', {}).get('exclude_patterns', [])
        
        include_spec = PathSpec.from_lines(GitWildMatchPattern, include_patterns)
        exclude_spec = PathSpec.from_lines(GitWildMatchPattern, exclude_patterns)
        
        # Find all markdown files
        for file_path in vault_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(vault_path)
                
                if include_spec.match_file(str(relative_path)) and \
                   not exclude_spec.match_file(str(relative_path)):
                    notes.append(file_path)
        
        console.print(f"Found {len(notes)} total notes in vault")
        
        # Sample if requested
        if sample_size and len(notes) > sample_size:
            import random
            notes = random.sample(notes, sample_size)
            console.print(f"Sampled {len(notes)} notes for analysis")
        
        return notes
    
    def analyze_note_structure(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze the structure of a single note."""
        analysis = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'folder': str(file_path.parent.name),
            'file_size': len(content.encode('utf-8')),
            'content_length': len(content),
            'lines': len(content.splitlines()),
            'has_frontmatter': content.startswith('---'),
            'frontmatter_lines': 0,
            'has_attachments': False,
            'attachment_count': 0,
            'has_links': False,
            'link_count': 0,
            'has_images': False,
            'image_count': 0,
            'has_code_blocks': False,
            'code_block_count': 0,
            'has_tables': False,
            'table_count': 0,
            'has_lists': False,
            'list_count': 0,
            'has_headers': False,
            'header_count': 0,
            'word_count': 0,
            'character_count': 0,
            'unique_words': 0,
            'avg_word_length': 0.0,
            'content_ratio': 0.0,  # Actual content vs metadata
            'structure_score': 0.0,
            'quality_indicators': {},
            'content_patterns': {},
            'issues': []
        }
        
        try:
            # Extract frontmatter
            if analysis['has_frontmatter']:
                frontmatter_end = content.find('---', 3)
                if frontmatter_end != -1:
                    frontmatter = content[3:frontmatter_end]
                    analysis['frontmatter_lines'] = len(frontmatter.splitlines())
                    analysis['content_ratio'] = (len(content) - len(frontmatter)) / len(content)
            
            # Count attachments and links
            attachment_pattern = r'\[.*?\]\((.*?)\)'
            attachments = re.findall(attachment_pattern, content)
            analysis['has_attachments'] = len(attachments) > 0
            analysis['attachment_count'] = len(attachments)
            
            # Count links (excluding attachments)
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            links = re.findall(link_pattern, content)
            analysis['has_links'] = len(links) > 0
            analysis['link_count'] = len(links)
            
            # Count images
            image_pattern = r'!\[.*?\]\(.*?\)'
            images = re.findall(image_pattern, content)
            analysis['has_images'] = len(images) > 0
            analysis['image_count'] = len(images)
            
            # Count code blocks
            code_block_pattern = r'```[\s\S]*?```'
            code_blocks = re.findall(code_block_pattern, content)
            analysis['has_code_blocks'] = len(code_blocks) > 0
            analysis['code_block_count'] = len(code_blocks)
            
            # Count tables
            table_pattern = r'\|.*\|'
            tables = re.findall(table_pattern, content)
            analysis['has_tables'] = len(tables) > 0
            analysis['table_count'] = len(tables)
            
            # Count lists
            list_pattern = r'^[\s]*[-*+]\s'
            lists = re.findall(list_pattern, content, re.MULTILINE)
            analysis['has_lists'] = len(lists) > 0
            analysis['list_count'] = len(lists)
            
            # Count headers
            header_pattern = r'^#{1,6}\s'
            headers = re.findall(header_pattern, content, re.MULTILINE)
            analysis['has_headers'] = len(headers) > 0
            analysis['header_count'] = len(headers)
            
            # Extract plain text for content analysis
            plain_text = self._extract_plain_text(content)
            analysis['character_count'] = len(plain_text)
            
            # Word analysis
            words = re.findall(r'\b\w+\b', plain_text.lower())
            analysis['word_count'] = len(words)
            analysis['unique_words'] = len(set(words))
            
            if words:
                analysis['avg_word_length'] = statistics.mean(len(word) for word in words)
            
            # Calculate structure score
            analysis['structure_score'] = self._calculate_structure_score(analysis)
            
            # Identify quality indicators
            analysis['quality_indicators'] = self._identify_quality_indicators(content, plain_text)
            
            # Identify content patterns
            analysis['content_patterns'] = self._identify_content_patterns(content, plain_text)
            
            # Identify issues
            analysis['issues'] = self._identify_issues(content, analysis)
            
        except Exception as e:
            analysis['issues'].append(f"Analysis error: {str(e)}")
        
        return analysis
    
    def _extract_plain_text(self, content: str) -> str:
        """Extract plain text from markdown content."""
        # Remove frontmatter
        if content.startswith('---'):
            frontmatter_end = content.find('---', 3)
            if frontmatter_end != -1:
                content = content[frontmatter_end + 3:]
        
        # Convert markdown to plain text
        rendered = self.md_parser.render(content)
        
        # Remove HTML tags
        plain_text = re.sub(r'<[^>]+>', '', rendered)
        
        # Clean up whitespace
        plain_text = re.sub(r'\n+', '\n', plain_text)
        plain_text = plain_text.strip()
        
        return plain_text
    
    def _calculate_structure_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate a structure quality score."""
        score = 0.0
        
        # Base score from content length
        if analysis['word_count'] > 100:
            score += 0.3
        elif analysis['word_count'] > 50:
            score += 0.2
        elif analysis['word_count'] > 20:
            score += 0.1
        
        # Structure elements
        if analysis['has_headers']:
            score += 0.2
        if analysis['has_lists']:
            score += 0.1
        if analysis['has_tables']:
            score += 0.1
        if analysis['has_code_blocks']:
            score += 0.1
        
        # Content ratio (actual content vs metadata)
        if analysis['content_ratio'] > 0.8:
            score += 0.2
        elif analysis['content_ratio'] > 0.6:
            score += 0.1
        
        return min(score, 1.0)
    
    def _identify_quality_indicators(self, content: str, plain_text: str) -> Dict[str, Any]:
        """Identify quality indicators in the content."""
        indicators = {
            'has_meaningful_content': len(plain_text.strip()) > 50,
            'has_structure': bool(re.search(r'^#{1,6}\s', content, re.MULTILINE)),
            'has_lists': bool(re.search(r'^[\s]*[-*+]\s', content, re.MULTILINE)),
            'has_links': bool(re.search(r'\[([^\]]+)\]\(([^)]+)\)', content)),
            'has_attachments': bool(re.search(r'\[.*?\]\((.*?)\)', content)),
            'has_code': bool(re.search(r'```[\s\S]*?```', content)),
            'has_tables': bool(re.search(r'\|.*\|', content, re.MULTILINE)),
            'is_evernote_clipping': any(indicator in content for indicator in [
                'Clipped from', 'Evernote', 'Web Clipper', 'Saved from', 'Source:'
            ]),
            'is_template': any(indicator in content.lower() for indicator in [
                'template', 'placeholder', 'example', 'sample'
            ]),
            'is_draft': any(indicator in content.lower() for indicator in [
                'draft', 'todo', 'temp', 'temporary', 'note to self'
            ]),
            'has_metadata': content.startswith('---'),
            'word_diversity': 0.0,
            'avg_sentence_length': 0.0
        }
        
        # Calculate word diversity
        words = re.findall(r'\b\w+\b', plain_text.lower())
        if words:
            indicators['word_diversity'] = len(set(words)) / len(words)
        
        # Calculate average sentence length
        sentences = re.split(r'[.!?]+', plain_text)
        if sentences:
            sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
            if sentence_lengths:
                indicators['avg_sentence_length'] = statistics.mean(sentence_lengths)
        
        return indicators
    
    def _identify_content_patterns(self, content: str, plain_text: str) -> Dict[str, Any]:
        """Identify content patterns and characteristics."""
        patterns = {
            'language': 'unknown',
            'has_numbers': bool(re.search(r'\d+', content)),
            'has_dates': bool(re.search(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', content)),
            'has_urls': bool(re.search(r'https?://', content)),
            'has_emails': bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
            'has_phone_numbers': bool(re.search(r'[\+]?[1-9][\d]{0,15}', content)),
            'has_currency': bool(re.search(r'[\$€£¥]\d+', content)),
            'has_percentages': bool(re.search(r'\d+%', content)),
            'has_measurements': bool(re.search(r'\d+\s*(km|m|cm|mm|kg|g|l|ml)', content, re.IGNORECASE)),
            'has_acronyms': bool(re.search(r'\b[A-Z]{2,}\b', content)),
            'has_technical_terms': False,
            'has_proper_nouns': False,
            'content_type': 'unknown'
        }
        
        # Detect language (basic)
        if re.search(r'[áéíóúñü]', content, re.IGNORECASE):
            patterns['language'] = 'spanish'
        elif re.search(r'[àâäéèêëïîôöùûüÿç]', content, re.IGNORECASE):
            patterns['language'] = 'french'
        elif re.search(r'[äöüß]', content, re.IGNORECASE):
            patterns['language'] = 'german'
        else:
            patterns['language'] = 'english'
        
        # Detect technical terms
        technical_terms = [
            'api', 'bim', 'ppp', 'infrastructure', 'digital', 'transformation',
            'governance', 'risk', 'management', 'project', 'finance', 'concession'
        ]
        patterns['has_technical_terms'] = any(term in content.lower() for term in technical_terms)
        
        # Detect proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', content)
        patterns['has_proper_nouns'] = len(proper_nouns) > 5
        
        # Determine content type
        if patterns['has_technical_terms'] and patterns['has_numbers']:
            patterns['content_type'] = 'technical_report'
        elif patterns['has_dates'] and patterns['has_proper_nouns']:
            patterns['content_type'] = 'meeting_notes'
        elif bool(re.search(r'^[\s]*[-*+]\s', content, re.MULTILINE)) and bool(re.search(r'^#{1,6}\s', content, re.MULTILINE)):
            patterns['content_type'] = 'structured_content'
        elif any(indicator in content.lower() for indicator in ['template', 'placeholder', 'example', 'sample']):
            patterns['content_type'] = 'template'
        else:
            patterns['content_type'] = 'general'
        
        return patterns
    
    def _identify_issues(self, content: str, analysis: Dict[str, Any]) -> List[str]:
        """Identify potential issues with the note."""
        issues = []
        
        # Content issues
        if analysis['word_count'] < 10:
            issues.append('very_short_content')
        elif analysis['word_count'] < 50:
            issues.append('short_content')
        
        if analysis['content_ratio'] < 0.3:
            issues.append('mostly_metadata')
        
        if analysis['structure_score'] < 0.3:
            issues.append('poor_structure')
        
        # Quality indicator issues
        indicators = analysis['quality_indicators']
        if indicators['is_evernote_clipping']:
            issues.append('evernote_clipping')
        if indicators['is_template']:
            issues.append('template_content')
        if indicators['is_draft']:
            issues.append('draft_content')
        
        # Structure issues
        if analysis['attachment_count'] > 10:
            issues.append('many_attachments')
        if analysis['link_count'] > 20:
            issues.append('many_links')
        
        return issues
    
    def analyze_vault(self, sample_size: int = 300) -> Dict[str, Any]:
        """Analyze the entire vault or a sample."""
        vault_path = Path(self.config['vault']['path'])
        
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")
        
        console.print(f"[bold blue]Analyzing vault: {vault_path}[/bold blue]")
        
        # Find notes
        notes = self.find_notes(vault_path, sample_size)
        
        # Analyze each note
        analyses = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing notes...", total=len(notes))
            
            for note_path in notes:
                try:
                    with open(note_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    analysis = self.analyze_note_structure(content, note_path)
                    analyses.append(analysis)
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"[red]Error analyzing {note_path}: {e}[/red]")
                    progress.update(task, advance=1)
        
        # Compile statistics
        stats = self._compile_statistics(analyses)
        
        return {
            'vault_path': str(vault_path),
            'analysis_date': datetime.now().isoformat(),
            'total_notes_analyzed': len(analyses),
            'sample_size': sample_size,
            'statistics': stats,
            'analyses': analyses
        }
    
    def _compile_statistics(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile comprehensive statistics from analyses."""
        stats = {
            'file_sizes': {
                'min': min(a['file_size'] for a in analyses),
                'max': max(a['file_size'] for a in analyses),
                'mean': statistics.mean(a['file_size'] for a in analyses),
                'median': statistics.median(a['file_size'] for a in analyses)
            },
            'content_lengths': {
                'min': min(a['content_length'] for a in analyses),
                'max': max(a['content_length'] for a in analyses),
                'mean': statistics.mean(a['content_length'] for a in analyses),
                'median': statistics.median(a['content_length'] for a in analyses)
            },
            'word_counts': {
                'min': min(a['word_count'] for a in analyses),
                'max': max(a['word_count'] for a in analyses),
                'mean': statistics.mean(a['word_count'] for a in analyses),
                'median': statistics.median(a['word_count'] for a in analyses)
            },
            'structure_scores': {
                'min': min(a['structure_score'] for a in analyses),
                'max': max(a['structure_score'] for a in analyses),
                'mean': statistics.mean(a['structure_score'] for a in analyses),
                'median': statistics.median(a['structure_score'] for a in analyses)
            },
            'feature_counts': {
                'has_frontmatter': sum(1 for a in analyses if a['has_frontmatter']),
                'has_attachments': sum(1 for a in analyses if a['has_attachments']),
                'has_links': sum(1 for a in analyses if a['has_links']),
                'has_images': sum(1 for a in analyses if a['has_images']),
                'has_code_blocks': sum(1 for a in analyses if a['has_code_blocks']),
                'has_tables': sum(1 for a in analyses if a['has_tables']),
                'has_lists': sum(1 for a in analyses if a['has_lists']),
                'has_headers': sum(1 for a in analyses if a['has_headers'])
            },
            'quality_indicators': {
                'has_meaningful_content': sum(1 for a in analyses if a['quality_indicators']['has_meaningful_content']),
                'has_structure': sum(1 for a in analyses if a['quality_indicators']['has_structure']),
                'is_evernote_clipping': sum(1 for a in analyses if a['quality_indicators']['is_evernote_clipping']),
                'is_template': sum(1 for a in analyses if a['quality_indicators']['is_template']),
                'is_draft': sum(1 for a in analyses if a['quality_indicators']['is_draft'])
            },
            'content_patterns': {
                'languages': Counter(a['content_patterns']['language'] for a in analyses),
                'content_types': Counter(a['content_patterns']['content_type'] for a in analyses),
                'has_technical_terms': sum(1 for a in analyses if a['content_patterns']['has_technical_terms']),
                'has_numbers': sum(1 for a in analyses if a['content_patterns']['has_numbers']),
                'has_dates': sum(1 for a in analyses if a['content_patterns']['has_dates'])
            },
            'issues': {
                'very_short_content': sum(1 for a in analyses if 'very_short_content' in a['issues']),
                'short_content': sum(1 for a in analyses if 'short_content' in a['issues']),
                'mostly_metadata': sum(1 for a in analyses if 'mostly_metadata' in a['issues']),
                'poor_structure': sum(1 for a in analyses if 'poor_structure' in a['issues']),
                'evernote_clipping': sum(1 for a in analyses if 'evernote_clipping' in a['issues']),
                'template_content': sum(1 for a in analyses if 'template_content' in a['issues']),
                'draft_content': sum(1 for a in analyses if 'draft_content' in a['issues'])
            },
            'folder_distribution': Counter(a['folder'] for a in analyses),
            'attachment_distribution': Counter(a['attachment_count'] for a in analyses),
            'link_distribution': Counter(a['link_count'] for a in analyses)
        }
        
        return stats
    
    def display_summary(self, results: Dict[str, Any]):
        """Display a comprehensive summary of the analysis."""
        stats = results['statistics']
        
        console.print(Panel.fit(
            Text("📊 Vault Content Analysis Summary", style="bold blue"),
            subtitle=f"Analyzed {results['total_notes_analyzed']} notes from {results['vault_path']}"
        ))
        
        # Basic statistics
        console.print("\n[bold]📈 Basic Statistics:[/bold]")
        basic_table = Table()
        basic_table.add_column("Metric", style="cyan")
        basic_table.add_column("Value", style="magenta")
        
        basic_table.add_row("Total Notes", str(results['total_notes_analyzed']))
        basic_table.add_row("Average File Size", f"{stats['file_sizes']['mean']:.0f} bytes")
        basic_table.add_row("Average Content Length", f"{stats['content_lengths']['mean']:.0f} chars")
        basic_table.add_row("Average Word Count", f"{stats['word_counts']['mean']:.0f} words")
        basic_table.add_row("Average Structure Score", f"{stats['structure_scores']['mean']:.2f}")
        
        console.print(basic_table)
        
        # Feature distribution
        console.print("\n[bold]🔧 Content Features:[/bold]")
        feature_table = Table()
        feature_table.add_column("Feature", style="cyan")
        feature_table.add_column("Count", style="magenta")
        feature_table.add_column("Percentage", style="green")
        
        total = results['total_notes_analyzed']
        for feature, count in stats['feature_counts'].items():
            percentage = (count / total) * 100
            feature_table.add_row(
                feature.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(feature_table)
        
        # Quality indicators
        console.print("\n[bold]🎯 Quality Indicators:[/bold]")
        quality_table = Table()
        quality_table.add_column("Indicator", style="cyan")
        quality_table.add_column("Count", style="magenta")
        quality_table.add_column("Percentage", style="green")
        
        for indicator, count in stats['quality_indicators'].items():
            percentage = (count / total) * 100
            quality_table.add_row(
                indicator.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(quality_table)
        
        # Issues
        console.print("\n[bold]⚠️  Issues Found:[/bold]")
        issues_table = Table()
        issues_table.add_column("Issue", style="cyan")
        issues_table.add_column("Count", style="magenta")
        issues_table.add_column("Percentage", style="red")
        
        for issue, count in stats['issues'].items():
            if count > 0:
                percentage = (count / total) * 100
                issues_table.add_row(
                    issue.replace('_', ' ').title(),
                    str(count),
                    f"{percentage:.1f}%"
                )
        
        console.print(issues_table)
        
        # Content patterns
        console.print("\n[bold]🌍 Content Patterns:[/bold]")
        pattern_table = Table()
        pattern_table.add_column("Pattern", style="cyan")
        pattern_table.add_column("Count", style="magenta")
        
        for language, count in stats['content_patterns']['languages'].most_common():
            pattern_table.add_row(f"Language: {language.title()}", str(count))
        
        for content_type, count in stats['content_patterns']['content_types'].most_common():
            pattern_table.add_row(f"Type: {content_type.replace('_', ' ').title()}", str(count))
        
        console.print(pattern_table)
        
        # Top folders
        console.print("\n[bold]📁 Top Folders:[/bold]")
        folder_table = Table()
        folder_table.add_column("Folder", style="cyan")
        folder_table.add_column("Count", style="magenta")
        
        for folder, count in stats['folder_distribution'].most_common(10):
            folder_table.add_row(folder, str(count))
        
        console.print(folder_table)


def main():
    """Main function."""
    console.print(Panel.fit(
        Text("🔍 Vault Content Analysis Tool", style="bold blue"),
        subtitle="Analyzing note structure and content patterns"
    ))
    
    try:
        analyzer = VaultContentAnalyzer()
        
        # Analyze vault with sample size
        sample_size = 300
        console.print(f"\n[yellow]Analyzing {sample_size} notes from vault...[/yellow]")
        
        results = analyzer.analyze_vault(sample_size=sample_size)
        
        # Display summary
        analyzer.display_summary(results)
        
        # Save detailed results
        output_dir = Path("results/content_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full analysis
        analysis_file = output_dir / f"vault_analysis_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save summary statistics
        summary_file = output_dir / f"vault_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results['statistics'], f, indent=2, default=str)
        
        console.print(f"\n[green]✅ Analysis complete![/green]")
        console.print(f"📄 Full analysis saved to: {analysis_file}")
        console.print(f"📊 Summary statistics saved to: {summary_file}")
        
        # Recommendations
        console.print("\n[bold]💡 Preprocessing Recommendations:[/bold]")
        stats = results['statistics']
        
        if stats['issues']['evernote_clipping'] > 0:
            console.print("• Implement Evernote clipping cleanup")
        
        if stats['issues']['template_content'] > 0:
            console.print("• Add template detection and filtering")
        
        if stats['issues']['draft_content'] > 0:
            console.print("• Add draft content detection")
        
        if stats['issues']['very_short_content'] > 0:
            console.print("• Add minimum content length filtering")
        
        if stats['quality_indicators']['has_meaningful_content'] < results['total_notes_analyzed'] * 0.8:
            console.print("• Improve content extraction from markdown")
        
        console.print("• Implement content quality scoring before LLM processing")
        console.print("• Add language detection for multilingual content")
        console.print("• Create preprocessing pipeline for different content types")
        
    except Exception as e:
        console.print(f"[red]❌ Error during analysis: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 