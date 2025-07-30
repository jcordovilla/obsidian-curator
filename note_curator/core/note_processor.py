"""Note processor for handling markdown files and content extraction."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from markdown_it import MarkdownIt
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from .models import NoteAnalysis, QualityScore, PillarAnalysis, PillarType, NoteType, CurationAction
from ..models.llm_manager import LLMManager
from ..utils.content_processor import ContentProcessor
from ..utils.preprocessor import ContentPreprocessor, PreprocessingResult

logger = logging.getLogger(__name__)


class NoteProcessor:
    """Processes markdown notes for classification."""
    
    def __init__(self, config: Dict[str, any], llm_manager: LLMManager):
        """Initialize the note processor."""
        self.config = config
        self.llm_manager = llm_manager
        self.md_parser = MarkdownIt()
        self.content_processor = ContentProcessor()
        self.preprocessor = ContentPreprocessor()
        
        # Create pathspec for file filtering
        include_patterns = config.get('include_patterns', ['*.md'])
        exclude_patterns = config.get('exclude_patterns', [])
        
        self.include_spec = PathSpec.from_lines(GitWildMatchPattern, include_patterns)
        self.exclude_spec = PathSpec.from_lines(GitWildMatchPattern, exclude_patterns)
    
    def find_notes(self, vault_path: Path) -> List[Path]:
        """Find all markdown notes in the vault."""
        notes = []
        
        for file_path in vault_path.rglob('*'):
            if file_path.is_file():
                # Check if file matches include/exclude patterns
                relative_path = file_path.relative_to(vault_path)
                
                if self.include_spec.match_file(str(relative_path)) and \
                   not self.exclude_spec.match_file(str(relative_path)):
                    notes.append(file_path)
        
        logger.info(f"Found {len(notes)} notes in vault")
        return notes
    
    def process_note(self, file_path: Path, max_chars: int = 3000) -> NoteAnalysis:
        """Process a single note and return analysis."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file metadata
            stat = file_path.stat()
            file_size = stat.st_size
            created_date = datetime.fromtimestamp(stat.st_ctime)
            modified_date = datetime.fromtimestamp(stat.st_mtime)
            
            # Step 1: Preprocess content
            preprocessing_result = self.preprocessor.preprocess_note(content, file_path)
            
            # Step 2: Check if note should be processed
            if not preprocessing_result.should_process:
                logger.info(f"Skipping {file_path.name}: {preprocessing_result.processing_reason}")
                return self._create_skipped_analysis(file_path, preprocessing_result)
            
            # Step 3: Use cleaned content for analysis
            plain_text = preprocessing_result.cleaned_content
            
            # Step 4: Truncate if necessary
            if len(plain_text) > max_chars:
                logger.warning(f"Truncating {file_path.name} to {max_chars} characters")
                plain_text = plain_text[:max_chars]
            
            # Step 5: Analyze with LLM (including folder context)
            analysis_result = self.llm_manager.analyze_and_classify_note(plain_text, file_path)
            
            # Step 6: Add preprocessing metadata to analysis result
            analysis_result['folder_context'] = str(file_path.parent.name)
            analysis_result['preprocessing_metadata'] = preprocessing_result.metadata
            analysis_result['content_type'] = preprocessing_result.content_type.value
            analysis_result['language'] = preprocessing_result.language.value
            
            # Step 7: Validate and adjust quality scores based on content quality
            analysis_result = self._validate_and_adjust_scores(analysis_result, plain_text, file_path)
            
            # Step 8: Build NoteAnalysis object
            note_analysis = NoteAnalysis(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                created_date=created_date,
                modified_date=modified_date,
                word_count=preprocessing_result.word_count,
                character_count=preprocessing_result.character_count,
                has_frontmatter=preprocessing_result.metadata.get('has_frontmatter', False),
                has_attachments=preprocessing_result.metadata.get('has_attachments', False),
                attachment_count=len(re.findall(r'\[.*?\]\((.*?)\)', content)),
                primary_pillar=self._parse_pillar(analysis_result.get('primary_pillar')),
                secondary_pillars=[self._parse_pillar(p) for p in analysis_result.get('secondary_pillars', [])],
                note_type=self._parse_note_type(analysis_result.get('note_type')),
                quality_scores=QualityScore(**analysis_result.get('quality_scores', {})),
                pillar_analyses=self._parse_pillar_analyses(analysis_result.get('pillar_analyses', [])),
                curation_action=self._parse_curation_action(analysis_result.get('curation_action')),
                curation_reasoning=analysis_result.get('curation_reasoning', ''),
                confidence=analysis_result.get('confidence', 0.0)
            )
            
            return note_analysis
            
        except Exception as e:
            logger.error(f"Error processing note {file_path}: {e}")
            # Return a minimal analysis for failed notes
            return self._create_failed_analysis(file_path, str(e))
    
    def _extract_content(self, content: str) -> Tuple[str, bool, bool, int]:
        """Extract plain text and metadata from markdown content."""
        # Check for frontmatter
        has_frontmatter = content.startswith('---')
        
        # Extract attachments
        attachment_pattern = r'\[.*?\]\((.*?)\)'
        attachments = re.findall(attachment_pattern, content)
        has_attachments = len(attachments) > 0
        attachment_count = len(attachments)
        
        # Convert markdown to plain text
        rendered = self.md_parser.render(content)
        plain_text = re.sub(r'\n+', '\n', rendered)
        plain_text = re.sub(r'<[^>]+>', '', plain_text)  # Remove HTML tags
        plain_text = plain_text.strip()
        
        return plain_text, has_frontmatter, has_attachments, attachment_count
    
    def _is_evernote_clipping(self, content: str) -> bool:
        """Detect if content is from Evernote web clipping."""
        everote_indicators = [
            'Clipped from',
            'Evernote',
            'Web Clipper',
            'Saved from',
            'Source:'
        ]
        return any(indicator in content for indicator in everote_indicators)
    
    def normalize_note(self, note_analysis: NoteAnalysis, output_dir: Path) -> Path:
        """Normalize and save a note that passed classification."""
        if note_analysis.curation_action.value not in ['keep', 'refine']:
            return note_analysis.file_path
        
        try:
            # Read original content
            with open(note_analysis.file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Get note type and pillar
            note_type = note_analysis.note_type.value if note_analysis.note_type else 'default'
            pillar = note_analysis.primary_pillar.value if note_analysis.primary_pillar else 'general'
            
            # Normalize content structure
            normalized_content = self.content_processor.normalize_note_structure(
                original_content, note_type, pillar
            )
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate new filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{note_analysis.file_name.replace('.md', '')}_{timestamp}.md"
            output_path = output_dir / new_filename
            
            # Save normalized note
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(normalized_content)
            
            logger.info(f"Normalized note saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to normalize note {note_analysis.file_path}: {e}")
            return note_analysis.file_path
    
    def _parse_pillar(self, pillar_str: Optional[str]) -> Optional[PillarType]:
        """Parse pillar string to PillarType enum."""
        if not pillar_str:
            return None
        
        try:
            return PillarType(pillar_str.lower())
        except ValueError:
            logger.warning(f"Unknown pillar type: {pillar_str}")
            return None
    
    def _parse_note_type(self, note_type_str: Optional[str]) -> Optional[NoteType]:
        """Parse note type string to NoteType enum."""
        if not note_type_str:
            return None
        
        try:
            return NoteType(note_type_str.lower())
        except ValueError:
            logger.warning(f"Unknown note type: {note_type_str}")
            return None
    
    def _parse_curation_action(self, action_str: Optional[str]) -> CurationAction:
        """Parse curation action string to CurationAction enum."""
        if not action_str:
            return CurationAction.ARCHIVE
        
        try:
            return CurationAction(action_str.lower())
        except ValueError:
            logger.warning(f"Unknown curation action: {action_str}")
            return CurationAction.ARCHIVE
    
    def _parse_pillar_analyses(self, analyses: List[Dict]) -> List[PillarAnalysis]:
        """Parse pillar analyses from LLM response."""
        pillar_analyses = []
        
        for analysis in analyses:
            try:
                pillar = self._parse_pillar(analysis.get('pillar'))
                if pillar:
                    pillar_analyses.append(PillarAnalysis(
                        pillar=pillar,
                        relevance_score=analysis.get('relevance_score', 0.0),
                        confidence=analysis.get('confidence', 0.0),
                        reasoning=analysis.get('reasoning', ''),
                        keywords_found=analysis.get('keywords_found', [])
                    ))
            except Exception as e:
                logger.warning(f"Error parsing pillar analysis: {e}")
        
        return pillar_analyses
    
    def _create_failed_analysis(self, file_path: Path, error: str) -> NoteAnalysis:
        """Create a minimal analysis for failed notes."""
        return NoteAnalysis(
            file_path=file_path,
            file_name=file_path.name,
            file_size=0,
            word_count=0,
            character_count=0,
            has_frontmatter=False,
            has_attachments=False,
            attachment_count=0,
            quality_scores=QualityScore(
                relevance=0.0,
                depth=0.0,
                actionability=0.0,
                uniqueness=0.0,
                structure=0.0
            ),
            curation_action=CurationAction.ARCHIVE,
            curation_reasoning=f"Processing failed: {error}",
            confidence=0.0
        )
    
    def _create_skipped_analysis(self, file_path: Path, preprocessing_result: PreprocessingResult) -> NoteAnalysis:
        """Create a minimal analysis for skipped notes."""
        return NoteAnalysis(
            file_path=file_path,
            file_name=file_path.name,
            file_size=len(preprocessing_result.original_content.encode('utf-8')),
            word_count=preprocessing_result.word_count,
            character_count=preprocessing_result.character_count,
            has_frontmatter=preprocessing_result.metadata.get('has_frontmatter', False),
            has_attachments=preprocessing_result.metadata.get('has_attachments', False),
            attachment_count=len(re.findall(r'\[.*?\]\((.*?)\)', preprocessing_result.original_content)),
            quality_scores=QualityScore(
                relevance=0.0,
                depth=0.0,
                actionability=0.0,
                uniqueness=0.0,
                structure=0.0
            ),
            curation_action=CurationAction.ARCHIVE,
            curation_reasoning=f"Preprocessing skipped: {preprocessing_result.processing_reason}",
            confidence=0.0
        ) 

    def _validate_and_adjust_scores(self, analysis_result: Dict[str, Any], plain_text: str, file_path: Path) -> Dict[str, Any]:
        """Validate and adjust quality scores based on content quality."""
        # Get quality scores
        quality_scores = analysis_result.get('quality_scores', {})
        
        # Adjust scores based on content characteristics
        word_count = len(plain_text.split())
        
        # Adjust relevance score based on content length and quality
        if word_count < 50:
            quality_scores['relevance'] = min(quality_scores.get('relevance', 0.1), 0.3)
            quality_scores['depth'] = min(quality_scores.get('depth', 0.1), 0.2)
        
        # Adjust structure score based on content formatting
        if plain_text.count('\n') < 3:
            quality_scores['structure'] = min(quality_scores.get('structure', 0.1), 0.4)
        
        # Ensure all scores are within valid range
        for key in ['relevance', 'depth', 'actionability', 'uniqueness', 'structure']:
            if key in quality_scores:
                quality_scores[key] = max(0.0, min(1.0, quality_scores[key]))
            else:
                quality_scores[key] = 0.1
        
        analysis_result['quality_scores'] = quality_scores
        return analysis_result
    
    def _build_note_analysis(
        self,
        file_path: Path,
        file_size: int,
        created_date: datetime,
        modified_date: datetime,
        plain_text: str,
        has_frontmatter: bool,
        has_attachments: bool,
        attachment_count: int,
        analysis_result: Dict[str, Any],
        classification_result: Dict[str, Any]
    ) -> NoteAnalysis:
        """Build a NoteAnalysis object from components."""
        try:
            # Parse enums from strings
            primary_pillar = self._parse_pillar(analysis_result.get('primary_pillar'))
            note_type = self._parse_note_type(analysis_result.get('note_type'))
            curation_action = self._parse_curation_action(classification_result.get('curation_action'))
            
            # Parse quality scores
            quality_scores = QualityScore(
                relevance=analysis_result.get('quality_scores', {}).get('relevance', 0.1),
                depth=analysis_result.get('quality_scores', {}).get('depth', 0.1),
                actionability=analysis_result.get('quality_scores', {}).get('actionability', 0.1),
                uniqueness=analysis_result.get('quality_scores', {}).get('uniqueness', 0.1),
                structure=analysis_result.get('quality_scores', {}).get('structure', 0.1)
            )
            
            # Parse pillar analyses
            pillar_analyses = self._parse_pillar_analyses(analysis_result.get('pillar_analyses', []))
            
            return NoteAnalysis(
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                created_date=created_date,
                modified_date=modified_date,
                word_count=len(plain_text.split()),
                character_count=len(plain_text),
                has_frontmatter=has_frontmatter,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                primary_pillar=primary_pillar,
                secondary_pillars=[],  # Simplified for now
                note_type=note_type,
                quality_scores=quality_scores,
                pillar_analyses=pillar_analyses,
                curation_action=curation_action,
                curation_reasoning=classification_result.get('curation_reasoning', 'Analysis completed'),
                confidence=classification_result.get('confidence', 0.5)
            )
            
        except Exception as e:
            logger.error(f"Failed to build note analysis for {file_path}: {e}")
            return self._create_failed_analysis(file_path, str(e)) 