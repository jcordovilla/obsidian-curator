"""Core orchestration for the Obsidian curation system."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from .models import CurationConfig, CurationResult, VaultStructure, CurationStats
from .content_processor import ContentProcessor
from .ai_analyzer import AIAnalyzer
from .theme_classifier import ThemeClassifier
from .vault_organizer import VaultOrganizer


class ObsidianCurator:
    """Main orchestrator for the Obsidian curation system."""
    
    def __init__(self, config: CurationConfig):
        """Initialize the Obsidian curator.
        
        Args:
            config: Curation configuration
        """
        self.config = config
        self.content_processor = ContentProcessor(
            clean_html=config.clean_html,
            preserve_metadata=config.preserve_metadata
        )
        self.ai_analyzer = AIAnalyzer(config)
        self.theme_classifier = ThemeClassifier()
        self.vault_organizer = VaultOrganizer(config)
        
        logger.info("Obsidian Curator initialized successfully")
    
    def curate_vault(self, input_path: Path, output_path: Path) -> CurationStats:
        """Curate an entire Obsidian vault.
        
        Args:
            input_path: Path to the input Obsidian vault
            output_path: Path for the curated vault output
            
        Returns:
            CurationStats object with processing statistics
        """
        logger.info(f"Starting vault curation from {input_path} to {output_path}")
        
        # Step 1: Discover and process notes
        notes = self._discover_notes(input_path)
        logger.info(f"Discovered {len(notes)} notes for processing")
        
        # Step 2: Process and clean content
        processed_notes = self._process_notes(notes)
        logger.info(f"Processed {len(processed_notes)} notes")
        
        # Step 3: AI analysis and curation
        curation_results = self._curate_notes(processed_notes)
        logger.info(f"Completed AI analysis for {len(curation_results)} notes")
        
        # Step 4: Create vault structure
        vault_structure = self._create_vault_structure(output_path, curation_results)
        
        # Step 5: Organize and save curated content
        stats = self.vault_organizer.create_curated_vault(
            curation_results, output_path, vault_structure
        )
        
        logger.info("Vault curation completed successfully")
        return stats
    
    def _discover_notes(self, vault_path: Path) -> List[Path]:
        """Discover all markdown notes in the vault.
        
        Args:
            vault_path: Path to the Obsidian vault
            
        Returns:
            List of markdown file paths
        """
        notes = []
        
        # Look for markdown files
        for file_path in vault_path.rglob("*.md"):
            # Skip certain directories and files
            if self._should_skip_file(file_path, vault_path):
                continue
            notes.append(file_path)
        
        # Sort by modification date (newest first)
        notes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return notes
    
    def _should_skip_file(self, file_path: Path, vault_path: Path) -> bool:
        """Determine if a file should be skipped during processing.
        
        Args:
            file_path: Path to the file
            vault_path: Root vault path
            
        Returns:
            True if file should be skipped
        """
        # Skip hidden files and directories
        if any(part.startswith('.') for part in file_path.parts):
            return True
        
        # Skip certain directories
        skip_dirs = {
            '.obsidian', 'attachments', 'assets', 'images', 'media',
            'templates', 'daily', 'archive', 'trash'
        }
        
        relative_path = file_path.relative_to(vault_path)
        if any(skip_dir in relative_path.parts for skip_dir in skip_dirs):
            return True
        
        # Skip certain file patterns
        skip_patterns = [
            'README.md', 'index.md', 'home.md', 'welcome.md',
            'template.md', 'daily-', 'weekly-', 'monthly-'
        ]
        
        filename = file_path.name.lower()
        if any(pattern in filename for pattern in skip_patterns):
            return True
        
        return False
    
    def _process_notes(self, note_paths: List[Path]) -> List[Any]:
        """Process and clean note content.
        
        Args:
            note_paths: List of note file paths
            
        Returns:
            List of processed Note objects
        """
        processed_notes = []
        
        for file_path in note_paths:
            try:
                note = self.content_processor.process_note(file_path)
                processed_notes.append(note)
                logger.debug(f"Processed note: {note.title}")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        return processed_notes
    
    def _curate_notes(self, notes: List[Any]) -> List[CurationResult]:
        """Curate notes using AI analysis.
        
        Args:
            notes: List of processed notes
            
        Returns:
            List of curation results
        """
        curation_results = []
        
        for note in notes:
            try:
                # AI analysis
                quality_scores, themes, curation_reason = self.ai_analyzer.analyze_note(note)
                
                # Determine if note should be curated
                is_curated = self._should_curate_note(quality_scores, themes)
                
                # Create curation result
                result = CurationResult(
                    note=note,
                    cleaned_content=note.content,  # Could be enhanced with cleaning
                    quality_scores=quality_scores,
                    themes=themes,
                    is_curated=is_curated,
                    curation_reason=curation_reason,
                    processing_notes=[]
                )
                
                curation_results.append(result)
                logger.debug(f"Curated note: {note.title} (curated: {is_curated})")
                
            except Exception as e:
                logger.error(f"Failed to curate {note.title}: {e}")
                # Create a failed result
                failed_result = CurationResult(
                    note=note,
                    cleaned_content=note.content,
                    quality_scores=self._default_quality_scores(),
                    themes=[self._default_theme()],
                    is_curated=False,
                    curation_reason=f"Processing failed: {str(e)}",
                    processing_notes=[f"Error: {str(e)}"]
                )
                curation_results.append(failed_result)
        
        return curation_results
    
    def _should_curate_note(self, quality_scores: Any, themes: List[Any]) -> bool:
        """Determine if a note should be curated based on quality and relevance.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            
        Returns:
            True if note should be curated
        """
        # Check quality threshold
        if quality_scores.overall < self.config.quality_threshold:
            return False
        
        # Check relevance threshold
        if quality_scores.relevance < self.config.relevance_threshold:
            return False
        
        # Check if themes align with target themes
        if self.config.target_themes:
            has_target_theme = any(
                theme.name.lower() in [t.lower() for t in self.config.target_themes]
                for theme in themes
            )
            if not has_target_theme:
                return False
        
        return True
    
    def _create_vault_structure(self, output_path: Path, 
                               curation_results: List[CurationResult]) -> VaultStructure:
        """Create the folder structure for the curated vault.
        
        Args:
            output_path: Root path for the curated vault
            curation_results: List of curation results
            
        Returns:
            VaultStructure object
        """
        # Classify themes
        theme_groups = self.theme_classifier.classify_themes(curation_results)
        
        # Create vault structure
        vault_structure = self.theme_classifier.create_vault_structure(
            output_path, theme_groups
        )
        
        return vault_structure
    
    def _default_quality_scores(self) -> Any:
        """Create default quality scores for failed processing.
        
        Returns:
            Default QualityScore object
        """
        from .models import QualityScore
        return QualityScore(
            overall=0.0,
            relevance=0.0,
            completeness=0.0,
            credibility=0.0,
            clarity=0.0
        )
    
    def _default_theme(self) -> Any:
        """Create default theme for failed processing.
        
        Returns:
            Default Theme object
        """
        from .models import Theme
        return Theme(
            name="unknown",
            confidence=0.0,
            subthemes=[],
            keywords=[]
        )
    
    def get_curation_summary(self, curation_results: List[CurationResult]) -> Dict[str, Any]:
        """Get a summary of curation results.
        
        Args:
            curation_results: List of curation results
            
        Returns:
            Summary dictionary
        """
        total_notes = len(curation_results)
        curated_notes = sum(1 for r in curation_results if r.is_curated)
        rejected_notes = total_notes - curated_notes
        
        # Theme distribution
        theme_counts = {}
        for result in curation_results:
            if result.themes:
                primary_theme = result.primary_theme
                if primary_theme:
                    theme_name = primary_theme.name
                    theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1
        
        # Quality distribution
        quality_ranges = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        for result in curation_results:
            score = result.quality_scores.overall
            if score < 0.2:
                quality_ranges["0.0-0.2"] += 1
            elif score < 0.4:
                quality_ranges["0.2-0.4"] += 1
            elif score < 0.6:
                quality_ranges["0.4-0.6"] += 1
            elif score < 0.8:
                quality_ranges["0.6-0.8"] += 1
            else:
                quality_ranges["0.8-1.0"] += 1
        
        return {
            "total_notes": total_notes,
            "curated_notes": curated_notes,
            "rejected_notes": rejected_notes,
            "curation_rate": (curated_notes / total_notes * 100) if total_notes > 0 else 0,
            "theme_distribution": theme_counts,
            "quality_distribution": quality_ranges
        }
    
    def export_curation_report(self, curation_results: List[CurationResult], 
                              output_path: Path) -> None:
        """Export a detailed curation report.
        
        Args:
            curation_results: List of curation results
            output_path: Path to save the report
        """
        summary = self.get_curation_summary(curation_results)
        
        report = []
        report.append("# Obsidian Curation Report")
        report.append("")
        report.append(f"Generated on: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        report.append("")
        report.append(f"- **Total Notes**: {summary['total_notes']}")
        report.append(f"- **Curated Notes**: {summary['curated_notes']}")
        report.append(f"- **Rejected Notes**: {summary['rejected_notes']}")
        report.append(f"- **Curation Rate**: {summary['curation_rate']:.1f}%")
        report.append("")
        
        # Theme distribution
        report.append("## Theme Distribution")
        report.append("")
        for theme, count in sorted(summary['theme_distribution'].items(), 
                                  key=lambda x: x[1], reverse=True):
            percentage = (count / summary['total_notes'] * 100) if summary['total_notes'] > 0 else 0
            report.append(f"- **{theme}**: {count} notes ({percentage:.1f}%)")
        report.append("")
        
        # Quality distribution
        report.append("## Quality Distribution")
        report.append("")
        for range_name, count in summary['quality_distribution'].items():
            percentage = (count / summary['total_notes'] * 100) if summary['total_notes'] > 0 else 0
            report.append(f"- **{range_name}**: {count} notes ({percentage:.1f}%)")
        report.append("")
        
        # Detailed results
        report.append("## Detailed Results")
        report.append("")
        
        for result in curation_results:
            status = "✅ CURATED" if result.is_curated else "❌ REJECTED"
            report.append(f"### {status}: {result.note.title}")
            report.append(f"- **Quality Score**: {result.quality_scores.overall:.2f}")
            report.append(f"- **Relevance Score**: {result.quality_scores.relevance:.2f}")
            report.append(f"- **Primary Theme**: {result.primary_theme.name if result.primary_theme else 'Unknown'}")
            report.append(f"- **Reason**: {result.curation_reason}")
            report.append("")
        
        # Save report
        output_path.write_text("\n".join(report), encoding='utf-8')
        logger.info(f"Curation report saved to: {output_path}")
