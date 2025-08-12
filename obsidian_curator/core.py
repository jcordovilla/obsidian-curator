"""Core orchestration logic for the Obsidian curation system."""

import random
import time
from pathlib import Path
from typing import List, Optional, Iterator

from loguru import logger
from tqdm import tqdm

from .models import (
    Note, CurationResult, CurationConfig, CurationStats, 
    VaultStructure, ProcessingCheckpoint
)
from .content_processor import ContentProcessor
from .ai_analyzer import AIAnalyzer
from .theme_classifier import ThemeClassifier
from .vault_organizer import VaultOrganizer


class ObsidianCurator:
    """Main orchestrator for the Obsidian curation process."""
    
    def __init__(self, config: CurationConfig):
        """Initialize the curator with configuration.
        
        Args:
            config: Curation configuration
        """
        self.config = config
        
        # Initialize components
        self.content_processor = ContentProcessor(
            clean_html=config.clean_html,
            preserve_metadata=config.preserve_metadata
        )
        self.ai_analyzer = AIAnalyzer(config)
        self.theme_classifier = ThemeClassifier()
        self.vault_organizer = VaultOrganizer(config)
        
        logger.info("Obsidian Curator initialized")
        logger.debug(f"Configuration: {config}")
    
    def curate_vault(self, input_path: Path, output_path: Path) -> CurationStats:
        """Curate an entire Obsidian vault.
        
        Args:
            input_path: Path to input vault
            output_path: Path to output curated vault
            
        Returns:
            CurationStats with processing results
        """
        start_time = time.time()
        
        logger.info(f"Starting vault curation: {input_path} -> {output_path}")
        
        try:
            # Step 1: Discover notes
            logger.info("Step 1: Discovering notes...")
            notes = self._discover_notes(input_path)
            
            if not notes:
                logger.warning("No notes found in input vault")
                return CurationStats(
                    total_notes=0,
                    curated_notes=0,
                    rejected_notes=0,
                    processing_time=time.time() - start_time,
                    themes_distribution={},
                    quality_distribution={}
                )
            
            logger.info(f"Found {len(notes)} notes to process")
            
            # Apply sample size if specified
            if self.config.sample_size and len(notes) > self.config.sample_size:
                notes = random.sample(notes, self.config.sample_size)
                logger.info(f"Using random sample of {len(notes)} notes")
            
            # Step 2: Process content
            logger.info("Step 2: Processing content...")
            processed_notes = self._process_notes(notes)
            
            # Step 3: AI analysis
            logger.info("Step 3: Performing AI analysis...")
            curation_results = self._analyze_notes(processed_notes)
            
            # Step 4: Create curated vault
            logger.info("Step 4: Creating curated vault...")
            stats = self._create_curated_vault(curation_results, output_path)
            
            # Update final statistics
            stats.processing_time = time.time() - start_time
            
            logger.info(f"Vault curation completed in {stats.processing_time:.1f}s")
            logger.info(f"Results: {stats.curated_notes}/{stats.total_notes} notes curated ({stats.curation_rate:.1f}%)")
            
            return stats
            
        except Exception as e:
            logger.error(f"Vault curation failed: {e}")
            raise
    
    def _discover_notes(self, input_path: Path) -> List[Note]:
        """Discover and load notes from the input vault.
        
        Args:
            input_path: Path to input vault
            
        Returns:
            List of discovered Note objects
        """
        notes = []
        
        # Find all markdown files
        markdown_files = []
        for pattern in ['*.md', '*.markdown']:
            markdown_files.extend(input_path.rglob(pattern))
        
        # Filter out system files and templates
        excluded_patterns = [
            '.obsidian',
            '.trash',
            'templates',
            'template',
            '.git'
        ]
        
        valid_files = []
        for file_path in markdown_files:
            # Skip hidden files and system directories
            if any(part.startswith('.') for part in file_path.parts):
                if not any(excluded in str(file_path).lower() for excluded in excluded_patterns):
                    continue
            
            # Skip excluded patterns
            if any(excluded in str(file_path).lower() for excluded in excluded_patterns):
                continue
            
            # Skip empty files
            try:
                if file_path.stat().st_size == 0:
                    continue
            except OSError:
                continue
            
            valid_files.append(file_path)
        
        # Sort by modification time (newest first)
        valid_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        logger.info(f"Found {len(valid_files)} valid markdown files")
        
        # Process files with progress bar
        with tqdm(valid_files, desc="Loading notes", unit="files") as pbar:
            for file_path in pbar:
                try:
                    note = self.content_processor.process_note(file_path)
                    notes.append(note)
                    pbar.set_postfix({"loaded": len(notes)})
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    continue
        
        logger.info(f"Successfully loaded {len(notes)} notes")
        return notes
    
    def _process_notes(self, notes: List[Note]) -> List[Note]:
        """Process notes through content cleaning and enhancement.
        
        Args:
            notes: List of notes to process
            
        Returns:
            List of processed notes
        """
        processed_notes = []
        
        with tqdm(notes, desc="Processing content", unit="notes") as pbar:
            for note in pbar:
                try:
                    # Content is already processed in content_processor.process_note()
                    # This step could add additional processing if needed
                    processed_notes.append(note)
                    pbar.set_postfix({"processed": len(processed_notes)})
                except Exception as e:
                    logger.warning(f"Failed to process note {note.title}: {e}")
                    continue
        
        logger.info(f"Processed {len(processed_notes)} notes")
        return processed_notes
    
    def _analyze_notes(self, notes: List[Note]) -> List[CurationResult]:
        """Analyze notes using AI for quality and theme assessment.
        
        Args:
            notes: List of notes to analyze
            
        Returns:
            List of curation results
        """
        curation_results = []
        
        with tqdm(notes, desc="AI analysis", unit="notes") as pbar:
            for note in pbar:
                try:
                    # Perform AI analysis
                    quality_scores, themes, curation_reason = self.ai_analyzer.analyze_note(note)
                    
                    # Determine if note should be curated
                    is_curated = self._should_curate(quality_scores, themes)
                    
                    # Create curation result
                    result = CurationResult(
                        note=note,
                        cleaned_content=note.content,  # Content already cleaned
                        quality_scores=quality_scores,
                        themes=themes,
                        is_curated=is_curated,
                        curation_reason=curation_reason,
                        processing_notes=[]
                    )
                    
                    curation_results.append(result)
                    
                    # Update progress
                    curated_count = sum(1 for r in curation_results if r.is_curated)
                    pbar.set_postfix({
                        "analyzed": len(curation_results),
                        "curated": curated_count,
                        "rate": f"{(curated_count/len(curation_results)*100):.1f}%"
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze note {note.title}: {e}")
                    # Create a failed result
                    from .models import QualityScore, Theme
                    default_scores = QualityScore(
                        overall=0.0, relevance=0.0, completeness=0.0, 
                        credibility=0.0, clarity=0.0
                    )
                    result = CurationResult(
                        note=note,
                        cleaned_content=note.content,
                        quality_scores=default_scores,
                        themes=[],
                        is_curated=False,
                        curation_reason=f"Analysis failed: {str(e)}",
                        processing_notes=[f"AI analysis failed: {str(e)}"]
                    )
                    curation_results.append(result)
                    continue
        
        curated_count = sum(1 for r in curation_results if r.is_curated)
        logger.info(f"Analyzed {len(curation_results)} notes: {curated_count} curated, {len(curation_results) - curated_count} rejected")
        
        return curation_results
    
    def _should_curate(self, quality_scores, themes) -> bool:
        """Determine if a note should be curated based on scores and themes.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            
        Returns:
            True if note should be curated
        """
        # Check quality and relevance thresholds
        if (quality_scores.overall >= self.config.quality_threshold and 
            quality_scores.relevance >= self.config.relevance_threshold):
            
            # If target themes specified, check theme alignment
            if self.config.target_themes:
                theme_names = [theme.name.lower() for theme in themes]
                theme_alignment = any(
                    target.lower() in theme_name or theme_name in target.lower()
                    for target in self.config.target_themes
                    for theme_name in theme_names
                )
                return theme_alignment
            
            return True
        
        return False
    
    def _create_curated_vault(self, curation_results: List[CurationResult], 
                             output_path: Path) -> CurationStats:
        """Create the curated vault with organized content.
        
        Args:
            curation_results: List of curation results
            output_path: Path to output vault
            
        Returns:
            CurationStats with results
        """
        # Filter curated results
        curated_results = [r for r in curation_results if r.is_curated]
        
        if not curated_results:
            logger.warning("No notes passed curation criteria")
            return CurationStats(
                total_notes=len(curation_results),
                curated_notes=0,
                rejected_notes=len(curation_results),
                processing_time=0.0,
                themes_distribution={},
                quality_distribution={}
            )
        
        # Create theme groups and vault structure
        theme_groups = self.theme_classifier.classify_themes(curated_results)
        vault_structure = self.theme_classifier.create_vault_structure(output_path, theme_groups)
        
        # Create curated vault
        stats = self.vault_organizer.create_curated_vault(
            curation_results, output_path, vault_structure
        )
        
        return stats
    
    def create_checkpoint(self, processed_notes: List[str], total_notes: int, 
                         current_step: str) -> ProcessingCheckpoint:
        """Create a processing checkpoint for resuming interrupted operations.
        
        Args:
            processed_notes: List of processed note paths
            total_notes: Total number of notes to process
            current_step: Current processing step
            
        Returns:
            ProcessingCheckpoint object
        """
        import hashlib
        
        # Create config hash for validation
        config_str = str(self.config.dict())
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        return ProcessingCheckpoint(
            processed_notes=processed_notes,
            total_notes=total_notes,
            current_step=current_step,
            config_hash=config_hash
        )
    
    def resume_from_checkpoint(self, checkpoint: ProcessingCheckpoint) -> bool:
        """Resume processing from a checkpoint.
        
        Args:
            checkpoint: Processing checkpoint to resume from
            
        Returns:
            True if resume is valid, False otherwise
        """
        import hashlib
        
        # Validate config hasn't changed
        config_str = str(self.config.dict())
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        if config_hash != checkpoint.config_hash:
            logger.warning("Configuration has changed since checkpoint was created")
            return False
        
        logger.info(f"Resuming from checkpoint: {checkpoint.current_step}")
        logger.info(f"Progress: {checkpoint.progress:.1f}% ({len(checkpoint.processed_notes)}/{checkpoint.total_notes})")
        
        return True
    
    def batch_process_vault(self, input_path: Path, output_path: Path, 
                           batch_size: int = 100) -> CurationStats:
        """Process a large vault in batches to manage memory usage.
        
        Args:
            input_path: Path to input vault
            output_path: Path to output vault
            batch_size: Number of notes to process per batch
            
        Returns:
            CurationStats with combined results
        """
        logger.info(f"Starting batch processing with batch size: {batch_size}")
        
        # Discover all notes first
        all_notes = self._discover_notes(input_path)
        
        if not all_notes:
            logger.warning("No notes found for batch processing")
            return CurationStats(
                total_notes=0, curated_notes=0, rejected_notes=0,
                processing_time=0.0, themes_distribution={}, quality_distribution={}
            )
        
        # Process in batches
        all_results = []
        total_batches = (len(all_notes) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(all_notes))
            batch_notes = all_notes[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_notes)} notes)")
            
            # Process batch
            processed_notes = self._process_notes(batch_notes)
            batch_results = self._analyze_notes(processed_notes)
            all_results.extend(batch_results)
            
            # Log batch progress
            batch_curated = sum(1 for r in batch_results if r.is_curated)
            logger.info(f"Batch {batch_num + 1} complete: {batch_curated}/{len(batch_results)} curated")
        
        # Create final curated vault
        logger.info("Creating final curated vault...")
        stats = self._create_curated_vault(all_results, output_path)
        
        logger.info(f"Batch processing complete: {stats.curated_notes}/{stats.total_notes} total curated")
        return stats