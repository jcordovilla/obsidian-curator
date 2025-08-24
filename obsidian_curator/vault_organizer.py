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
        
        # Save rejected notes for visibility
        self._save_rejected_notes(rejected_results, vault_structure)
        
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
                    # Create folder if it doesn't exist - flat structure only
                    clean_theme_name = theme_name.split("/")[0] if "/" in theme_name else theme_name
                    folder_path = vault_structure.root_path / clean_theme_name
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
    
    def _save_rejected_notes(self, rejected_results: List[CurationResult], 
                           vault_structure: VaultStructure) -> int:
        """Save rejected notes to a separate folder for visibility.
        
        Args:
            rejected_results: Rejected curation results
            vault_structure: Vault structure information
            
        Returns:
            Number of rejected notes saved
        """
        if not rejected_results:
            return 0
        
        # Create rejected notes folder
        rejected_folder = vault_structure.root_path / "_discarded"
        rejected_folder.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        for result in rejected_results:
            try:
                self._save_rejected_note(result, rejected_folder)
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save rejected note {result.note.title}: {e}")
        
        # Create summary file
        summary_path = rejected_folder / "_rejection_summary.md"
        self._create_rejection_summary(rejected_results, summary_path)
        
        logger.info(f"Saved {saved_count} rejected notes to {rejected_folder}")
        return saved_count
    
    def _save_rejected_note(self, result: CurationResult, folder_path: Path) -> None:
        """Save a single rejected note with rejection reason.
        
        Args:
            result: Rejected curation result
            folder_path: Folder to save the note in
        """
        # Generate filename
        filename = self._generate_filename(result.note.title)
        file_path = folder_path / f"{filename}.md"
        
        # Create rejected note content
        content = []
        
        # Frontmatter with rejection info
        content.append("---")
        content.append(f"title: {result.note.title}")
        content.append(f"rejected_date: {datetime.now().isoformat()}")
        content.append(f"source: {result.note.source_url or 'Unknown'}")
        content.append(f"rejection_reason: {result.curation_reason}")
        content.append(f"overall_quality: {result.quality_scores.overall:.2f}")
        content.append(f"relevance: {result.quality_scores.relevance:.2f}")
        content.append(f"analytical_depth: {result.quality_scores.analytical_depth:.2f}")
        content.append("status: rejected")
        content.append("---")
        content.append("")
        
        # Add title and rejection info
        content.append(f"# {result.note.title}")
        content.append("")
        content.append("## Rejection Analysis")
        content.append("")
        content.append(f"**Reason**: {result.curation_reason}")
        content.append("")
        content.append("**Quality Scores**:")
        content.append(f"- Overall Quality: {result.quality_scores.overall:.2f}/1.0")
        content.append(f"- Relevance: {result.quality_scores.relevance:.2f}/1.0")
        content.append(f"- Analytical Depth: {result.quality_scores.analytical_depth:.2f}/1.0")
        content.append(f"- Critical Thinking: {result.quality_scores.critical_thinking:.2f}/1.0")
        content.append("")
        
        # Add original content for reference
        content.append("## Original Content")
        content.append("")
        if result.note.content and len(result.note.content.strip()) > 0:
            # Limit content to first 500 chars for rejected notes
            content_preview = result.note.content[:500]
            if len(result.note.content) > 500:
                content_preview += "..."
            content.append(content_preview)
        else:
            content.append("*No content available*")
        
        # Save file
        file_path.write_text("\n".join(content), encoding='utf-8')
        logger.debug(f"Saved rejected note: {file_path}")
    
    def _create_rejection_summary(self, rejected_results: List[CurationResult], 
                                summary_path: Path) -> None:
        """Create a summary file for all rejected notes.
        
        Args:
            rejected_results: List of rejected results
            summary_path: Path to save summary file
        """
        content = []
        
        content.append("# Rejected Notes Summary")
        content.append("")
        content.append(f"Generated on: {datetime.now().isoformat()}")
        content.append(f"Total rejected notes: {len(rejected_results)}")
        content.append("")
        
        # Group by rejection reason
        rejection_groups = {}
        for result in rejected_results:
            reason = result.curation_reason
            if reason not in rejection_groups:
                rejection_groups[reason] = []
            rejection_groups[reason].append(result)
        
        content.append("## Rejection Reasons")
        content.append("")
        for reason, results in rejection_groups.items():
            content.append(f"### {reason} ({len(results)} notes)")
            content.append("")
            for result in results:
                content.append(f"- **{result.note.title}** (Quality: {result.quality_scores.overall:.2f}, Relevance: {result.quality_scores.relevance:.2f})")
            content.append("")
        
        # Quality distribution of rejected notes
        content.append("## Quality Distribution")
        content.append("")
        quality_ranges = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0}
        for result in rejected_results:
            score = result.quality_scores.overall
            if score < 0.2:
                quality_ranges["0.0-0.2"] += 1
            elif score < 0.4:
                quality_ranges["0.2-0.4"] += 1
            elif score < 0.6:
                quality_ranges["0.4-0.6"] += 1
            else:
                quality_ranges["0.6-0.8"] += 1
        
        for range_name, count in quality_ranges.items():
            if count > 0:
                content.append(f"- {range_name}: {count} notes")
        
        content.append("")
        content.append("---")
        content.append("*This folder contains notes that were evaluated but did not meet the curation criteria.*")
        content.append("*Review these notes to understand what content is being filtered out.*")
        
        summary_path.write_text("\n".join(content), encoding='utf-8')
    
    def _save_note(self, result: CurationResult, folder_path: Path) -> None:
        """Save a single curated note to the specified folder.
        
        Args:
            result: Curation result to save
            folder_path: Folder to save the note in
        """
        # Generate filename and ensure uniqueness
        filename = self._generate_filename(result.note.title)
        file_path = folder_path / f"{filename}.md"
        
        # Create note content first
        note_content = self._create_note_content(result)
        
        # Enhanced duplicate detection and prevention
        if file_path.exists():
            try:
                existing_content = file_path.read_text(encoding='utf-8')
                # Compare the actual content parts (excluding metadata differences)
                existing_main_content = self._extract_main_content(existing_content)
                new_main_content = self._extract_main_content(note_content)
                
                # If main content is identical, skip saving completely
                if existing_main_content.strip() == new_main_content.strip():
                    logger.info(f"Skipping duplicate note: {result.note.title} (identical main content)")
                    return
                
                # If content is very similar (90%+ similarity), still skip
                similarity = self._calculate_content_similarity(existing_main_content, new_main_content)
                if similarity > 0.9:
                    logger.info(f"Skipping near-duplicate note: {result.note.title} (similarity: {similarity:.2f})")
                    return
                    
            except Exception as e:
                logger.warning(f"Failed to read existing file for comparison: {e}")
        
        # If we reach here and file exists, it means content is different enough
        # But let's still avoid creating v2 files unless absolutely necessary
        if file_path.exists():
            logger.warning(f"File exists with different content, will overwrite: {file_path.name}")
            # Instead of creating v2, we'll overwrite (since deduplication should have caught true duplicates)
        
        # No versioning - if we got here, save directly
        
        # Save file
        file_path.write_text(note_content, encoding='utf-8')
        logger.debug(f"Saved note: {file_path}")
    
    def _extract_main_content(self, content: str) -> str:
        """Extract main content excluding metadata for comparison."""
        lines = content.split('\n')
        in_frontmatter = False
        main_content_lines = []
        
        for line in lines:
            if line.strip() == '---':
                in_frontmatter = not in_frontmatter
                continue
            if not in_frontmatter:
                main_content_lines.append(line)
        
        return '\n'.join(main_content_lines)
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        # Simple similarity based on common words
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
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
    
    def _generate_professional_tags(self, result: CurationResult) -> List[str]:
        """Generate comprehensive professional tags for social media and professional use.
        
        Args:
            result: Curation result with themes and quality scores
            
        Returns:
            List of professional tags
        """
        tags = set()
        
        # Theme-based tags (main themes)
        for theme in result.themes:
            if theme.confidence >= 0.5:
                # Main theme
                tags.add(theme.name)
                
                # Add professional context tags based on theme characteristics
                if theme.expertise_level == "expert":
                    tags.add("ExpertAnalysis")
                    tags.add("ProfessionalInsight")
                elif theme.expertise_level == "thought_leader":
                    tags.add("ThoughtLeadership")
                    tags.add("IndustryLeadership")
                
                # Content category tags
                if theme.content_category == "strategic":
                    tags.add("Strategy")
                    tags.add("Planning")
                elif theme.content_category == "policy":
                    tags.add("Policy")
                    tags.add("Governance")
                elif theme.content_category == "technical":
                    tags.add("Technical")
                    tags.add("Implementation")
                elif theme.content_category == "operational":
                    tags.add("Operations")
                    tags.add("Management")
                
                # Business value tags
                if theme.business_value == "strategic":
                    tags.add("BusinessStrategy")
                elif theme.business_value == "governance":
                    tags.add("RiskManagement")
                    tags.add("Compliance")
                elif theme.business_value == "innovation":
                    tags.add("Innovation")
                    tags.add("Transformation")
        
        # Quality-based professional tags
        if result.quality_scores:
            if result.quality_scores.overall >= 0.8:
                tags.add("HighQuality")
                tags.add("BestPractices")
            
            if result.quality_scores.analytical_depth >= 0.8:
                tags.add("DeepAnalysis")
                tags.add("Research")
            
            if result.quality_scores.evidence_quality >= 0.8:
                tags.add("EvidenceBased")
                tags.add("DataDriven")
            
            if result.quality_scores.critical_thinking >= 0.8:
                tags.add("CriticalThinking")
                tags.add("StrategicThinking")
            
            if result.quality_scores.practical_value >= 0.8:
                tags.add("Actionable")
                tags.add("PracticalGuidance")
        
        # Industry and domain tags based on content
        content_lower = result.note.content.lower() if result.note.content else ""
        title_lower = result.note.title.lower()
        
        # Infrastructure and construction
        if any(term in content_lower or term in title_lower for term in ["infrastructure", "construction", "project"]):
            tags.add("Infrastructure")
            tags.add("ProjectManagement")
        
        if any(term in content_lower or term in title_lower for term in ["ppp", "public-private", "partnership"]):
            tags.add("PPP")
            tags.add("PublicPrivatePartnership")
        
        # Financial and economic
        if any(term in content_lower or term in title_lower for term in ["finance", "investment", "economic", "cost"]):
            tags.add("Finance")
            tags.add("Investment")
        
        # Technology and digital
        if any(term in content_lower or term in title_lower for term in ["digital", "technology", "innovation", "smart"]):
            tags.add("Technology")
            tags.add("DigitalTransformation")
        
        # Sustainability and environment
        if any(term in content_lower or term in title_lower for term in ["sustainable", "environment", "climate", "green"]):
            tags.add("Sustainability")
            tags.add("ClimateChange")
        
        # Professional social media tags
        tags.add("Professional")
        tags.add("IndustryInsights")
        
        # Content type indicators for professional context
        if len(result.note.content) > 2000:
            tags.add("ComprehensiveAnalysis")
        elif len(result.note.content) > 500:
            tags.add("DetailedReview")
        else:
            tags.add("KeyInsights")
        
        # Convert to sorted list and limit to reasonable number
        tags_list = sorted(list(tags))
        
        # Limit to 12 tags for readability (common social media best practice)
        if len(tags_list) > 12:
            # Prioritize main themes and high-value tags
            priority_tags = []
            general_tags = []
            
            for tag in tags_list:
                if tag in [theme.name for theme in result.themes if theme.confidence >= 0.7]:
                    priority_tags.append(tag)
                elif tag in ["ThoughtLeadership", "ExpertAnalysis", "HighQuality", "BestPractices"]:
                    priority_tags.append(tag)
                else:
                    general_tags.append(tag)
            
            # Take priority tags first, then fill with general tags
            tags_list = priority_tags + general_tags[:12-len(priority_tags)]
        
        return tags_list
    
    def _create_note_content(self, result: CurationResult) -> str:
        """Create the content for a curated note.
        
        Args:
            result: Curation result
            
        Returns:
            Formatted note content
        """
        content = []
        
        # Essential metadata only - preserve original note metadata when available
        frontmatter = {
            "title": result.note.title,
            "curated_date": datetime.now().isoformat(),
            "source": result.note.source_url or "Unknown",
            "tags": self._generate_professional_tags(result),
        }
        
        # Add original note dates directly from the Note object
        if result.note.created_date:
            frontmatter['original_created'] = result.note.created_date.isoformat()
        if result.note.modified_date:
            frontmatter['original_modified'] = result.note.modified_date.isoformat()
        
        # Preserve original metadata fields if they exist
        if result.note.metadata:
            # Keep essential original metadata
            essential_fields = ['date_created', 'date_modified', 'language', 'author', 'tags', 'status']
            for field in essential_fields:
                if field in result.note.metadata:
                    frontmatter[field] = result.note.metadata[field]
            
            # Add any existing tags to our theme-based tags
            if 'tags' in result.note.metadata and isinstance(result.note.metadata['tags'], list):
                existing_tags = set(result.note.metadata['tags'])
                new_tags = set(frontmatter.get('tags', []))
                frontmatter['tags'] = list(existing_tags.union(new_tags))
        
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
        
        # Add quality and theme information for transparency
        if result.quality_scores:
            content.append("## Quality Assessment")
            content.append("")
            content.append(f"- **Overall Quality**: {result.quality_scores.overall:.2f}/10")
            content.append(f"- **Relevance**: {result.quality_scores.relevance:.2f}/10")
            content.append(f"- **Analytical Depth**: {result.quality_scores.analytical_depth:.2f}/10")
            content.append("")
        
        if result.themes:
            content.append("## Identified Themes")
            content.append("")
            for theme in result.themes:
                if theme.confidence >= 0.5:  # Only show confident themes
                    content.append(f"- **{theme.name}**")
            content.append("")
        
        # Add curated content
        content.append("## Content")
        content.append("")
        
        # Clean and format the cleaned content
        cleaned_content = result.cleaned_content.strip()
        if cleaned_content:
            # Split into paragraphs and clean each one
            paragraphs = cleaned_content.split('\n\n')
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph and len(paragraph) > 20:  # Only add substantial paragraphs
                    content.append(paragraph)
                    content.append("")
        else:
            content.append("*No content available after curation.*")
        
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
        
        # Curated notes with full analytical metadata
        log_content.append("## Curated Notes")
        log_content.append("")
        for result in curated_results:
            log_content.append(f"### {result.note.title}")
            log_content.append(f"- **File**: {result.note.file_path}")
            log_content.append(f"- **Source**: {result.note.source_url or 'Unknown'}")
            log_content.append(f"- **Content Type**: {result.note.content_type.value}")
            log_content.append("")
            
            # Quality Scores
            log_content.append("**Quality Assessment:**")
            log_content.append(f"- Overall: {result.quality_scores.overall:.2f}")
            log_content.append(f"- Relevance: {result.quality_scores.relevance:.2f}")
            log_content.append(f"- Analytical Depth: {result.quality_scores.analytical_depth:.2f}")
            log_content.append(f"- Critical Thinking: {result.quality_scores.critical_thinking:.2f}")
            log_content.append(f"- Evidence Quality: {result.quality_scores.evidence_quality:.2f}")
            log_content.append(f"- Argument Structure: {result.quality_scores.argument_structure:.2f}")
            log_content.append(f"- Practical Value: {result.quality_scores.practical_value:.2f}")
            log_content.append("")
            
            # Themes
            if result.themes:
                log_content.append("**Identified Themes:**")
                for theme in result.themes:
                    log_content.append(f"- {theme.name} (confidence: {theme.confidence:.2f}, expertise: {theme.expertise_level}, category: {theme.content_category})")
                log_content.append("")
            
            # Content Structure
            if result.content_structure:
                log_content.append("**Content Structure:**")
                log_content.append(f"- Clear Problem: {result.content_structure.has_clear_problem}")
                log_content.append(f"- Has Evidence: {result.content_structure.has_evidence}")
                log_content.append(f"- Multiple Perspectives: {result.content_structure.has_multiple_perspectives}")
                log_content.append(f"- Actionable Conclusions: {result.content_structure.has_actionable_conclusions}")
                log_content.append(f"- Logical Flow: {result.content_structure.logical_flow_score:.2f}")
                log_content.append("")
            
            log_content.append(f"- **Curation Reason**: {result.curation_reason}")
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
                log_content.append(f"- **Analytical Depth**: {result.quality_scores.analytical_depth:.2f}")
                log_content.append(f"- **Critical Thinking**: {result.quality_scores.critical_thinking:.2f}")
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
