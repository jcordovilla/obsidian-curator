"""Vault organization and file management for curated content."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from .models import CurationResult, VaultStructure, CurationStats, CurationConfig


class VaultOrganizer:
    """Organizes and saves curated content to a new vault structure."""
    
    def __init__(self, config: CurationConfig):
        """Initialize the vault organizer.
        
        Args:
            config: Curation configuration
        """
        self.config = config
    
    def create_curated_vault(self, 
                            curation_results: List[CurationResult], 
                            output_path: Path,
                            vault_structure: VaultStructure) -> CurationStats:
        """Create the curated vault with organized content.
        
        Args:
            curation_results: List of curation results to organize
            output_path: Root path for the curated vault
            vault_structure: Vault structure information
            
        Returns:
            CurationStats object with processing statistics
        """
        start_time = datetime.now()
        
        logger.info(f"Creating curated vault at: {output_path}")
        
        # Filter curated results
        curated_results = [r for r in curation_results if r.is_curated]
        rejected_results = [r for r in curation_results if not r.is_curated]
        
        # Create theme groups
        from .theme_classifier import ThemeClassifier
        theme_classifier = ThemeClassifier(
            self.config.theme_similarity_threshold
        )
        theme_groups = theme_classifier.classify_themes(curated_results)
        
        # Save curated notes to theme folders
        saved_notes = self._save_curated_notes(theme_groups, vault_structure)
        
        # Generate and save metadata
        self._save_metadata(curation_results, curated_results, rejected_results, 
                           vault_structure, theme_groups)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create statistics
        stats = CurationStats(
            total_notes=len(curation_results),
            curated_notes=len(curated_results),
            rejected_notes=len(rejected_results),
            processing_time=processing_time,
            themes_distribution={name: len(results) for name, results in theme_groups.items()},
            quality_distribution=self._calculate_quality_distribution(curated_results)
        )
        
        logger.info(f"Curated vault created successfully. {stats.curated_notes}/{stats.total_notes} notes curated ({stats.curation_rate:.1f}%)")
        
        return stats
    
    def _save_curated_notes(self, theme_groups: Dict[str, List[CurationResult]], 
                           vault_structure: VaultStructure) -> int:
        """Save curated notes to their respective theme folders.
        
        Args:
            theme_groups: Theme groups with curation results
            vault_structure: Vault structure information
            
        Returns:
            Number of notes saved
        """
        saved_count = 0
        
        for theme_name, results in theme_groups.items():
            if not results:
                continue
            
            # Determine folder path
            if theme_name == "unknown":
                folder_path = vault_structure.root_path / "miscellaneous"
                folder_path.mkdir(parents=True, exist_ok=True)
            else:
                folder_path = vault_structure.theme_folders.get(theme_name)
                if not folder_path:
                    # Create folder if it doesn't exist
                    if "/" in theme_name:
                        main_theme, subtheme = theme_name.split("/", 1)
                        folder_path = vault_structure.root_path / main_theme / subtheme
                    else:
                        folder_path = vault_structure.root_path / theme_name
                    folder_path.mkdir(parents=True, exist_ok=True)
                    # Store the created folder path for future use
                    vault_structure.theme_folders[theme_name] = folder_path
            
            # Save notes to folder
            for result in results:
                try:
                    self._save_note(result, folder_path)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save note {result.note.title}: {e}")
        
        return saved_count
    
    def _save_note(self, result: CurationResult, folder_path: Path) -> None:
        """Save a single curated note to the specified folder.
        
        Args:
            result: Curation result to save
            folder_path: Folder to save the note in
        """
        # Generate filename and ensure uniqueness
        filename = self._generate_filename(result.note.title)
        file_path = folder_path / f"{filename}.md"
        counter = 1
        while file_path.exists():
            file_path = folder_path / f"{filename}_{counter}.md"
            counter += 1
        
        # Create note content
        note_content = self._create_note_content(result)
        
        # Save file
        file_path.write_text(note_content, encoding='utf-8')
        logger.debug(f"Saved note: {file_path}")
    
    def _generate_filename(self, title: str) -> str:
        """Generate a clean filename from a title.
        
        Args:
            title: Note title
            
        Returns:
            Clean filename
        """
        import re
        
        # Remove special characters and replace spaces with underscores
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[-\s]+', '_', filename)
        filename = filename.strip('_')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100].rstrip('_')
        
        return filename.lower()
    
    def _create_note_content(self, result: CurationResult) -> str:
        """Create the content for a curated note.
        
        Args:
            result: Curation result
            
        Returns:
            Formatted note content
        """
        content = []
        
        # Add frontmatter with enhanced professional writing metrics
        frontmatter = {
            "title": result.note.title,
            "curated_date": datetime.now().isoformat(),
            "original_source": result.note.source_url or "Unknown",
            "content_type": result.note.content_type.value,
            "quality_scores": {
                # Core quality metrics
                "overall": result.quality_scores.overall,
                "relevance": result.quality_scores.relevance,
                "completeness": result.quality_scores.completeness,
                "credibility": result.quality_scores.credibility,
                "clarity": result.quality_scores.clarity,
                # Professional writing metrics (NEW)
                "analytical_depth": result.quality_scores.analytical_depth,
                "evidence_quality": result.quality_scores.evidence_quality,
                "critical_thinking": result.quality_scores.critical_thinking,
                "argument_structure": result.quality_scores.argument_structure,
                "practical_value": result.quality_scores.practical_value,
                "professional_writing_score": result.quality_scores.professional_writing_score
            },
            "themes": [theme.name for theme in result.themes],
            "curation_reason": result.curation_reason
        }
        
        # Add enhanced theme information if available
        if result.themes:
            frontmatter["enhanced_themes"] = []
            for theme in result.themes:
                theme_info = {
                    "name": theme.name,
                    "confidence": theme.confidence,
                    "expertise_level": theme.expertise_level,
                    "content_category": theme.content_category,
                    "business_value": theme.business_value,
                    "subthemes": theme.subthemes,
                    "keywords": theme.keywords
                }
                frontmatter["enhanced_themes"].append(theme_info)
        
        # Add content structure analysis if available
        if result.content_structure:
            frontmatter["content_structure"] = {
                "has_clear_problem": result.content_structure.has_clear_problem,
                "has_evidence": result.content_structure.has_evidence,
                "has_multiple_perspectives": result.content_structure.has_multiple_perspectives,
                "has_actionable_conclusions": result.content_structure.has_actionable_conclusions,
                "logical_flow_score": result.content_structure.logical_flow_score,
                "argument_coherence": result.content_structure.argument_coherence,
                "conclusion_strength": result.content_structure.conclusion_strength,
                "structure_quality_score": result.content_structure.structure_quality_score
            }
        
        # Add original metadata if preserved
        if self.config.preserve_metadata and result.note.metadata:
            frontmatter["original_metadata"] = result.note.metadata
        
        # Convert to YAML-like format
        content.append("---")
        for key, value in frontmatter.items():
            if isinstance(value, dict):
                content.append(f"{key}:")
                for subkey, subvalue in value.items():
                    content.append(f"  {subkey}: {subvalue}")
            elif isinstance(value, list):
                content.append(f"{key}:")
                for item in value:
                    content.append(f"  - {item}")
            else:
                content.append(f"{key}: {value}")
        content.append("---")
        content.append("")
        
        # Add title
        content.append(f"# {result.note.title}")
        content.append("")
        
        # Add enhanced curation information
        content.append("## Curation Information")
        content.append("")
        content.append(f"- **Curated Date**: {frontmatter['curated_date']}")
        content.append(f"- **Quality Score**: {result.quality_scores.overall:.2f}/1.0")
        content.append(f"- **Relevance Score**: {result.quality_scores.relevance:.2f}/1.0")
        content.append(f"- **Professional Writing Score**: {result.quality_scores.professional_writing_score:.2f}/1.0")
        content.append(f"- **Primary Theme**: {result.primary_theme.name if result.primary_theme else 'Unknown'}")
        content.append(f"- **Curation Reason**: {result.curation_reason}")
        content.append("")
        
        # Add professional writing metrics
        content.append("## Professional Writing Quality Metrics")
        content.append("")
        content.append(f"- **Analytical Depth**: {result.quality_scores.analytical_depth:.2f}/1.0")
        content.append(f"- **Evidence Quality**: {result.quality_scores.evidence_quality:.2f}/1.0")
        content.append(f"- **Critical Thinking**: {result.quality_scores.critical_thinking:.2f}/1.0")
        content.append(f"- **Argument Structure**: {result.quality_scores.argument_structure:.2f}/1.0")
        content.append(f"- **Practical Value**: {result.quality_scores.practical_value:.2f}/1.0")
        content.append("")
        
        # Add content structure analysis
        if result.content_structure:
            content.append("## Content Structure Analysis")
            content.append("")
            content.append(f"- **Structure Quality Score**: {result.content_structure.structure_quality_score:.2f}/1.0")
            content.append(f"- **Has Clear Problem**: {'Yes' if result.content_structure.has_clear_problem else 'No'}")
            content.append(f"- **Has Evidence**: {'Yes' if result.content_structure.has_evidence else 'No'}")
            content.append(f"- **Multiple Perspectives**: {'Yes' if result.content_structure.has_multiple_perspectives else 'No'}")
            content.append(f"- **Actionable Conclusions**: {'Yes' if result.content_structure.has_actionable_conclusions else 'No'}")
            content.append(f"- **Logical Flow**: {result.content_structure.logical_flow_score:.2f}/1.0")
            content.append(f"- **Argument Coherence**: {result.content_structure.argument_coherence:.2f}/1.0")
            content.append(f"- **Conclusion Strength**: {result.content_structure.conclusion_strength:.2f}/1.0")
            content.append("")
        
        # Add enhanced themes section
        if result.themes:
            content.append("## Identified Themes")
            content.append("")
            for theme in result.themes:
                content.append(f"### {theme.name}")
                content.append(f"- **Confidence**: {theme.confidence:.2f}")
                content.append(f"- **Expertise Level**: {theme.expertise_level}")
                content.append(f"- **Content Category**: {theme.content_category}")
                content.append(f"- **Business Value**: {theme.business_value}")
                if theme.subthemes:
                    content.append(f"- **Sub-themes**: {', '.join(theme.subthemes)}")
                if theme.keywords:
                    content.append(f"- **Keywords**: {', '.join(theme.keywords)}")
                content.append("")
        
        # Add original content
        content.append("## Content")
        content.append("")
        content.append(result.cleaned_content)
        content.append("")
        
        # Add processing notes if any
        if result.processing_notes:
            content.append("## Processing Notes")
            content.append("")
            for note in result.processing_notes:
                content.append(f"- {note}")
            content.append("")
        
        return "\n".join(content)
    
    def _save_metadata(self, all_results: List[CurationResult], 
                       curated_results: List[CurationResult],
                       rejected_results: List[CurationResult],
                       vault_structure: VaultStructure,
                       theme_groups: Dict[str, List[CurationResult]]) -> None:
        """Save metadata and analysis files.
        
        Args:
            all_results: All curation results
            curated_results: Curated results only
            rejected_results: Rejected results only
            vault_structure: Vault structure information
            theme_groups: Theme groups
        """
        # Save curation log
        self._save_curation_log(all_results, curated_results, rejected_results, vault_structure)
        
        # Save theme analysis
        from .theme_classifier import ThemeClassifier
        theme_classifier = ThemeClassifier(
            self.config.theme_similarity_threshold
        )
        theme_analysis = theme_classifier.generate_theme_analysis(theme_groups, vault_structure)
        vault_structure.theme_analysis_path.write_text(theme_analysis, encoding='utf-8')
        
        # Save configuration
        self._save_configuration(vault_structure)
        
        # Save statistics
        self._save_statistics(all_results, curated_results, rejected_results, vault_structure)
    
    def _save_curation_log(self, all_results: List[CurationResult],
                           curated_results: List[CurationResult],
                           rejected_results: List[CurationResult],
                           vault_structure: VaultStructure) -> None:
        """Save curation log with detailed information.
        
        Args:
            all_results: All curation results
            curated_results: Curated results only
            rejected_results: Rejected results only
            vault_structure: Vault structure information
        """
        log_content = []
        
        log_content.append("# Curation Log")
        log_content.append("")
        log_content.append(f"Generated on: {datetime.now().isoformat()}")
        log_content.append(f"Configuration: {self.config.dict()}")
        log_content.append("")
        
        # Summary
        log_content.append("## Summary")
        log_content.append("")
        log_content.append(f"- **Total Notes Processed**: {len(all_results)}")
        log_content.append(f"- **Notes Curated**: {len(curated_results)}")
        log_content.append(f"- **Notes Rejected**: {len(rejected_results)}")
        log_content.append(f"- **Curation Rate**: {(len(curated_results) / len(all_results) * 100):.1f}%")
        log_content.append("")
        
        # Curated notes
        log_content.append("## Curated Notes")
        log_content.append("")
        for result in curated_results:
            log_content.append(f"### {result.note.title}")
            log_content.append(f"- **File**: {result.note.file_path}")
            log_content.append(f"- **Quality**: {result.quality_scores.overall:.2f}")
            log_content.append(f"- **Relevance**: {result.quality_scores.relevance:.2f}")
            log_content.append(f"- **Primary Theme**: {result.primary_theme.name if result.primary_theme else 'Unknown'}")
            log_content.append(f"- **Reason**: {result.curation_reason}")
            log_content.append("")
        
        # Rejected notes
        if rejected_results:
            log_content.append("## Rejected Notes")
            log_content.append("")
            for result in rejected_results:
                log_content.append(f"### {result.note.title}")
                log_content.append(f"- **File**: {result.note.file_path}")
                log_content.append(f"- **Quality**: {result.quality_scores.overall:.2f}")
                log_content.append(f"- **Relevance**: {result.quality_scores.relevance:.2f}")
                log_content.append(f"- **Reason**: {result.curation_reason}")
                log_content.append("")
        
        vault_structure.curation_log_path.write_text("\n".join(log_content), encoding='utf-8')
    
    def _save_configuration(self, vault_structure: VaultStructure) -> None:
        """Save configuration file to the vault.
        
        Args:
            vault_structure: Vault structure information
        """
        config_path = vault_structure.metadata_folder / "configuration.json"
        
        config_data = {
            "curation_config": self.config.dict(),
            "generated_date": datetime.now().isoformat(),
            "vault_structure": {
                "root_path": str(vault_structure.root_path),
                "theme_folders": {name: str(path) for name, path in vault_structure.theme_folders.items()},
                "metadata_folder": str(vault_structure.metadata_folder)
            }
        }
        
        config_path.write_text(json.dumps(config_data, indent=2), encoding='utf-8')
    
    def _save_statistics(self, all_results: List[CurationResult],
                        curated_results: List[CurationResult],
                        rejected_results: List[CurationResult],
                        vault_structure: VaultStructure) -> None:
        """Save detailed statistics to the vault.
        
        Args:
            all_results: All curation results
            curated_results: Curated results only
            rejected_results: Rejected results only
            vault_structure: Vault structure information
        """
        stats_path = vault_structure.metadata_folder / "statistics.json"
        
        # Calculate quality distributions
        quality_ranges = {
            "0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0
        }
        
        for result in all_results:
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
        
        stats_data = {
            "summary": {
                "total_notes": len(all_results),
                "curated_notes": len(curated_results),
                "rejected_notes": len(rejected_results),
                "curation_rate": len(curated_results) / len(all_results) if all_results else 0
            },
            "quality_distribution": quality_ranges,
            "average_scores": {
                "overall": sum(r.quality_scores.overall for r in all_results) / len(all_results) if all_results else 0,
                "relevance": sum(r.quality_scores.relevance for r in all_results) / len(all_results) if all_results else 0,
                "completeness": sum(r.quality_scores.completeness for r in all_results) / len(all_results) if all_results else 0,
                "credibility": sum(r.quality_scores.credibility for r in all_results) / len(all_results) if all_results else 0,
                "clarity": sum(r.quality_scores.clarity for r in all_results) / len(all_results) if all_results else 0
            },
            "generated_date": datetime.now().isoformat()
        }
        
        stats_path.write_text(json.dumps(stats_data, indent=2), encoding='utf-8')
    
    def _calculate_quality_distribution(self, results: List[CurationResult]) -> Dict[str, int]:
        """Calculate distribution of quality scores.
        
        Args:
            results: List of curation results
            
        Returns:
            Dictionary with quality score ranges and counts
        """
        distribution = {
            "0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0
        }
        
        for result in results:
            score = result.quality_scores.overall
            if score < 0.2:
                distribution["0.0-0.2"] += 1
            elif score < 0.4:
                distribution["0.2-0.4"] += 1
            elif score < 0.6:
                distribution["0.4-0.6"] += 1
            elif score < 0.8:
                distribution["0.6-0.8"] += 1
            else:
                distribution["0.8-1.0"] += 1
        
        return distribution
