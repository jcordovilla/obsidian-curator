"""Advanced content preprocessing module for note classification."""

import logging
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum

import markdown_it
from rich.console import Console

from .evernote_cleaner import EvernoteClippingCleaner, EvernoteCleaningResult

logger = logging.getLogger(__name__)
console = Console()


class ContentType(Enum):
    """Types of content that can be detected."""
    TECHNICAL_REPORT = "technical_report"
    MEETING_NOTES = "meeting_notes"
    STRUCTURED_CONTENT = "structured_content"
    TEMPLATE = "template"
    DRAFT = "draft"
    EVERNOTE_CLIPPING = "evernote_clipping"
    GENERAL = "general"


class Language(Enum):
    """Supported languages."""
    ENGLISH = "english"
    SPANISH = "spanish"
    FRENCH = "french"
    GERMAN = "german"
    UNKNOWN = "unknown"


@dataclass
class PreprocessingResult:
    """Result of preprocessing a note."""
    original_content: str
    cleaned_content: str
    content_type: ContentType
    language: Language
    quality_score: float
    word_count: int
    character_count: int
    structure_score: float
    has_meaningful_content: bool
    issues: List[str]
    metadata: Dict[str, Any]
    should_process: bool
    processing_reason: str


class ContentPreprocessor:
    """Advanced content preprocessor for note classification."""
    
    def __init__(self):
        """Initialize the preprocessor."""
        self.md_parser = markdown_it.MarkdownIt()
        self.evernote_cleaner = EvernoteClippingCleaner()
        
        # Quality thresholds
        self.min_word_count = 20
        self.min_character_count = 100
        self.min_structure_score = 0.3
        self.min_quality_score = 0.4
        
        # Content type indicators
        self.technical_terms = {
            'api', 'bim', 'ppp', 'infrastructure', 'digital', 'transformation',
            'governance', 'risk', 'management', 'project', 'finance', 'concession',
            'public-private', 'partnership', 'investment', 'development', 'construction',
            'transport', 'energy', 'water', 'telecommunications', 'healthcare',
            'education', 'social', 'economic', 'environmental', 'sustainability'
        }
        
        self.draft_indicators = {
            'draft', 'todo', 'temp', 'temporary', 'note to self', 'reminder',
            'placeholder', 'to do', 'pending', 'incomplete', 'unfinished'
        }
        
        self.template_indicators = {
            'template', 'placeholder', 'example', 'sample', 'format',
            'structure', 'outline', 'framework', 'model'
        }
        
        self.evernote_indicators = {
            'clipped from', 'evernote', 'web clipper', 'saved from', 'source:',
            'original url', 'clipped on', 'tags:', 'notebook:'
        }
    
    def preprocess_note(self, content: str, file_path: Path) -> PreprocessingResult:
        """Preprocess a note and determine if it should be processed further."""
        try:
            # Step 1: Clean Evernote clippings if detected
            evernote_result = self.evernote_cleaner.clean_evernote_clipping(content, file_path)
            if evernote_result.is_evernote_clipping:
                content = evernote_result.cleaned_content
                logger.info(f"Cleaned Evernote clipping: {evernote_result.cleaning_stats['reduction_ratio']:.1%} size reduction")
            
            # Step 2: Extract and clean content
            cleaned_content = self._extract_clean_content(content)
            
            # Step 3: Detect content type
            content_type = self._detect_content_type(content, cleaned_content)
            
            # Step 4: Detect language
            language = self._detect_language(content)
            
            # Step 5: Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(content, cleaned_content)
            
            # Step 6: Identify issues
            issues = self._identify_issues(content, cleaned_content, quality_metrics)
            
            # Step 7: Determine if should process
            should_process, reason = self._should_process_note(
                content_type, quality_metrics, issues
            )
            
            # Step 8: Build metadata
            metadata = self._build_metadata(
                content, cleaned_content, content_type, language, quality_metrics, issues, evernote_result
            )
            
            return PreprocessingResult(
                original_content=content,
                cleaned_content=cleaned_content,
                content_type=content_type,
                language=language,
                quality_score=quality_metrics['overall_score'],
                word_count=quality_metrics['word_count'],
                character_count=quality_metrics['character_count'],
                structure_score=quality_metrics['structure_score'],
                has_meaningful_content=quality_metrics['has_meaningful_content'],
                issues=issues,
                metadata=metadata,
                should_process=should_process,
                processing_reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing {file_path}: {e}")
            return self._create_failed_result(content, str(e))
    
    def _extract_clean_content(self, content: str) -> str:
        """Extract and clean content from markdown."""
        # Remove frontmatter
        if content.startswith('---'):
            frontmatter_end = content.find('---', 3)
            if frontmatter_end != -1:
                content = content[frontmatter_end + 3:]
        
        # Convert markdown to plain text
        rendered = self.md_parser.render(content)
        
        # Remove HTML tags
        plain_text = re.sub(r'<[^>]+>', '', rendered)
        
        # Remove excessive whitespace
        plain_text = re.sub(r'\n+', '\n', plain_text)
        plain_text = re.sub(r' +', ' ', plain_text)
        plain_text = plain_text.strip()
        
        return plain_text
    
    def _detect_content_type(self, original_content: str, cleaned_content: str) -> ContentType:
        """Detect the type of content."""
        content_lower = original_content.lower()
        
        # Check for Evernote clippings first
        if any(indicator in content_lower for indicator in self.evernote_indicators):
            return ContentType.EVERNOTE_CLIPPING
        
        # Check for templates
        if any(indicator in content_lower for indicator in self.template_indicators):
            return ContentType.TEMPLATE
        
        # Check for drafts
        if any(indicator in content_lower for indicator in self.draft_indicators):
            return ContentType.DRAFT
        
        # Check for technical reports
        has_technical = any(term in content_lower for term in self.technical_terms)
        has_numbers = bool(re.search(r'\d+', original_content))
        if has_technical and has_numbers:
            return ContentType.TECHNICAL_REPORT
        
        # Check for meeting notes
        has_dates = bool(re.search(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', original_content))
        has_proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', original_content)) > 5
        if has_dates and has_proper_nouns:
            return ContentType.MEETING_NOTES
        
        # Check for structured content
        has_lists = bool(re.search(r'^[\s]*[-*+]\s', original_content, re.MULTILINE))
        has_headers = bool(re.search(r'^#{1,6}\s', original_content, re.MULTILINE))
        if has_lists and has_headers:
            return ContentType.STRUCTURED_CONTENT
        
        return ContentType.GENERAL
    
    def _detect_language(self, content: str) -> Language:
        """Detect the language of the content."""
        # Basic language detection based on character patterns
        if re.search(r'[áéíóúñü]', content, re.IGNORECASE):
            return Language.SPANISH
        elif re.search(r'[àâäéèêëïîôöùûüÿç]', content, re.IGNORECASE):
            return Language.FRENCH
        elif re.search(r'[äöüß]', content, re.IGNORECASE):
            return Language.GERMAN
        else:
            return Language.ENGLISH
    
    def _calculate_quality_metrics(self, original_content: str, cleaned_content: str) -> Dict[str, Any]:
        """Calculate quality metrics for the content."""
        # Basic metrics
        word_count = len(cleaned_content.split())
        character_count = len(cleaned_content)
        
        # Structure analysis
        structure_score = self._calculate_structure_score(original_content, cleaned_content)
        
        # Content quality indicators
        has_meaningful_content = len(cleaned_content.strip()) > 50
        has_structure = bool(re.search(r'^#{1,6}\s', original_content, re.MULTILINE))
        has_lists = bool(re.search(r'^[\s]*[-*+]\s', original_content, re.MULTILINE))
        has_links = bool(re.search(r'\[([^\]]+)\]\(([^)]+)\)', original_content))
        
        # Word diversity
        words = re.findall(r'\b\w+\b', cleaned_content.lower())
        word_diversity = len(set(words)) / len(words) if words else 0.0
        
        # Average sentence length
        sentences = re.split(r'[.!?]+', cleaned_content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        avg_sentence_length = statistics.mean(sentence_lengths) if sentence_lengths else 0.0
        
        # Overall quality score
        overall_score = self._calculate_overall_quality_score({
            'word_count': word_count,
            'character_count': character_count,
            'structure_score': structure_score,
            'has_meaningful_content': has_meaningful_content,
            'has_structure': has_structure,
            'has_lists': has_lists,
            'has_links': has_links,
            'word_diversity': word_diversity,
            'avg_sentence_length': avg_sentence_length
        })
        
        return {
            'word_count': word_count,
            'character_count': character_count,
            'structure_score': structure_score,
            'has_meaningful_content': has_meaningful_content,
            'has_structure': has_structure,
            'has_lists': has_lists,
            'has_links': has_links,
            'word_diversity': word_diversity,
            'avg_sentence_length': avg_sentence_length,
            'overall_score': overall_score
        }
    
    def _calculate_structure_score(self, original_content: str, cleaned_content: str) -> float:
        """Calculate a structure quality score."""
        score = 0.0
        
        # Base score from content length
        word_count = len(cleaned_content.split())
        if word_count > 100:
            score += 0.3
        elif word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1
        
        # Structure elements
        if re.search(r'^#{1,6}\s', original_content, re.MULTILINE):
            score += 0.2
        if re.search(r'^[\s]*[-*+]\s', original_content, re.MULTILINE):
            score += 0.1
        if re.search(r'\|.*\|', original_content, re.MULTILINE):
            score += 0.1
        if re.search(r'```[\s\S]*?```', original_content):
            score += 0.1
        
        # Content ratio (actual content vs metadata)
        if original_content.startswith('---'):
            frontmatter_end = original_content.find('---', 3)
            if frontmatter_end != -1:
                frontmatter = original_content[3:frontmatter_end]
                content_ratio = (len(original_content) - len(frontmatter)) / len(original_content)
                if content_ratio > 0.8:
                    score += 0.2
                elif content_ratio > 0.6:
                    score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overall_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score from metrics."""
        score = 0.0
        
        # Content length (30%)
        if metrics['word_count'] > 100:
            score += 0.3
        elif metrics['word_count'] > 50:
            score += 0.2
        elif metrics['word_count'] > 20:
            score += 0.1
        
        # Structure (25%)
        score += metrics['structure_score'] * 0.25
        
        # Meaningful content (20%)
        if metrics['has_meaningful_content']:
            score += 0.2
        
        # Word diversity (15%)
        score += min(metrics['word_diversity'], 1.0) * 0.15
        
        # Sentence structure (10%)
        if 5 <= metrics['avg_sentence_length'] <= 25:
            score += 0.1
        
        return min(score, 1.0)
    
    def _identify_issues(self, original_content: str, cleaned_content: str, metrics: Dict[str, Any]) -> List[str]:
        """Identify potential issues with the content."""
        issues = []
        
        # Content length issues
        if metrics['word_count'] < 10:
            issues.append('very_short_content')
        elif metrics['word_count'] < self.min_word_count:
            issues.append('short_content')
        
        if metrics['character_count'] < self.min_character_count:
            issues.append('insufficient_content')
        
        # Structure issues
        if metrics['structure_score'] < self.min_structure_score:
            issues.append('poor_structure')
        
        # Quality issues
        if not metrics['has_meaningful_content']:
            issues.append('no_meaningful_content')
        
        # Content type specific issues
        content_lower = original_content.lower()
        
        if any(indicator in content_lower for indicator in self.evernote_indicators):
            issues.append('evernote_clipping')
        
        if any(indicator in content_lower for indicator in self.template_indicators):
            issues.append('template_content')
        
        if any(indicator in content_lower for indicator in self.draft_indicators):
            issues.append('draft_content')
        
        # Structure issues
        attachment_count = len(re.findall(r'\[.*?\]\((.*?)\)', original_content))
        if attachment_count > 10:
            issues.append('many_attachments')
        
        link_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', original_content))
        if link_count > 20:
            issues.append('many_links')
        
        return issues
    
    def _should_process_note(self, content_type: ContentType, metrics: Dict[str, Any], issues: List[str]) -> Tuple[bool, str]:
        """Determine if the note should be processed further."""
        # Automatic rejection for certain content types
        if content_type in [ContentType.TEMPLATE, ContentType.DRAFT]:
            return False, f"Content type {content_type.value} automatically rejected"
        
        # Reject based on quality score
        if metrics['overall_score'] < self.min_quality_score:
            return False, f"Quality score {metrics['overall_score']:.2f} below threshold {self.min_quality_score}"
        
        # Reject based on content length
        if metrics['word_count'] < self.min_word_count:
            return False, f"Word count {metrics['word_count']} below minimum {self.min_word_count}"
        
        # Reject based on structure
        if metrics['structure_score'] < self.min_structure_score:
            return False, f"Structure score {metrics['structure_score']:.2f} below threshold {self.min_structure_score}"
        
        # Reject if no meaningful content
        if not metrics['has_meaningful_content']:
            return False, "No meaningful content detected"
        
        # Reject for critical issues
        critical_issues = ['very_short_content', 'no_meaningful_content']
        if any(issue in issues for issue in critical_issues):
            return False, f"Critical issues detected: {[i for i in issues if i in critical_issues]}"
        
        return True, "Content passed all quality checks"
    
    def _build_metadata(self, original_content: str, cleaned_content: str, content_type: ContentType, 
                       language: Language, metrics: Dict[str, Any], issues: List[str], 
                       evernote_result: EvernoteCleaningResult) -> Dict[str, Any]:
        """Build comprehensive metadata for the note."""
        metadata = {
            'content_type': content_type.value,
            'language': language.value,
            'quality_metrics': metrics,
            'issues': issues,
            'has_frontmatter': original_content.startswith('---'),
            'has_attachments': bool(re.search(r'\[.*?\]\((.*?)\)', original_content)),
            'has_links': bool(re.search(r'\[([^\]]+)\]\(([^)]+)\)', original_content)),
            'has_images': bool(re.search(r'!\[.*?\]\(.*?\)', original_content)),
            'has_code_blocks': bool(re.search(r'```[\s\S]*?```', original_content)),
            'has_tables': bool(re.search(r'\|.*\|', original_content, re.MULTILINE)),
            'has_lists': bool(re.search(r'^[\s]*[-*+]\s', original_content, re.MULTILINE)),
            'has_headers': bool(re.search(r'^#{1,6}\s', original_content, re.MULTILINE)),
            'technical_terms_found': [term for term in self.technical_terms if term in original_content.lower()],
            'preprocessing_timestamp': str(Path().stat().st_mtime) if Path().exists() else None
        }
        
        # Add Evernote cleaning metadata if applicable
        if evernote_result.is_evernote_clipping:
            metadata['evernote_cleaning'] = {
                'is_evernote_clipping': True,
                'extracted_title': evernote_result.extracted_title,
                'extracted_url': evernote_result.extracted_url,
                'extracted_tags': evernote_result.extracted_tags,
                'extracted_date': evernote_result.extracted_date,
                'cleaning_stats': evernote_result.cleaning_stats
            }
        else:
            metadata['evernote_cleaning'] = {
                'is_evernote_clipping': False
            }
        
        return metadata
    
    def _create_failed_result(self, content: str, error: str) -> PreprocessingResult:
        """Create a failed preprocessing result."""
        return PreprocessingResult(
            original_content=content,
            cleaned_content="",
            content_type=ContentType.GENERAL,
            language=Language.UNKNOWN,
            quality_score=0.0,
            word_count=0,
            character_count=0,
            structure_score=0.0,
            has_meaningful_content=False,
            issues=[f"preprocessing_error: {error}"],
            metadata={},
            should_process=False,
            processing_reason=f"Preprocessing failed: {error}"
        )
    
    def batch_preprocess(self, notes_data: List[Tuple[Path, str]]) -> List[PreprocessingResult]:
        """Preprocess multiple notes in batch."""
        results = []
        
        for file_path, content in notes_data:
            try:
                result = self.preprocess_note(content, file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error preprocessing {file_path}: {e}")
                results.append(self._create_failed_result(content, str(e)))
        
        return results
    
    def get_preprocessing_stats(self, results: List[PreprocessingResult]) -> Dict[str, Any]:
        """Get statistics from preprocessing results."""
        if not results:
            return {}
        
        total_notes = len(results)
        processed_notes = sum(1 for r in results if r.should_process)
        rejected_notes = total_notes - processed_notes
        
        # Content type distribution
        content_types = {}
        for result in results:
            content_type = result.content_type.value
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        # Language distribution
        languages = {}
        for result in results:
            language = result.language.value
            languages[language] = languages.get(language, 0) + 1
        
        # Issue distribution
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Quality score statistics
        quality_scores = [r.quality_score for r in results if r.quality_score > 0]
        word_counts = [r.word_count for r in results if r.word_count > 0]
        
        return {
            'total_notes': total_notes,
            'processed_notes': processed_notes,
            'rejected_notes': rejected_notes,
            'processing_rate': processed_notes / total_notes if total_notes > 0 else 0.0,
            'content_types': content_types,
            'languages': languages,
            'issues': issue_counts,
            'quality_scores': {
                'mean': statistics.mean(quality_scores) if quality_scores else 0.0,
                'median': statistics.median(quality_scores) if quality_scores else 0.0,
                'min': min(quality_scores) if quality_scores else 0.0,
                'max': max(quality_scores) if quality_scores else 0.0
            },
            'word_counts': {
                'mean': statistics.mean(word_counts) if word_counts else 0.0,
                'median': statistics.median(word_counts) if word_counts else 0.0,
                'min': min(word_counts) if word_counts else 0.0,
                'max': max(word_counts) if word_counts else 0.0
            }
        } 