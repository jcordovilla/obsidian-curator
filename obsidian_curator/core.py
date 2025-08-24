"""Core orchestration logic for the Obsidian curation system."""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Iterator, Dict, Any

from loguru import logger
from tqdm import tqdm

from .models import (
    Note,
    CurationResult,
    CurationConfig,
    CurationStats,
    VaultStructure,
    ProcessingCheckpoint,
)
from .content_processor import ContentProcessor
from .ai_analyzer import AIAnalyzer
from .theme_classifier import ThemeClassifier
from .vault_organizer import VaultOrganizer
from .note_discovery import discover_markdown_files
from .triage import TriageManager
from .deduplication import DeduplicationManager


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
            preserve_metadata=config.preserve_metadata,
            intelligent_extraction=True,  # Enable intelligent extraction by default
            ai_model=config.ai_model  # Pass AI model for content curation
        )
        self.ai_analyzer = AIAnalyzer(config)
        self.theme_classifier = ThemeClassifier(
            similarity_threshold=config.theme_similarity_threshold
        )
        self.vault_organizer = VaultOrganizer(config)
        self.triage_manager = TriageManager(config.triage)
        self.dedup_manager = DeduplicationManager(config.dedupe)
        
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
            # Step 1: Discover notes (lightweight - just file paths)
            logger.info("Step 1: Discovering notes...")
            all_note_paths = self._discover_note_paths(input_path)
            
            if not all_note_paths:
                logger.warning("No notes found in input vault")
                return CurationStats(
                    total_notes=0,
                    curated_notes=0,
                    rejected_notes=0,
                    processing_time=time.time() - start_time,
                    themes_distribution={},
                    quality_distribution={}
                )
            
            logger.info(f"Found {len(all_note_paths)} note files in {input_path}")
            
            # Apply sample size IMMEDIATELY after discovery (before any processing)
            if self.config.sample_size and len(all_note_paths) > self.config.sample_size:
                selected_paths = random.sample(all_note_paths, self.config.sample_size)
                logger.info(f"Using random sample of {len(selected_paths)} notes from {len(all_note_paths)} available")
                
                # Log which files were selected for processing
                selected_files = [path.name for path in selected_paths]
                logger.info(f"Selected files for processing: {selected_files}")
            else:
                selected_paths = all_note_paths
                logger.info(f"Processing all {len(selected_paths)} notes")
            
            # Step 1.5: Process only the selected notes
            logger.info("Step 1.5: Processing selected notes...")
            notes = self._process_selected_notes(selected_paths)
            
            # Log content type distribution for analysis
            content_types = {}
            for note in notes:
                content_type = note.content_type.value
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            logger.info(f"Content type distribution: {content_types}")
            
            # Step 2: Process content
            logger.info("Step 2: Processing content...")
            processed_notes = self._process_notes(notes)
            
            # Step 3: AI analysis
            logger.info("Step 3: Performing AI analysis...")
            curation_results = self._analyze_notes(processed_notes)
            
            # Step 3.5: Deduplication
            logger.info("Step 3.5: Performing deduplication...")
            curation_results = self._deduplicate_results(curation_results)
            
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
    
    def _discover_note_paths(self, vault_path: Path) -> List[Path]:
        """Discover markdown files in the vault (lightweight - just paths).
        
        Args:
            vault_path: Path to the vault to search
            
        Returns:
            List of Path objects for markdown files
        """
        try:
            valid_files = discover_markdown_files(vault_path)
            logger.info(f"Found {len(valid_files)} valid markdown files")
            
            # Sort by modification time (newest first) for better sampling
            valid_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            return valid_files
            
        except Exception as e:
            logger.error(f"Failed to discover notes in {vault_path}: {e}")
            return []

    def _process_selected_notes(self, file_paths: List[Path]) -> List[Note]:
        """Process only the selected note files.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of processed Note objects
        """
        processor = ContentProcessor(
            clean_html=self.config.clean_html,
            preserve_metadata=self.config.preserve_metadata,
            intelligent_extraction=True,
            ai_model=self.config.ai_model
        )
        
        notes = []
        total_files = len(file_paths)
        processed_content_hashes = set()  # Track processed content to avoid duplicates
        processed_titles = set()  # Also track titles to catch near-duplicates
        
        with tqdm(file_paths, desc="Loading notes", unit="files") as pbar:
            for i, file_path in enumerate(pbar):
                pbar.set_postfix(loaded=len(notes))
                try:
                    note = processor.process_note(file_path)
                    
                    # Enhanced duplicate detection
                    # 1. Check content hash (for identical content)
                    content_hash = hash(note.content.strip().lower())
                    if content_hash in processed_content_hashes:
                        logger.warning(f"Skipping duplicate content: {note.title} (identical content)")
                        continue
                    
                    # 2. Check title similarity (for near-duplicate files)
                    normalized_title = self._normalize_title(note.title)
                    if normalized_title in processed_titles:
                        logger.warning(f"Skipping duplicate title: {note.title} (similar title)")
                        continue
                    
                    # 3. Check if content is too short to be meaningful (except audio content)
                    if len(note.content.strip()) < 100 and note.content_type != "audio_annotation":
                        logger.warning(f"Skipping minimal content: {note.title} ({len(note.content.strip())} chars)")
                        continue
                    
                    processed_content_hashes.add(content_hash)
                    processed_titles.add(normalized_title)
                    notes.append(note)
                    
                    # Log progress
                    logger.info(f"Processed note {i+1}/{total_files}: {note.title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    continue
        
        logger.info(f"Successfully processed {len(notes)} unique notes")
        return notes
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection."""
        import re
        # Convert to lowercase, remove special characters, normalize whitespace
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _discover_notes(self, input_path: Path) -> List[Note]:
        """Discover and load notes from the input vault.
        
        Args:
            input_path: Path to input vault
            
        Returns:
            List of discovered Note objects
        """
        notes = []
        valid_files = discover_markdown_files(input_path)

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
    
    def _analyze_notes(self, notes: List[Note], progress_callback=None) -> List[CurationResult]:
        """Analyze notes using AI for quality and theme assessment.
        
        Args:
            notes: List of notes to analyze
            progress_callback: Optional callback function(progress, message) for progress updates
            
        Returns:
            List of curation results
        """
        curation_results = []
        
        # Create output directory structure for immediate saving
        from .theme_classifier import ThemeClassifier
        from .vault_organizer import VaultOrganizer
        
        theme_classifier = ThemeClassifier()
        vault_organizer = VaultOrganizer(self.config)
        
        # Create temporary output directory for immediate saving
        # Use a more specific path that includes the target directory
        temp_dir_name = f"temp_curated_vault_{int(time.time())}"
        # Create temp directory in the current working directory for consistency
        temp_output_path = Path.cwd() / temp_dir_name
        temp_output_path.mkdir(exist_ok=True)
        
        # Store the temporary directory path for later use
        self._temp_output_path = temp_output_path.resolve()  # Use absolute path
        logger.info(f"Created temporary directory: {self._temp_output_path}")
        logger.info(f"Temporary directory exists: {self._temp_output_path.exists()}")
        logger.info(f"Temporary directory absolute: {self._temp_output_path.resolve()}")
        
        # Track saved notes to avoid duplicates
        saved_notes = set()
        
        logger.info(f"Starting analysis of {len(notes)} notes")
        logger.info(f"Temporary directory for saving: {temp_output_path}")
        
        with tqdm(notes, desc="AI analysis", unit="notes") as pbar:
            for i, note in enumerate(pbar):
                # Update progress if callback provided
                if progress_callback:
                    progress = 20 + int((i / len(notes)) * 60)  # 20% to 80%
                    progress_callback(progress, f"Analyzing: {note.title[:30]}...")
                try:
                    # Pre-filter obviously low-value content before AI analysis
                    if not self._is_worth_analyzing(note):
                        # Create rejection result immediately
                        from .models import QualityScore, ContentStructure
                        default_scores = QualityScore(
                            overall=0.1, relevance=0.1, completeness=0.1, 
                            credibility=0.1, clarity=0.1,
                            analytical_depth=0.1, evidence_quality=0.1, critical_thinking=0.1,
                            argument_structure=0.1, practical_value=0.1
                        )
                        default_structure = ContentStructure(
                            has_clear_problem=False, has_evidence=False, has_multiple_perspectives=False,
                            has_actionable_conclusions=False, logical_flow_score=0.1,
                            argument_coherence=0.1, conclusion_strength=0.1
                        )
                        result = CurationResult(
                            note=note,
                            cleaned_content=note.content,
                            quality_scores=default_scores,
                            themes=[],
                            content_structure=default_structure,
                            is_curated=False,
                            curation_reason="Pre-filtered: Low-value content (minimal, personal, or non-professional)",
                            processing_notes=["Rejected by pre-filter"],
                            route_info=None,
                            needs_triage=False,
                            triage_info=None,
                            is_duplicate=False,
                            duplicate_info=None
                        )
                        curation_results.append(result)
                        continue
                    
                    # Perform AI analysis with enhanced metrics
                    analysis_result = self.ai_analyzer.analyze_note(note)
                    if len(analysis_result) == 5:
                        quality_scores, themes, content_structure, curation_reason, route_info = analysis_result
                    else:
                        # Backward compatibility
                        quality_scores, themes, content_structure, curation_reason = analysis_result
                        route_info = None
                    
                    # Check if this note needs triage
                    thresholds = {
                        "overall": self.config.quality_threshold,
                        "relevance": self.config.relevance_threshold,
                        "professional_writing": getattr(self.config, 'professional_writing_threshold', 0.65),
                        "analytical_depth": getattr(self.config, 'analytical_depth_threshold', 0.65)
                    }
                    
                    # Check for existing triage decision
                    existing_decision = self.triage_manager.get_decision(note)
                    if existing_decision:
                        is_curated = existing_decision == "keep"
                        needs_triage = False
                        triage_info = {"previous_decision": existing_decision}
                        logger.info(f"Using previous triage decision for {note.title}: {existing_decision}")
                    else:
                        # Check if triage is needed
                        needs_triage = self.triage_manager.needs_triage(note, quality_scores, thresholds)
                        
                        if needs_triage:
                            # For now, apply standard curation logic but mark for triage
                            content_length = len(note.content) if note.content else 0
                            suggested_decision = "keep" if self._should_curate(quality_scores, themes, content_length, note.content_type) else "discard"
                            
                            # Create triage item
                            triage_item = self.triage_manager.create_triage_item(
                                note, quality_scores, thresholds, suggested_decision,
                                f"Borderline scores in gray zone (margin: {self.config.triage.margin})"
                            )
                            
                            # Defer final decision - for CLI mode, we'll use suggested decision
                            # GUI can handle this differently
                            is_curated = suggested_decision == "keep"
                            triage_info = {
                                "fingerprint": triage_item.fingerprint,
                                "suggested_decision": suggested_decision,
                                "reason": triage_item.reason
                            }
                        else:
                            # Standard curation decision
                            content_length = len(note.content) if note.content else 0
                            is_curated = self._should_curate(quality_scores, themes, content_length, note.content_type)
                            triage_info = None
                    
                    # Create curation result with enhanced metrics
                    result = CurationResult(
                        note=note,
                        cleaned_content=note.content,  # Use the already cleaned content from processor
                        quality_scores=quality_scores,
                        themes=themes,
                        content_structure=content_structure,  # NEW: Include content structure
                        is_curated=is_curated,
                        curation_reason=curation_reason,
                        processing_notes=[],
                        route_info=route_info,  # NEW: Include routing information
                        needs_triage=needs_triage,  # NEW: Triage flag
                        triage_info=triage_info,  # NEW: Triage information
                        is_duplicate=False,  # NEW: Duplicate flag (will be updated in deduplication)
                        duplicate_info=None  # NEW: Duplicate information
                    )
                    
                    curation_results.append(result)
                    
                    # Save curated notes immediately to avoid losing work
                    if is_curated and note.title not in saved_notes:
                        try:
                            self._save_note_immediately(result, temp_output_path, theme_classifier)
                            saved_notes.add(note.title)
                            logger.info(f"Saved note immediately: {note.title}")
                        except Exception as save_error:
                            logger.warning(f"Failed to save note {note.title}: {save_error}")
                    
                    # Update progress
                    curated_count = sum(1 for r in curation_results if r.is_curated)
                    pbar.set_postfix({
                        "analyzed": len(curation_results),
                        "curated": curated_count,
                        "saved": len(saved_notes),
                        "rate": f"{(curated_count/len(curation_results)*100):.1f}%"
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze note {note.title}: {e}")
                    # Create a failed result with enhanced defaults
                    from .models import QualityScore, Theme, ContentStructure
                    default_scores = QualityScore(
                        overall=0.0, relevance=0.0, completeness=0.0, 
                        credibility=0.0, clarity=0.0,
                        analytical_depth=0.0, evidence_quality=0.0, critical_thinking=0.0,
                        argument_structure=0.0, practical_value=0.0
                    )
                    default_structure = ContentStructure(
                        has_clear_problem=False, has_evidence=False, has_multiple_perspectives=False,
                        has_actionable_conclusions=False, logical_flow_score=0.0,
                        argument_coherence=0.0, conclusion_strength=0.0
                    )
                    result = CurationResult(
                        note=note,
                        cleaned_content=note.content,
                        quality_scores=default_scores,
                        themes=[],
                        content_structure=default_structure,  # NEW: Include content structure
                        is_curated=False,
                        curation_reason=f"Analysis failed: {str(e)}",
                        processing_notes=[f"AI analysis failed: {str(e)}"],
                        route_info=None,
                        needs_triage=False,
                        triage_info=None,
                        is_duplicate=False,
                        duplicate_info=None
                    )
                    curation_results.append(result)
                    continue
        
        curated_count = sum(1 for r in curation_results if r.is_curated)
        rejected_count = len(curation_results) - curated_count
        logger.info(f"Analyzed {len(curation_results)} notes: {curated_count} curated, {rejected_count} rejected")
        logger.info(f"Saved {len(saved_notes)} notes to temporary directory: {temp_output_path}")
        
        # Store the temporary directory path for later use
        self._temp_output_path = temp_output_path
        
        # Log detailed curation decisions for analysis
        for result in curation_results:
            status = "CURATED" if result.is_curated else "REJECTED"
            quality = result.quality_scores.overall
            relevance = result.quality_scores.relevance
            logger.info(f"{status}: '{result.note.title[:50]}...' (Q:{quality:.2f}, R:{relevance:.2f}) - {result.curation_reason}")
        
        return curation_results
    
    def _deduplicate_results(self, curation_results: List[CurationResult]) -> List[CurationResult]:
        """Perform deduplication on curation results.
        
        Args:
            curation_results: List of curation results
            
        Returns:
            List of deduplicated curation results
        """
        if not self.config.dedupe.enabled:
            logger.info("Deduplication disabled, skipping")
            return curation_results
        
        logger.info(f"Starting deduplication on {len(curation_results)} results")
        
        # Detect duplicates
        canonical_results, duplicate_clusters = self.dedup_manager.detect_duplicates(curation_results)
        
        # Mark duplicates in clusters
        self.dedup_manager.mark_duplicates_in_clusters(duplicate_clusters)
        
        # Generate duplicate report
        if self.config.dedupe.report_path and duplicate_clusters:
            output_path = Path(self.config.dedupe.report_path)
            if not output_path.is_absolute():
                # Make relative to output directory (we'll need to get this from somewhere)
                output_path = Path("metadata") / output_path.name
            
            self.dedup_manager.generate_duplicate_report(duplicate_clusters, str(output_path))
        
        # Count results
        total_duplicates = sum(len(cluster) - 1 for cluster in duplicate_clusters)
        logger.info(f"Deduplication complete: {len(canonical_results)} unique, {total_duplicates} duplicates removed")
        
        # Return all results (including duplicates marked for reference)
        # The vault organizer will decide which ones to actually save
        return curation_results
    
    def _should_curate(self, quality_scores, themes, content_length: int = 0, content_type=None) -> bool:
        """Determine if a note should be curated based on scores and themes.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            content_length: Length of cleaned content in characters
            content_type: Content type for type-specific rules
            
        Returns:
            True if note should be curated
        """
        try:
            # Get content-type specific rules
            content_type_str = content_type.value if content_type and hasattr(content_type, 'value') else 'DEFAULT'
            type_rules = None
            
            if hasattr(self.config, 'content_types'):
                type_rules = getattr(self.config.content_types, content_type_str, None)
                if not type_rules:
                    type_rules = getattr(self.config.content_types, 'DEFAULT', None)
            
            # Use content-type specific thresholds if available
            if type_rules and type_rules.thresholds:
                quality_threshold = type_rules.thresholds.get('overall', self.config.quality_threshold)
                relevance_threshold = type_rules.thresholds.get('relevance', self.config.relevance_threshold)
                analytical_depth_threshold = type_rules.thresholds.get('analytical_depth', getattr(self.config, 'analytical_depth_threshold', 0.65))
                min_content_length = type_rules.min_length
            else:
                # Fall back to global thresholds
                quality_threshold = self.config.quality_threshold
                relevance_threshold = self.config.relevance_threshold
                analytical_depth_threshold = getattr(self.config, 'analytical_depth_threshold', 0.65)
                min_content_length = getattr(self.config, 'min_content_length', 300)
            
            # Enhanced quality thresholds for analytical content
            meets_quality = quality_scores.overall >= quality_threshold
            meets_relevance = quality_scores.relevance >= relevance_threshold
            meets_analytical_depth = quality_scores.analytical_depth >= analytical_depth_threshold
            
            # Check minimum content length for usefulness
            meets_length_requirement = content_length >= min_content_length
            
            # Professional writing quality assessment (higher standards)
            professional_writing_score = (
                quality_scores.analytical_depth + 
                quality_scores.evidence_quality + 
                quality_scores.critical_thinking + 
                quality_scores.argument_structure
            ) / 4.0
            
            # Use content-type specific professional writing threshold if available
            if type_rules and type_rules.thresholds:
                professional_threshold = type_rules.thresholds.get('professional_writing', getattr(self.config, 'professional_writing_threshold', 0.65))
            else:
                professional_threshold = getattr(self.config, 'professional_writing_threshold', 0.65)
            meets_professional = professional_writing_score >= professional_threshold
            
            # Theme relevance check
            has_relevant_themes = False
            if themes:
                # Check if any theme has sufficient confidence
                confident_themes = [t for t in themes if t.confidence >= 0.5]
                has_relevant_themes = len(confident_themes) > 0
                
                # If target themes are specified, check alignment
                if self.config.target_themes:
                    theme_alignment = any(
                        any(target.lower() in theme.name.lower() or 
                             any(target.lower() in keyword.lower() for keyword in theme.keywords)
                             for target in self.config.target_themes)
                        for theme in confident_themes
                    )
                    has_relevant_themes = has_relevant_themes and theme_alignment
            
            # Intelligent curation decision logic
            # 1. High-quality content: meets all criteria
            high_quality = meets_quality and meets_relevance and meets_analytical_depth
            
            # 2. Good content: meets basic criteria with some flexibility
            good_quality = (meets_quality or meets_relevance) and has_relevant_themes
            
            # 3. Specialized content: may not meet general criteria but has value
            specialized_content = (
                content_length > 200 and  # Has some substance
                has_relevant_themes and   # Is relevant
                any(theme.confidence > 0.6 for theme in themes)  # High-confidence theme
            )
            
            # 4. Content length considerations
            substantial_content = content_length >= min_content_length
            
            # Decision logic: curate if any criteria met
            should_curate = False
            curation_reasons = []
            
            if high_quality and substantial_content:
                should_curate = True
                curation_reasons.append("High quality with substantial content")
            elif good_quality and substantial_content:
                should_curate = True
                curation_reasons.append("Good quality with substantial content")
            elif specialized_content:
                should_curate = True
                curation_reasons.append("Specialized relevant content")
            elif meets_quality and content_length > 150:  # Lower bar for short but quality content
                should_curate = True
                curation_reasons.append("Quality content despite length")
            
            if not should_curate:
                curation_reasons.append("Did not meet minimum quality or relevance criteria")
            
            # Detailed debug logging
            logger.info(f"Curation decision details ({content_type_str}):")
            logger.info(f"  Quality scores: overall={quality_scores.overall:.2f}, relevance={quality_scores.relevance:.2f}")
            logger.info(f"  Thresholds: quality={quality_threshold}, relevance={relevance_threshold}, min_length={min_content_length}")
            logger.info(f"  Meets quality: {meets_quality}, meets relevance: {meets_relevance}")
            logger.info(f"  Themes: {len(themes)} found, relevant: {has_relevant_themes}")
            logger.info(f"  Content length: {content_length} chars")
            logger.info(f"  Final decision: {'CURATE' if should_curate else 'REJECT'}")
            
            return should_curate
            
        except Exception as e:
            logger.error(f"Error in curation decision for note: {e}")
            return False
    
    def _is_worth_analyzing(self, note: Note) -> bool:
        """Pre-filter to determine if a note is worth AI analysis.
        
        Args:
            note: Note to evaluate
            
        Returns:
            True if note should be analyzed, False if it should be rejected immediately
        """
        title = note.title.lower()
        content = note.content.lower() if note.content else ""
        content_length = len(note.content.strip()) if note.content else 0
        
        # 1. Reject obviously personal/trivial content by title patterns
        trivial_patterns = [
            "sim card", "tarjeta sim", "host a .net", "host application",
            "password", "login", "username", "wifi", "wi-fi",
            "grocery", "shopping list", "todo", "to-do", "reminder",
            "birthday", "anniversary", "personal", "diary", "journal",
            "photo", "image", "screenshot", "selfie"
        ]
        
        for pattern in trivial_patterns:
            if pattern in title:
                logger.info(f"Pre-filter rejection: Trivial title pattern '{pattern}' in '{note.title}'")
                return False
        
        # 2. Reject minimal content that's clearly not valuable
        if content_length < 50:
            logger.info(f"Pre-filter rejection: Too short ({content_length} chars): '{note.title}'")
            return False
        
        # 3. Reject content that's mostly attachments/links with no substance
        if content_length < 200:
            # Count meaningful words vs attachments/links
            meaningful_words = len([word for word in content.split() 
                                  if len(word) > 3 and not word.startswith('http') 
                                  and '[[' not in word and '![[' not in word])
            
            if meaningful_words < 10:
                logger.info(f"Pre-filter rejection: Minimal meaningful content ({meaningful_words} words): '{note.title}'")
                return False
        
        # 4. Reject purely administrative/metadata content
        admin_patterns = [
            "scan", "scanned", "escaneado", "img_", "screenshot",
            "untitled", "new note", "template", "example"
        ]
        
        for pattern in admin_patterns:
            if pattern in title and content_length < 300:
                logger.info(f"Pre-filter rejection: Administrative pattern '{pattern}': '{note.title}'")
                return False
        
        # 5. Content quality heuristics - reject obvious low-value content
        if content_length > 100:
            # Check for professional indicators
            professional_indicators = [
                "analysis", "strategy", "policy", "governance", "infrastructure",
                "management", "development", "implementation", "framework",
                "research", "study", "report", "assessment", "evaluation",
                "planning", "project", "business", "economic", "financial",
                "technical", "engineering", "construction", "procurement"
            ]
            
            # Personal/non-professional indicators
            personal_indicators = [
                "i think", "i feel", "my opinion", "personally", "imho",
                "just saying", "random thoughts", "quick note", "reminder",
                "don't forget", "call mom", "buy", "grocery", "appointment"
            ]
            
            professional_count = sum(1 for indicator in professional_indicators 
                                   if indicator in content)
            personal_count = sum(1 for indicator in personal_indicators 
                               if indicator in content)
            
            # If clearly personal and no professional content, reject
            if personal_count > 2 and professional_count == 0:
                logger.info(f"Pre-filter rejection: Personal content pattern: '{note.title}'")
                return False
        
        # 6. Language and formatting checks for professional content
        if content_length > 50:
            # Reject content that's mostly special characters or formatting
            text_chars = sum(1 for c in content if c.isalnum() or c.isspace())
            text_ratio = text_chars / len(content)
            
            if text_ratio < 0.7:  # Less than 70% actual text
                logger.info(f"Pre-filter rejection: Too much formatting/symbols ({text_ratio:.2f} text ratio): '{note.title}'")
                return False
        
        # 7. Check for completely extracted content that failed processing
        if "![[" in content and content_length < 100:
            # Mostly just attachment references
            logger.info(f"Pre-filter rejection: Mostly attachments: '{note.title}'")
            return False
        
        logger.debug(f"Pre-filter passed: '{note.title}' ({content_length} chars)")
        return True
    
    def _save_note_immediately(self, result, output_path, theme_classifier):
        """Save a curated note immediately to disk to avoid losing work."""
        try:
            logger.info(f"Attempting to save note immediately: {result.note.title}")
            logger.info(f"Output path: {output_path}")
            logger.info(f"Output path exists: {output_path.exists()}")
            
            # Classify themes and create folder structure
            theme_groups = theme_classifier.classify_themes([result])
            logger.info(f"Theme groups: {theme_groups}")
            
            # Create theme folders
            for theme_name, notes in theme_groups.items():
                theme_path = output_path / theme_name
                logger.info(f"Creating theme path: {theme_path}")
                theme_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Theme path created: {theme_path.exists()}")
                
                # Save note to appropriate theme folder
                for note_result in notes:
                    if note_result.is_curated:
                        # Create filename
                        safe_title = "".join(c for c in note_result.note.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title.replace(' ', '_').lower()
                        filename = f"{safe_title}.md"
                        file_path = theme_path / filename
                        logger.info(f"Creating file: {file_path}")
                        
                        # Create curated note content
                        curated_content = self._create_curated_note_content(note_result)
                        logger.info(f"Content length: {len(curated_content)} characters")
                        
                        # Write to file immediately
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(curated_content)
                        
                        logger.info(f"Successfully saved note immediately: {file_path}")
                        logger.info(f"File exists after save: {file_path.exists()}")
                        logger.info(f"File size: {file_path.stat().st_size} bytes")
                        
        except Exception as e:
            logger.error(f"Failed to save note immediately: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _create_curated_note_content(self, result):
        """Create the content for a curated note."""
        note = result.note
        quality = result.quality_scores
        themes = result.themes
        
        # Create YAML frontmatter
        frontmatter = f"""---
title: {note.title}
curated_date: {datetime.now().isoformat()}
        source: {note.source_url or 'Unknown'}
tags:
"""
        
        for theme in themes:
            frontmatter += f"  - {theme.name}\n"
        
        frontmatter += f"language: {note.metadata.get('language', 'en')}\n---\n\n"
        
        # Create content
        content = f"# {note.title}\n\n"
        content += "## Quality Assessment\n\n"
        content += f"- **Overall Quality**: {quality.overall:.2f}/1.0\n"
        content += f"- **Relevance**: {quality.relevance:.2f}/1.0\n"
        content += f"- **Analytical Depth**: {quality.analytical_depth:.2f}/1.0\n"
        content += f"- **Critical Thinking**: {quality.critical_thinking:.2f}/1.0\n"
        content += f"- **Evidence Quality**: {quality.evidence_quality:.2f}/1.0\n"
        content += f"- **Argument Structure**: {quality.argument_structure:.2f}/1.0\n"
        content += f"- **Practical Value**: {quality.practical_value:.2f}/1.0\n\n"
        
        content += "## Identified Themes\n\n"
        for theme in themes:
            content += f"- **{theme.name}** (confidence: {theme.confidence:.2f})\n"
        
        content += "\n## Content\n\n"
        content += note.content
        
        return frontmatter + content
    
    def _create_curated_vault(self, curation_results: List[CurationResult], 
                             output_path: Path) -> CurationStats:
        """Create the curated vault with organized content.
        
        Args:
            curation_results: List of curation results
            output_path: Path to output vault
            
        Returns:
            CurationStats with results
        """
        logger.info(f"Creating curated vault for {len(curation_results)} results")
        logger.info(f"Output path: {output_path}")
        logger.info(f"Output path exists: {output_path.exists()}")
        
        # Filter curated results
        curated_results = [r for r in curation_results if r.is_curated]
        logger.info(f"Curated results: {len(curated_results)}")
        
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
        
        # Check if notes were already saved during processing
        # First check if we have a stored temporary directory path
        if hasattr(self, '_temp_output_path'):
            logger.info(f"Found stored temporary path: {self._temp_output_path}")
            logger.info(f"Stored temp path exists: {self._temp_output_path.exists()}")
            if self._temp_output_path.exists():
                latest_temp_dir = self._temp_output_path
                logger.info(f"Using stored temporary directory: {latest_temp_dir}")
            else:
                logger.warning("Stored temporary path does not exist")
                latest_temp_dir = None
        else:
            logger.info("No stored temporary path found")
            latest_temp_dir = None
        
        if not latest_temp_dir:
            # Fallback: Look for temporary directories that might contain saved notes
            import glob
            temp_dirs = glob.glob("temp_curated_vault_*")
            logger.info(f"Found {len(temp_dirs)} temporary directories: {temp_dirs}")
            
            if temp_dirs:
                # Use the most recent temporary directory
                latest_temp_dir = max(temp_dirs, key=lambda x: int(x.split('_')[-1]))
                latest_temp_dir = Path(latest_temp_dir)
                logger.info(f"Using fallback temporary directory: {latest_temp_dir}")
            else:
                latest_temp_dir = None
                logger.warning("No temporary directories found")
        
        if latest_temp_dir and latest_temp_dir.exists():
            logger.info(f"Found temporary directory with saved notes: {latest_temp_dir}")
            logger.info(f"Temporary directory contents:")
            for item in latest_temp_dir.rglob("*"):
                if item.is_file():
                    logger.info(f"  File: {item.relative_to(latest_temp_dir)} ({item.stat().st_size} bytes)")
                elif item.is_dir():
                    logger.info(f"  Directory: {item.relative_to(latest_temp_dir)}")
            
            # Move saved notes to final output location
            import shutil
            try:
                if output_path.exists():
                    logger.info(f"Removing existing output path: {output_path}")
                    shutil.rmtree(output_path)
                
                logger.info(f"Moving {latest_temp_dir} to {output_path}")
                shutil.move(str(latest_temp_dir), str(output_path))
                logger.info(f"Successfully moved saved notes from {latest_temp_dir} to {output_path}")
                
                # Create final metadata and statistics
                stats = self._create_final_metadata(curation_results, output_path)
                
                # Clean up the stored temporary path
                if hasattr(self, '_temp_output_path'):
                    delattr(self, '_temp_output_path')
                
                return stats
                
            except Exception as e:
                logger.error(f"Failed to move saved notes: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fall back to normal processing
        else:
            logger.warning("No temporary directory found or it doesn't exist")
        
        # Normal processing if no temporary directory found
        logger.info("Creating curated vault with normal processing...")
        
        # Create theme groups and vault structure
        theme_groups = self.theme_classifier.classify_themes(curated_results)
        vault_structure = self.theme_classifier.create_vault_structure(output_path, theme_groups)
        
        # Create curated vault
        stats = self.vault_organizer.create_curated_vault(
            curation_results, output_path, vault_structure
        )
        
        return stats
    
    def _create_final_metadata(self, curation_results: List[CurationResult], output_path: Path) -> CurationStats:
        """Create final metadata and statistics for the curated vault."""
        try:
            # Create metadata directory
            metadata_path = output_path / "metadata"
            metadata_path.mkdir(exist_ok=True)
            
            # Calculate statistics
            total_notes = len(curation_results)
            curated_notes = sum(1 for r in curation_results if r.is_curated)
            rejected_notes = total_notes - curated_notes
            
            # Create theme distribution
            themes_distribution = {}
            for result in curation_results:
                if result.is_curated:
                    for theme in result.themes:
                        theme_name = theme.name
                        themes_distribution[theme_name] = themes_distribution.get(theme_name, 0) + 1
            
            # Create quality distribution
            quality_distribution = {"0.6-0.8": curated_notes}  # Simplified for now
            
            # Create stats object
            from .models import CurationStats
            stats = CurationStats(
                total_notes=total_notes,
                curated_notes=curated_notes,
                rejected_notes=rejected_notes,
                processing_time=0.0,  # Will be set by caller
                themes_distribution=themes_distribution,
                quality_distribution=quality_distribution
            )
            
            # Save statistics
            import json
            with open(metadata_path / "statistics.json", 'w', encoding='utf-8') as f:
                json.dump(stats.dict(), f, indent=2, default=str)
            
            # Save configuration
            config_data = {
                'curation_config': self.config.dict(),
                'generated_date': datetime.now().isoformat(),
                'vault_structure': {
                    'root_path': str(output_path),
                    'theme_folders': {theme: str(output_path / theme) for theme in themes_distribution.keys()},
                    'metadata_folder': str(metadata_path)
                }
            }
            
            with open(metadata_path / "configuration.json", 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            logger.info(f"Created final metadata for {curated_notes} curated notes")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to create final metadata: {e}")
            # Return basic stats on error
            return CurationStats(
                total_notes=len(curation_results),
                curated_notes=sum(1 for r in curation_results if r.is_curated),
                rejected_notes=sum(1 for r in curation_results if not r.is_curated),
                processing_time=0.0,
                themes_distribution={},
                quality_distribution={}
            )
    
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
    
    def get_triage_stats(self) -> Dict[str, Any]:
        """Get triage statistics.
        
        Returns:
            Dictionary with triage statistics
        """
        return self.triage_manager.get_stats()
    
    def get_pending_triage_items(self) -> List:
        """Get pending triage items for GUI display.
        
        Returns:
            List of pending triage items
        """
        return self.triage_manager.get_pending_items()
    
    def resolve_triage_item(self, fingerprint: str, decision: str) -> bool:
        """Resolve a triage item with human decision.
        
        Args:
            fingerprint: Item fingerprint
            decision: Human decision: "keep" or "discard"
            
        Returns:
            True if resolved successfully
        """
        return self.triage_manager.resolve_triage_item(fingerprint, decision)