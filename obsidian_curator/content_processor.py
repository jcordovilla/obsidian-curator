"""Content processing and cleaning for Obsidian notes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import markdown
from bs4 import BeautifulSoup
from loguru import logger

# Removed trafilatura dependencies - using optimized custom solution

from .models import Note, ContentType
from .content_extractor import ContentExtractor
from .ai_content_classifier import AIContentClassifier, ContentAnalysis
from .specialized_processors import SpecializedContentProcessor, ProcessingResult


class ContentProcessor:
    """Processes and cleans Obsidian note content."""
    
    def __init__(self, 
                 clean_html: bool = True, 
                 preserve_metadata: bool = True,
                 extract_linked_content: bool = True,
                 max_pdf_pages: int = 100,
                 intelligent_extraction: bool = True,
                 ai_model: str = None,
                 enable_ai_classification: bool = True):
        """Initialize the content processor.
        
        Args:
            clean_html: Whether to clean HTML content
            preserve_metadata: Whether to preserve original metadata
            extract_linked_content: Whether to extract content from linked PDFs, images, URLs
            max_pdf_pages: Maximum number of PDF pages to process
            intelligent_extraction: Use AI to filter and summarize extracted content
            ai_model: AI model to use for intelligent extraction
            enable_ai_classification: Whether to use AI for content classification
        """
        self.clean_html = clean_html
        self.preserve_metadata = preserve_metadata
        self.extract_linked_content = extract_linked_content
        self.enable_ai_classification = enable_ai_classification
        
        # Initialize AI content classifier if enabled
        if self.enable_ai_classification:
            self.ai_classifier = AIContentClassifier(
                model=ai_model or "phi3:mini",
                enable_ai=True,
                fallback_to_rules=True
            )
            self.specialized_processor = SpecializedContentProcessor()
            logger.info("AI content classification enabled")
        else:
            self.ai_classifier = None
            self.specialized_processor = None
            logger.info("AI content classification disabled")
        
        # Initialize content extractor if enabled
        if self.extract_linked_content:
            self.content_extractor = ContentExtractor(
                max_pdf_pages=max_pdf_pages,
                intelligent_extraction=intelligent_extraction,
                ai_model=ai_model
            )
        else:
            self.content_extractor = None
        
        # Common HTML elements to remove
        self.html_elements_to_remove = [
            'script', 'style', 'noscript', 'iframe', 'embed', 'object',
            'form', 'input', 'button', 'select', 'textarea'
        ]
        
        # Aggressive web clutter patterns
        patterns_path = Path(__file__).with_name('clutter_patterns.txt')
        if patterns_path.exists():
            pattern_strings = [
                line.strip()
                for line in patterns_path.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.strip().startswith('#')  # Skip comments and empty lines
            ]
            self.clutter_patterns = []
            for pat in pattern_strings:
                try:
                    self.clutter_patterns.append(re.compile(pat, re.IGNORECASE | re.DOTALL))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pat}': {e}")
        else:
            self.clutter_patterns = []
    
    def process_note(self, file_path: Path) -> Note:
        """Process a single note file and return a Note object.
        
        Args:
            file_path: Path to the note file
            
        Returns:
            Note object with processed content
        """
        logger.info(f"Processing note: {file_path}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning(f"Unicode decode error for {file_path}, trying different encoding")
            try:
                content = file_path.read_text(encoding='latin-1')
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                raise
        
        # Extract metadata and content
        metadata, clean_content = self._extract_metadata_and_content(content)
        
        # Apply sanitization if configured
        clean_content = self._sanitize_content(clean_content)
        
        # Use AI classification if enabled
        if self.enable_ai_classification and self.ai_classifier:
            try:
                # Classify content using AI
                content_analysis = self.ai_classifier.classify_content(
                    clean_content, metadata, file_path
                )
                
                # Process content using specialized processor
                processing_result = self.specialized_processor.process_content(
                    clean_content, content_analysis, metadata, file_path
                )
                
                # Use the processed content and type
                clean_content = processing_result.cleaned_content
                content_type = processing_result.content_type
                
                # Log processing results
                logger.info(f"AI classification: {content_analysis.category.value} "
                          f"(confidence: {content_analysis.confidence:.2f})")
                logger.info(f"Processing strategy: {content_analysis.processing_strategy}")
                logger.info(f"Quality score: {processing_result.quality_score:.2f}")
                
                # Add processing metadata
                if 'ai_analysis' not in metadata:
                    metadata['ai_analysis'] = {}
                metadata['ai_analysis'].update({
                    'category': content_analysis.category.value,
                    'confidence': content_analysis.confidence,
                    'processing_strategy': content_analysis.processing_strategy,
                    'quality_score': processing_result.quality_score,
                    'processing_notes': processing_result.processing_notes
                })
                
            except Exception as e:
                logger.warning(f"AI classification failed: {e}, falling back to rule-based")
                # Fall back to rule-based content type determination
                content_type = self._determine_content_type(metadata, clean_content)
                
                # For web content, check if cleaning resulted in meaningful content
                if content_type in [ContentType.WEB_CLIPPING] and clean_content:
                    clean_content = self._validate_web_content_quality(clean_content, file_path)
        else:
            # Use traditional rule-based approach
            content_type = self._determine_content_type(metadata, clean_content)
            
            # For web content, check if cleaning resulted in meaningful content
            if content_type in [ContentType.WEB_CLIPPING] and clean_content:
                clean_content = self._validate_web_content_quality(clean_content, file_path)
        
        # Clean content if needed - apply HTML cleaning only to actual HTML content
        # For web clippings that are already in Markdown format, use text-based cleaning
        if self.clean_html and content_type in [ContentType.WEB_CLIPPING, ContentType.IMAGE_ANNOTATION, ContentType.PDF_ANNOTATION]:
            # Check if content is actually HTML or already Markdown
            html_indicators = ['<div', '<span', '<table', '<tr', '<td', '<p>', '<ul', '<ol', '<li', '<html', '<body']
            is_html = any(indicator in clean_content for indicator in html_indicators)
            
            if is_html:
                clean_content = self._clean_html_content(clean_content)
            else:
                # It's a Markdown web clipping - use gentler text-based cleaning
                clean_content = self._clean_markdown_web_content(clean_content)
        # URL references don't need HTML cleaning as they're typically simple bookmarks
        
        # Extract linked content if enabled
        if self.extract_linked_content and self.content_extractor:
            vault_root = file_path.parent
            # Find vault root by looking for .obsidian folder or going up to reasonable limit
            current_path = file_path.parent
            max_depth = 10
            depth = 0
            
            while depth < max_depth and current_path.parent != current_path:
                if (current_path / '.obsidian').exists():
                    vault_root = current_path
                    break
                current_path = current_path.parent
                depth += 1
            
            try:
                clean_content = self.content_extractor.enhance_note_content(clean_content, vault_root)
            except Exception as e:
                logger.warning(f"Failed to extract linked content: {e}")
                # Continue with original content if extraction fails
        
        # Extract title
        title = self._extract_title(metadata, clean_content, file_path)
        
        # Extract dates
        created_date, modified_date = self._extract_dates(metadata, file_path)
        
        # Extract tags
        tags = self._extract_tags(metadata, clean_content)
        
        # Extract source URL
        source_url = self._extract_source_url(metadata, clean_content)
        
        # Semantic content validation
        if not self._has_meaningful_content(clean_content, content_type):
            logger.warning(f"Note '{file_path.name}' lacks meaningful content")
        
        return Note(
            file_path=file_path,
            title=title,
            content=clean_content,
            content_type=content_type,
            metadata=metadata if self.preserve_metadata else {},
            created_date=created_date,
            modified_date=modified_date,
            tags=tags,
            source_url=source_url
        )
    
    def _extract_metadata_and_content(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter metadata and content.
        
        Args:
            content: Raw note content
            
        Returns:
            Tuple of (metadata_dict, clean_content)
        """
        metadata = {}
        clean_content = content
        
        # Check for YAML frontmatter
        if content.startswith('---'):
            try:
                # Find end of frontmatter
                end_index = content.find('---', 3)
                if end_index != -1:
                    frontmatter = content[3:end_index].strip()
                    clean_content = content[end_index + 3:].strip()
                    
                    # Parse YAML-like frontmatter (simplified)
                    for line in frontmatter.split('\n'):
                        line = line.strip()
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            
                            metadata[key] = value
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")
        
        return metadata, clean_content
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by removing problematic Unicode and normalizing.
        
        Args:
            content: Content to sanitize
            
        Returns:
            Sanitized content
        """
        if not content:
            return content
        
        import unicodedata
        
        # Unicode normalization
        try:
            content = unicodedata.normalize('NFKC', content)
        except Exception as e:
            logger.warning(f"Unicode normalization failed: {e}")
        
        # Remove problematic Unicode characters
        unicode_replacements = {
            'NBSP': '\u00A0',           # Non-breaking space
            'SOFT_HYPHEN': '\u00AD',    # Soft hyphen
            'ZWSP': '\u200B',           # Zero-width space
            'ZWNJ': '\u200C',           # Zero-width non-joiner
            'ZWJ': '\u200D',            # Zero-width joiner
            'LRM': '\u200E',            # Left-to-right mark
            'RLM': '\u200F',            # Right-to-left mark
        }
        
        for char_name, char_code in unicode_replacements.items():
            content = content.replace(char_code, ' ')
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Remove common boilerplate patterns if file exists
        try:
            patterns_path = Path(__file__).with_name('clutter_patterns.txt')
            if patterns_path.exists():
                pattern_lines = patterns_path.read_text(encoding='utf-8').splitlines()
                for pattern_line in pattern_lines:
                    pattern_line = pattern_line.strip()
                    if pattern_line and not pattern_line.startswith('#'):
                        try:
                            content = re.sub(pattern_line, '', content, flags=re.IGNORECASE | re.MULTILINE)
                        except re.error:
                            continue
        except Exception as e:
            logger.warning(f"Failed to apply boilerplate patterns: {e}")
        
        return content
    
    def _validate_web_content_quality(self, content: str, file_path: Path) -> str:
        """Validate that web content is meaningful after cleaning.
        
        Args:
            content: Cleaned web content
            file_path: Path to the original file
            
        Returns:
            Validated content or empty string if content is poor quality
        """
        if not content or len(content.strip()) < 100:
            logger.warning(f"Web content too short after cleaning: {file_path}")
            return ""
        
        # Check for patterns that indicate mostly navigation/metadata
        navigation_indicators = [
            # Multiple empty parentheses or formatting artifacts
            r'\(\)\s*\(\)\s*\(\)',
            # Table formatting artifacts
            r'\|\s*\|\s*\|\s*\|',
            r':---:\s*\|\s*:---:',
            # Contact/administrative info
            r'mailto:.*@.*\.',
            r'Publisher:\s*\(\)',
            r'Editor-in-Chief:',
            r'Managing Director:',
            # Navigation artifacts
            r'regions\s*\|\s*$',
            r'careers.*objId.*type=article'
        ]
        
        # Count navigation artifacts
        navigation_count = sum(1 for pattern in navigation_indicators 
                             if re.search(pattern, content, re.IGNORECASE))
        
        # Count meaningful words (excluding common web artifacts)
        words = content.split()
        meaningful_words = [word for word in words 
                          if len(word) > 3 
                          and word not in ['()', '|', ':---:', 'mailto:', 'objId']]
        
        # Calculate quality metrics
        navigation_ratio = navigation_count / max(1, len(words) // 20)  # Per 20 words
        meaningful_word_ratio = len(meaningful_words) / max(1, len(words))
        
        # Reject if content is mostly navigation/artifacts
        if navigation_ratio > 0.3:  # More than 30% navigation artifacts
            logger.warning(f"High navigation ratio ({navigation_ratio:.2f}) in web content: {file_path}")
            return ""
        
        if meaningful_word_ratio < 0.5:  # Less than 50% meaningful words
            logger.warning(f"Low meaningful word ratio ({meaningful_word_ratio:.2f}) in web content: {file_path}")
            return ""
        
        # Check for repeated patterns that indicate failed extraction
        lines = content.split('\n')
        empty_lines = len([line for line in lines if not line.strip()])
        if len(lines) > 10 and empty_lines / len(lines) > 0.7:  # More than 70% empty lines
            logger.warning(f"Too many empty lines ({empty_lines}/{len(lines)}) in web content: {file_path}")
            return ""
        
        # Content passes quality checks
        logger.debug(f"Web content quality validated: {file_path} ({len(meaningful_words)} meaningful words)")
        return content
    
    def _determine_content_type(self, metadata: Dict[str, Any], content: str) -> ContentType:
        """Determine the type of content based on metadata and content.
        
        Args:
            metadata: Note metadata
            content: Note content
            
        Returns:
            ContentType enum value
        """
        # Check for PDF annotations first (highest priority for specific content)
        if self._contains_pdf_references(content):
            return ContentType.PDF_ANNOTATION
        
        # Check for web clippings first (before audio/image since web clippings often contain them)
        if self._contains_urls(content):
            # First check if it's a substantial web clipping
            if self._is_web_clipping(content):
                # Then check if it's a professional publication based on source
                if metadata.get('source') and 'linkedin.com' in str(metadata.get('source', '')):
                    return ContentType.PROFESSIONAL_PUBLICATION
                return ContentType.WEB_CLIPPING
            
            # If it contains URLs but isn't a web clipping, determine if it's a URL reference
            # vs personal note that happens to contain URLs
            if self._is_primarily_url_reference(content):
                return ContentType.URL_REFERENCE
            # If URLs are just incidental to substantial personal content, it's a personal note
        
        # Check for audio annotations  
        if self._contains_audio_references(content):
            return ContentType.AUDIO_ANNOTATION
        
        # Check for image annotations
        if self._contains_image_references(content):
            return ContentType.IMAGE_ANNOTATION
        
        # Check for academic content
        if self._is_academic_content(content):
            return ContentType.ACADEMIC_PAPER
        
        # Default to personal note
        return ContentType.PERSONAL_NOTE
    
    def _contains_pdf_references(self, content: str) -> bool:
        """Check if content contains PDF references."""
        pdf_patterns = [
            r'\.pdf',
            r'PDF',
            r'pdf',
            r'\[\[.*\.pdf\]\]',  # Obsidian PDF links
            r'!\[\[.*\.pdf\]\]'  # Obsidian PDF embeds
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in pdf_patterns)
    
    def _contains_audio_references(self, content: str) -> bool:
        """Check if content contains audio/media references."""
        audio_patterns = [
            r'!\[\[.*\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\]\]',  # Obsidian audio embeds
            r'!\[.*\]\(.*\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\)',  # Markdown audio links
            r'<audio[^>]*>',  # HTML audio tags
            r'<video[^>]*>',  # HTML video tags
            r'\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)',  # Audio file extensions
            r'!\[\[attachments/[^/]*\.resources/.*\]\]',  # Obsidian generic resource references (often audio)
            r'\d{1,2}\s+(ago|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\.\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}',  # Timestamp patterns
        ]
        
        # Also check if content is minimal and mainly contains attachment references
        lines = content.strip().split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # If most content is just attachment references, likely audio
        attachment_lines = sum(1 for line in non_empty_lines if '![[attachments/' in line)
        if len(non_empty_lines) <= 3 and attachment_lines > 0:
            return True
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in audio_patterns)
    
    def _contains_image_references(self, content: str) -> bool:
        """Check if content contains image references."""
        image_patterns = [
            r'\.(png|jpg|jpeg|gif|svg|webp)',
            r'!\[\[.*\.(png|jpg|jpeg|gif|svg|webp)\]\]',  # Obsidian image embeds
            r'<img[^>]*>',  # HTML image tags
            r'image',
            r'Image'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in image_patterns)
    
    def _contains_urls(self, content: str) -> bool:
        """Check if content contains URLs."""
        url_patterns = [
            r'https?://',  # Fixed: was http[s]
            r'<https?://',  # Markdown/HTML wrapped URLs
            r'www\.',
            r'linkedin\.com',
            r'twitter\.com',
            r'facebook\.com'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in url_patterns)
    
    def _is_primarily_url_reference(self, content: str) -> bool:
        """Check if content is primarily a URL reference/bookmark vs personal content with URLs.
        
        A URL reference is characterized by:
        - Minimal descriptive text (usually just a title and URL)
        - URLs are the primary content, not incidental
        - Little personal commentary or analysis
        """
        # Remove frontmatter and clean content for analysis
        clean_text = re.sub(r'---.*?---', '', content, flags=re.DOTALL)
        clean_text = re.sub(r'#+ ', '', clean_text)  # Remove headers
        clean_text = clean_text.strip()
        
        # Count URLs vs total content  
        urls = re.findall(r'<?(https?://[^\s<>"{}|\\^`\[\]]+)>?', clean_text)
        url_chars = sum(len(url) for url in urls)
        
        # Remove URLs to see remaining content
        text_without_urls = re.sub(r'<?(https?://[^\s<>"{}|\\^`\[\]]+)>?', '', clean_text)
        text_without_urls = re.sub(r'<[^>]+>', '', text_without_urls)  # Remove any HTML
        text_without_urls = re.sub(r'\*\*.*?\*\*', '', text_without_urls)  # Remove bold text
        text_without_urls = re.sub(r'\s+', ' ', text_without_urls).strip()
        
        non_url_words = len(text_without_urls.split()) if text_without_urls else 0
        total_chars = len(clean_text)
        total_words = len(clean_text.split())
        
        # It's primarily a URL reference if:
        # 1. Very short content (quick reference style)
        # 2. URLs are prominent compared to text
        # 3. Limited descriptive content
        
        is_very_short = total_chars < 200  # Increased threshold
        is_minimal_words = total_words < 25  # Simple word count check
        is_minimal_non_url_content = non_url_words < 20  # Focus on substantial content
        
        # A URL reference typically has:
        # - Short content OR
        # - Minimal words OR 
        # - Very little non-URL content (indicating it's mainly for the links)
        
        return is_very_short or is_minimal_words or is_minimal_non_url_content
    
    def _is_web_clipping(self, content: str) -> bool:
        """Check if content is a web clipping (vs a simple URL reference).
        
        A web clipping should have substantial HTML content or clear signs of web scraping.
        This is different from a simple URL reference or bookmark.
        """
        # Strong indicators of web clipping (HTML structure)
        html_indicators = [
            r'<html',
            r'<div[^>]*>.*</div>',  # Actual div content, not just isolated tags
            r'<span[^>]*>.*</span>',  # Actual span content
            r'<p[^>]*>.*</p>',  # Actual paragraph content
            r'<article[^>]*>',
            r'<section[^>]*>',
            r'<header[^>]*>',
            r'<main[^>]*>',
        ]
        
        # Count HTML tags - if there are many, it's likely a web clipping
        html_tag_count = len(re.findall(r'<[^>]+>', content))
        
        # Count total content words (excluding HTML)
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        word_count = len(clean_text.split())
        
        # Web clipping indicators:
        # 1. Has substantial HTML structure (multiple tags)
        # 2. Has substantial text content (not just a URL + short description)
        # 3. Contains specific HTML elements that indicate scraped content
        
        has_html_structure = any(re.search(pattern, content, re.IGNORECASE | re.DOTALL) 
                               for pattern in html_indicators)
        has_many_html_tags = html_tag_count > 5
        has_substantial_content = word_count > 50
        
        # Additional indicators of web scraping
        web_scraping_indicators = [
            r'Published by',
            r'By\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # "By Author Name"
            r'Copyright\s+©',
            r'© \d{4}',
            r'AddThis Sharing',
            r'Share on',
            r'Follow us on',
            r'Subscribe to',
            r'Read more',
            r'Continue reading',
            r'View original',
        ]
        
        has_web_metadata = any(re.search(pattern, content, re.IGNORECASE) 
                              for pattern in web_scraping_indicators)
        
        # It's a web clipping if:
        # - Has HTML structure AND substantial content, OR
        # - Has many HTML tags, OR  
        # - Has clear web scraping metadata, OR
        # - Has moderate content with some HTML indicators
        has_moderate_content = word_count > 25 and html_tag_count > 2
        
        return ((has_html_structure and has_substantial_content) or 
                has_many_html_tags or 
                has_web_metadata or
                has_moderate_content)
    
    def _is_academic_content(self, content: str) -> bool:
        """Check if content is academic in nature."""
        academic_patterns = [
            r'academic',
            r'research',
            r'study',
            r'paper',
            r'journal',
            r'conference',
            r'proceedings',
            r'abstract',
            r'methodology',
            r'literature review'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in academic_patterns)
    
    def _clean_html_content(self, content: str) -> str:
        """Clean HTML content and convert to clean markdown.
        
        Args:
            content: HTML content to clean
            
        Returns:
            Cleaned markdown content
        """
        if not content.strip():
            return content
        
        # Remove HTML comments and clutter
        for pattern in self.clutter_patterns:
            content = pattern.sub('', content)
        
        # Check if content is primarily HTML or Markdown
        html_indicators = ['<div', '<span', '<table', '<tr', '<td', '<p>', '<ul', '<ol', '<li']
        is_html = any(indicator in content for indicator in html_indicators)
        
        if is_html:
            # Parse HTML with BeautifulSoup
            try:
                soup = BeautifulSoup(content, 'html.parser')
            except Exception as e:
                logger.warning(f"Failed to parse HTML with BeautifulSoup: {e}")
                # Fallback: basic HTML tag removal
                return self._basic_html_cleanup(content)
            
            # Remove unwanted elements
            for element in soup.find_all(self.html_elements_to_remove):
                element.decompose()
            
            # Clean up common web elements
            self._clean_web_elements(soup)
            
            # Try to extract main article content
            main_content = self._extract_main_content(soup)
            
            # Convert to markdown
            try:
                # Use the main content if found, otherwise full soup
                content_to_convert = main_content if main_content else soup
                cleaned_content = self._html_to_markdown(content_to_convert)
            except Exception as e:
                logger.warning(f"Failed to convert HTML to markdown: {e}")
                content_to_convert = main_content if main_content else soup
                cleaned_content = content_to_convert.get_text(separator='\n', strip=True)
        else:
            # Content is already Markdown - apply comprehensive text cleanup
            cleaned_content = self._clean_markdown_web_content(content)
        
        # Final cleanup of remaining clutter
        cleaned_content = self._final_text_cleanup(cleaned_content)
        
        return cleaned_content
    
    def _clean_markdown_web_content(self, content: str) -> str:
        """Clean web clutter from markdown content while preserving article content."""
        lines = content.split('\n')
        cleaned_lines = []
        
        # More aggressive patterns for lines to completely remove
        skip_line_patterns = [
            # Navigation and structural elements
            r'^Subjects \|.*',  # Subject line with tags
            r'^\d{1,2} \w+ \d{4} \|.*',  # Date line with source
            r'^\[Share on .*?\].*',  # Share buttons
            r'^Share on \w+.*',  # Share links
            r'^\[Back to .*?\].*',  # Back navigation
            r'^Back to .*',  # Back navigation
            r'^Please \[sign in\].*',  # Login prompts
            r'^Please sign in.*',  # Login prompts
            r'^More Sharing Services.*',  # Sharing services
            r'^\[.*?\]\(http.*addthis.*\).*',  # AddThis sharing links
            r'^<http.*>$',  # Standalone URLs in angle brackets
            r'^## Share This Column$',  # Share section headers
            r'^## Discuss$',  # Discussion section headers
            r'^\s*\.\s*$',  # Lines with just a period
            r'^\*\*\s*$',  # Empty bold markers
            r'^•\*\*\s*$',  # Bullet with empty bold
            
            # Website navigation and menus - general patterns
            r'^Secciones$',  # Section headers
            r'^\s*\|\s*\|\s*\|\s*\|\s*\|.*',  # Malformed table rows
            r'^\s*:---:\s*\|\s*:---:\s*\|.*',  # Table separator rows
            r'^\s*\|\s*$',  # Empty table cells
            r'^\s*\(\)\s*\(\)\s*\(\).*',  # Empty parentheses patterns
            r'^\s*\*\s*Other\s*Sections\s*\(\).*',  # Navigation sections
            r'^\s*regions\s*\|\s*$',  # Region navigation
            r'.*careers.*rt=1.*objId.*',  # Career links with tracking
            r'.*mailto:.*@.*\.com.*',  # Email links patterns
            r'^\s*Publisher:\s*\(\)\s*$',  # Empty publisher info
            r'^\s*Editor-in-Chief:\s*\(mailto:.*',  # Editor contact info
            r'^\s*Managing Director:\s*\(mailto:.*',  # Director contact info
            r'^\s*Online news editor:\s*\(mailto:.*',  # Editor contact info
            r'^Casa Real.*',  # Royal family section
            r'^Madrid.*',  # Madrid section
            r'^Sevilla.*',  # Sevilla section
            r'^Aragón.*',  # Aragon section
            r'^Canarias.*',  # Canary Islands section
            r'^Castilla y León.*',  # Castile and Leon section
            r'^Cataluña.*',  # Catalonia section
            r'^C\. Valenciana.*',  # Valencia section
            r'^Galicia.*',  # Galicia section
            r'^Navarra.*',  # Navarre section
            r'^País Vasco.*',  # Basque Country section
            r'^Toledo.*',  # Toledo section
            r'^Internacional.*',  # International section
            r'^Declaración Renta.*',  # Tax declaration section
            r'^Inmobiliario.*',  # Real estate section
            r'^Blogs.*',  # Blogs section
            r'^Fe De Ratas.*',  # Fe de Ratas section
            r'^El Astrolabio.*',  # El Astrolabio section
            r'^El Sacapuntas.*',  # El Sacapuntas section
            r'^Real Madrid.*',  # Real Madrid section
            r'^Atlético de Madrid.*',  # Atletico Madrid section
            r'^Fútbol.*',  # Football section
            r'^Baloncesto.*',  # Basketball section
            r'^Tenis.*',  # Tennis section
            r'^Fórmula 1.*',  # Formula 1 section
            r'^Motos.*',  # Motorcycles section
            r'^Náutica.*',  # Sailing section
            r'^Ciclismo.*',  # Cycling section
            r'^Torneo ACBNext.*',  # ACB Next tournament section
            r'^Ciencia.*',  # Science section
            r'^Salud.*',  # Health section
            
            # Social media and sharing
            r'^Síguenos en$',  # Follow us
            r'^_ABC\.es_$',  # ABC.es header
            
            # Corporate website patterns
            r'^This website uses cookies.*',  # Cookie notices
            r'^By navigating around this site.*',  # Cookie consent
            r'^Select your region$',  # Region selection
            r'^By Business Objective$',  # Business objective headers
            r'^Contact us today.*',  # Contact prompts
            r'^Contact Sales$',  # Sales contact
            r'^A member of our sales team.*',  # Sales team info
            r'^Live Chat with Sales.*',  # Live chat
            r'^View Our Products and Services$',  # Product section headers
            r'^Download Resources$',  # Download section headers
            r'^Copyright ©.*$',  # Copyright notices
            r'^All rights reserved$',  # Rights reserved
            r'^\d+\.\d+ KB\)$',  # File size indicators
            r'^\d+\.\d+ MB\)$',  # File size indicators
            r'^PIANOS.*$',  # Product names
            r'^Self Assessment Checklist$',  # Product features
            r'^Internal Network Reconnaissance Infographic$',  # Product features
            r'^Report$',  # Generic report references
            r'^Identifíquese$',  # Identify yourself
            r'^Acceda a \*\*ClubABC\*\*.*',  # Access ClubABC
            r'^Entre$',  # Enter
            r'^¿Ha olvidado su contraseña\?$',  # Forgot password
            r'^Regístrese$',  # Register
            r'^Únase a \*\*ClubABC\*\*.*',  # Join ClubABC
            r'^Regístrese ahora$',  # Register now
            
            # News and content sections
            r'^Es Noticia$',  # It's News
            r'^Castor.*',  # Castor news
            r'^Presupuestos Generales.*',  # General Budget news
            r'^Elecciones Francia.*',  # French elections news
            r'^Cita Previa Declaración Renta.*',  # Tax appointment news
            r'^Regalos Día de la Madre.*',  # Mother's Day gifts news
            r'^Venezuela.*',  # Venezuela news
            r'^La Casa de Papel.*',  # Money Heist news
            r'^YouTube.*',  # YouTube news
            r'^Brexit.*',  # Brexit news
            
            # Generic web elements
            r'^\[.*?\]\(http.*\)$',  # Any markdown link that's just a link
            r'^http[s]?://.*$',  # Standalone URLs
            r'^www\..*$',  # Standalone www URLs
            r'^[A-Z][a-z]+ \d{4}$',  # Date patterns like "May 2017"
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # Date patterns like "4/5/2017"
            
            # Corporate website patterns
            r'^This website uses cookies.*',  # Cookie notices
            r'^By navigating around this site.*',  # Cookie consent
            r'^Select your region$',  # Region selection
            r'^By Business Objective$',  # Business objective headers
            r'^Contact us today.*',  # Contact prompts
            r'^Contact Sales$',  # Sales contact
            r'^A member of our sales team.*',  # Sales team info
            r'^Live Chat with Sales.*',  # Live chat
            r'^View Our Products and Services$',  # Product section headers
            r'^Download Resources$',  # Download section headers
            r'^Copyright ©.*$',  # Copyright notices
            r'^All rights reserved$',  # Rights reserved
            r'^\d+\.\d+ KB\)$',  # File size indicators
            r'^\d+\.\d+ MB\)$',  # File size indicators
            r'^PIANOS.*$',  # Product names (specific to this case)
            r'^Self Assessment Checklist$',  # Product features
            r'^Internal Network Reconnaissance Infographic$',  # Product features
            r'^Report$',  # Generic report references
        ]
        
        # Process each line
        for line in lines:
            # Skip truly empty lines
            if not line.strip():
                cleaned_lines.append('')  # Preserve paragraph breaks
                continue
                
            # Check if this line should be completely removed
            should_skip = False
            for pattern in skip_line_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # Clean the line more aggressively
            cleaned_line = line
            
            # Remove problematic elements
            cleaned_line = re.sub(r'\[Share on .*?\].*?', '', cleaned_line)
            cleaned_line = re.sub(r'\[.*?\]\(http.*addthis.*\)', '', cleaned_line)
            cleaned_line = re.sub(r'<http[^>]*>', '', cleaned_line)
            cleaned_line = re.sub(r'http[s]?://www\.addthis\.com[^\s\)]*', '', cleaned_line)
            
            # Remove more web clutter
            cleaned_line = re.sub(r'\[.*?\]\(http.*\)', '', cleaned_line)  # Remove all markdown links
            cleaned_line = re.sub(r'http[s]?://[^\s\)]+', '', cleaned_line)  # Remove all URLs
            cleaned_line = re.sub(r'www\.[^\s\)]+', '', cleaned_line)  # Remove www URLs
            
            # Only keep lines with substantial content (not just navigation)
            if len(cleaned_line.strip()) > 10:  # Lines must have at least 10 characters of actual content
                cleaned_lines.append(cleaned_line)
        
        # Join the cleaned lines
        result = '\n'.join(cleaned_lines)
        
        # Remove excessive blank lines but preserve some structure
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
        
        # Final cleanup - remove lines that are just punctuation or very short
        final_lines = []
        for line in result.split('\n'):
            if len(line.strip()) > 5 or not line.strip():  # Keep lines with >5 chars or empty lines
                final_lines.append(line)
        
        return '\n'.join(final_lines)
    
    def _clean_web_elements(self, soup: BeautifulSoup) -> None:
        """Clean up common web elements that add clutter.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove navigation and structural elements
        for nav in soup.find_all(['nav', 'header', 'footer', 'aside', 'section']):
            nav.decompose()
        
        # Remove common web clutter by class (partial matches)
        clutter_classes = [
            'advertisement', 'ad', 'banner', 'sidebar', 'navigation', 'nav',
            'menu', 'footer', 'header', 'social', 'share', 'comment',
            'related', 'recommended', 'popular', 'trending', 'widget',
            'toolbar', 'breadcrumb', 'pagination', 'pager', 'metadata',
            'tags', 'category', 'byline', 'author', 'date', 'timestamp',
            'copyright', 'legal', 'disclaimer', 'terms', 'privacy',
            'subscribe', 'newsletter', 'signup', 'login', 'search',
            # LinkedIn specific classes
            'linkedin', 'profile', 'connections', 'network', 'inbox',
            'notifications', 'account', 'settings', 'talent', 'sales'
        ]
        
        # Find elements with classes containing clutter keywords
        for element in soup.find_all(True):
            if element.get('class'):
                class_str = ' '.join(element.get('class')).lower()
                if any(clutter in class_str for clutter in clutter_classes):
                    element.decompose()
                    continue
            
            # Also check IDs
            if element.get('id'):
                id_str = element.get('id').lower()
                if any(clutter in id_str for clutter in clutter_classes):
                    element.decompose()
        
        # Remove LinkedIn-specific navigation text patterns
        linkedin_patterns = [
            r'skip to main content',
            r'find people, jobs, companies',
            r'grow my network',
            r'pending invitations',
            r'people you may know',
            r'add contacts',
            r'account & settings',
            r'sign out',
            r'upgrade.*account',
            r'job posting manage',
            r'company page manage',
            r'privacy.*settings',
            r'help center',
            r'get help',
            r'edit profile',
            r'who.*viewed.*profile',
            r'your updates',
            r'connections',
            r'find alumni',
            r'learning',
            r'talent solutions',
            r'sales solutions',
            r'try premium',
            r'user agreement',
            r'privacy policy',
            r'ad choices',
            r'community guidelines',
            r'cookie policy',
            r'discover more stories',
            r'don.*miss more posts',
            r'sign in to like',
            r'sign in to reply'
        ]
        
        # Remove elements containing LinkedIn navigation patterns
        import re
        for pattern in linkedin_patterns:
            for element in soup.find_all(string=re.compile(pattern, re.IGNORECASE)):
                if element.parent:
                    element.parent.decompose()
        
        # Remove tables that look like navigation/layout (not content)
        for table in soup.find_all('table'):
            # If table has very little text content, it's likely layout
            text_content = table.get_text().strip()
            if len(text_content) < 100 or not any(char.isalpha() for char in text_content):
                table.decompose()
        
        # Remove divs with only links (likely navigation)
        for div in soup.find_all('div'):
            links = div.find_all('a')
            text_content = div.get_text().strip()
            # If div is mostly links with little text, remove it
            if len(links) > 2 and len(text_content) < 200:
                div.decompose()
        
        # Remove lists that are likely navigation menus
        for ul in soup.find_all(['ul', 'ol']):
            items = ul.find_all('li')
            # If most list items contain only links, it's likely navigation
            if len(items) > 3:
                link_items = sum(1 for li in items if li.find('a') and len(li.get_text().strip()) < 50)
                if link_items / len(items) > 0.7:
                    ul.decompose()
    
    def _html_to_markdown(self, soup: BeautifulSoup) -> str:
        """Convert HTML to clean markdown with intelligent content extraction.
        
        Args:
            soup: BeautifulSoup object to convert
            
        Returns:
            Clean markdown content
        """
        # Remove all script, style, and tracking elements
        for element in soup.find_all(['script', 'style', 'noscript', 'iframe', 'embed', 'object']):
            element.decompose()
        
        # Remove tracking and analytics elements
        tracking_patterns = [
            'google-analytics', 'gtag', 'ga(', 'tracking', 'pixel',
            'smartadserver', 'click', 'analytics', 'track'
        ]
        
        for element in soup.find_all(True):
            # Check attributes for tracking patterns
            for attr in ['id', 'class', 'src', 'href']:
                if element.get(attr):
                    attr_value = str(element.get(attr)).lower()
                    if any(pattern in attr_value for pattern in tracking_patterns):
                        element.decompose()
                        break
            
            # Remove elements with suspicious content
            if element.get_text():
                text = element.get_text().lower()
                if any(pattern in text for pattern in ['tracking', 'analytics', 'pixel', 'smartadserver']):
                    element.decompose()
        
        # Extract main content area
        main_content = self._extract_main_content(soup)
        if main_content:
            content_to_convert = main_content
        else:
            # Fallback: use body content but clean it aggressively
            content_to_convert = soup.find('body') or soup
        
        # Convert to markdown with proper structure
        markdown_content = []
        
        # Process headings
        for heading in content_to_convert.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            text = heading.get_text().strip()
            if text and len(text) > 3:  # Only add meaningful headings
                markdown_content.append(f"{'#' * level} {text}")
                markdown_content.append("")
        
        # Process paragraphs
        for p in content_to_convert.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 20:  # Only add substantial paragraphs
                # Clean up the text
                text = self._clean_text_content(text)
                if text:
                    markdown_content.append(text)
                    markdown_content.append("")
        
        # Process lists
        for ul in content_to_convert.find_all(['ul', 'ol']):
            list_items = ul.find_all('li')
            if len(list_items) > 0:
                for li in list_items:
                    text = li.get_text().strip()
                    if text and len(text) > 5:
                        text = self._clean_text_content(text)
                        if text:
                            markdown_content.append(f"- {text}")
                markdown_content.append("")
        
        # Process blockquotes
        for blockquote in content_to_convert.find_all('blockquote'):
            text = blockquote.get_text().strip()
            if text and len(text) > 20:
                text = self._clean_text_content(text)
                if text:
                    markdown_content.append(f"> {text}")
                    markdown_content.append("")
        
        # Join and clean up
        result = "\n".join(markdown_content)
        
        # Final cleanup
        result = self._final_text_cleanup(result)
        
        return result
    
    def _clean_text_content(self, text: str) -> str:
        """Clean individual text content by removing clutter and normalizing.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove LinkedIn-specific navigation text
        linkedin_clutter = [
            r'Skip to main content',
            r'Find People, Jobs, Companies, and More',
            r'All\s*People\s*Jobs\s*Companies\s*Groups\s*Universities\s*Posts',
            r'Inbox.*messages',
            r'Notifications.*unseen notifications',
            r'Grow My Network',
            r'See all.*invitations',
            r'People You May Know',
            r'Add contacts',
            r'Gmail\s*Yahoo\s*Hotmail\s*Other',
            r'Account & Settings',
            r'Sign Out',
            r'Job Posting Manage',
            r'Company Page Manage',
            r'Language Change',
            r'Privacy & Settings Manage',
            r'Help Center.*Get Help',
            r'Home.*Edit Profile.*Connections',
            r'Who.*s Viewed Your Profile',
            r'Your Updates',
            r'Find Alumni',
            r'Learning.*Jobs.*Companies.*Groups',
            r'Post a Job',
            r'Talent Solutions',
            r'Advertise',
            r'Sales Solutions',
            r'Learning Solutions',
            r'Try Premium for free',
            r'Publish a post',
            r'Don.*t Miss More Posts',
            r'Discover more stories',
            r'Sign in to like this comment',
            r'Sign in to reply to this comment',
            r'Report this',
            r'Help Center.*Press.*Blog.*Developers.*Careers',
            r'Advertising.*Talent Solutions.*Sales Solutions',
            r'Small Business.*Mobile.*Language',
            r'Upgrade Your Account',
            r'User Agreement.*Privacy Policy.*Ad Choices',
            r'Community Guidelines.*Cookie Policy'
        ]
        
        for pattern in linkedin_clutter:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove common web clutter patterns (enhanced)
        clutter_patterns = [
            r'\[Share on .*?\].*?',  # Social media sharing buttons
            r'Share on \w+.*?',  # Share buttons
            r'\[Back to .*?\].*?',  # Navigation links
            r'Please \[sign in\].*?comment.*?',  # Comment prompts
            r'Subjects \|.*?',  # Subject tags/categories
            r'\d{1,2} \w+ \d{4} \|.*?',  # Date stamps with sources
            r'More Sharing Services.*?',  # Sharing service prompts
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # Remove URLs
            r'www\.[^\s]+',  # Remove www URLs
            r'photo:.*',  # Remove photo captions
            r'Published on.*\d{4}',  # Remove publication dates
            r'\[.*?\]\(http[^\)]*\)',  # Remove markdown-style links
            r'<http[^>]*>',  # Remove angle-bracket URLs
        ]
        
        for pattern in clutter_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up remaining whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Only return if content is substantial
        if len(text) < 20:
            return ""
        
        return text
    
    def _basic_html_cleanup(self, content: str) -> str:
        """Basic HTML cleanup when BeautifulSoup fails.
        
        Args:
            content: HTML content to clean
            
        Returns:
            Cleaned content
        """
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML entities
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        
        return content.strip()
    
    def _extract_title(self, metadata: Dict[str, Any], content: str, file_path: Path) -> str:
        """Extract title from metadata, content, or filename.
        
        Args:
            metadata: Note metadata
            content: Note content
            file_path: Path to the note file
            
        Returns:
            Extracted title
        """
        # Try metadata first
        if 'title' in metadata:
            return metadata['title']
        
        # Try to extract from content (first heading or first line)
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('## '):
                return line[3:].strip()
            elif line and not line.startswith('---'):
                return line[:100]  # Limit length
        
        # Fallback to filename
        return file_path.stem.replace('_', ' ').replace('-', ' ')
    
    def _extract_dates(self, metadata: Dict[str, Any], file_path: Path) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract creation and modification dates.
        
        Args:
            metadata: Note metadata
            file_path: Path to the note file
            
        Returns:
            Tuple of (created_date, modified_date)
        """
        created_date = None
        modified_date = None
        
        # Try metadata dates
        if 'created' in metadata:
            try:
                created_date = datetime.fromisoformat(metadata['created'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        if 'modified' in metadata:
            try:
                modified_date = datetime.fromisoformat(metadata['modified'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Fallback to file system dates
        if not created_date:
            try:
                created_date = datetime.fromtimestamp(file_path.stat().st_ctime)
            except OSError:
                pass
        
        if not modified_date:
            try:
                modified_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            except OSError:
                pass
        
        return created_date, modified_date
    
    def _extract_tags(self, metadata: Dict[str, Any], content: str) -> List[str]:
        """Extract tags from metadata or content.
        
        Args:
            metadata: Note metadata
            content: Note content
            
        Returns:
            List of tags
        """
        tags = []
        
        # Try metadata tags
        if 'tags' in metadata:
            if isinstance(metadata['tags'], list):
                tags.extend(metadata['tags'])
            elif isinstance(metadata['tags'], str):
                # Parse comma-separated tags
                tags.extend([tag.strip() for tag in metadata['tags'].split(',')])
        
        # Try to extract tags from content (Obsidian format: [[tag]])
        tag_pattern = r'\[\[([^\]]+)\]\]'
        content_tags = re.findall(tag_pattern, content)
        tags.extend(content_tags)
        
        # Remove duplicates and clean
        tags = list(set([tag.strip() for tag in tags if tag.strip()]))
        
        return tags
    
    def _extract_source_url(self, metadata: Dict[str, Any], content: str) -> Optional[str]:
        """Extract source URL from metadata or content.
        
        Args:
            metadata: Note metadata
            content: Note content
            
        Returns:
            Source URL if found, None otherwise
        """
        # Try metadata first
        if 'source' in metadata:
            source = metadata['source']
            if source.startswith('http'):
                return source
        
        # Try to find URLs in content
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        if urls:
            return urls[0]  # Return first URL found
        
        return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract the main article content from the soup.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup object with main content or None if not found
        """
        # Try to find article content by looking for Reuters/news patterns
        article_indicators = [
            lambda el: 'REUTERS' in el.get_text(),
            lambda el: 'Reuters' in el.get_text(),
            lambda el: any(phrase in el.get_text() for phrase in ['officials said', 'according to', 'reported', 'announced']),
            lambda el: len(el.get_text().strip()) > 200 and any(word in el.get_text().lower() for word in ['project', 'company', 'government', 'development', 'investment'])
        ]
        
        # Look for paragraphs or divs containing article content
        potential_articles = []
        for element in soup.find_all(['p', 'div']):
            text = element.get_text().strip()
            if len(text) > 100:  # Substantial content
                score = 0
                for indicator in article_indicators:
                    if indicator(element):
                        score += 1
                if score > 0:
                    potential_articles.append((score, len(text), element))
        
        if potential_articles:
            # Sort by score first, then by length
            potential_articles.sort(key=lambda x: (x[0], x[1]), reverse=True)
            best_element = potential_articles[0][2]
            
            # Try to find the parent container that includes the full article
            parent = best_element
            while parent.parent and len(parent.parent.get_text().strip()) > len(best_element.get_text().strip()) * 1.5:
                parent = parent.parent
                # Stop if we're getting too much extra content
                if len(parent.get_text().strip()) > len(best_element.get_text().strip()) * 3:
                    break
            
            new_soup = BeautifulSoup('', 'html.parser')
            new_soup.append(parent.extract())
            return new_soup
        
        # Fallback: Common main content selectors
        main_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.article',
            '.post',
            '.entry',
            '.story'
        ]
        
        for selector in main_selectors:
            main_element = soup.select_one(selector)
            if main_element:
                new_soup = BeautifulSoup('', 'html.parser')
                new_soup.append(main_element.extract())
                return new_soup
        
        return None
    
    def _final_text_cleanup(self, content: str) -> str:
        """Final cleanup of text content to remove remaining clutter.
        
        Args:
            content: Text content to clean
            
        Returns:
            Cleaned text content
        """
        if not content:
            return content
        
        # First, clean up malformed URLs and broken links
        content = self._clean_malformed_urls(content)
        
        lines = content.split('\n')
        cleaned_lines = []
        in_article_content = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Detect when we're in substantial article content
            if (len(line) > 100 and any(word in line.lower() for word in 
                ['government', 'project', 'projects', 'construction', 'infrastructure', 'million', 'billion', 'company', 'investment'])):
                in_article_content = True
            
            # Keep substantial content lines (likely article paragraphs)
            if (len(line) > 50 and 
                any(word in line.lower() for word in ['the', 'and', 'said', 'project', 'company', 'government', 'will', 'would', 'can', 'construction', 'infrastructure', 'development'])):
                cleaned_lines.append(line)
                continue
            
            # If we're in article content, be much more conservative about removal
            if in_article_content:
                # Only remove very obvious clutter in article content
                skip_indicators = [
                    'PUBLICIDAD', 'Publicidad', 'Productos Yahoo!',
                    'Más Buscados', 'Todo Sobre Los Mercados',
                    'YAHOO! FINANZAS', 'Más Yahoo! Finanzas',
                    'Correo electrónico', 'Share on', 'Back to'
                ]
                
                # Only skip if it's clearly not article content
                if any(indicator in line for indicator in skip_indicators):
                    continue
                
                # Keep any remaining content when in article mode
                cleaned_lines.append(line)
                continue
            
            # Enhanced clutter removal for web content
            clutter_indicators = [
                'Buscar', 'buscar', 'Search', 'search',
                'Yahoo!', 'Copyright', 'Todos los derechos',
                'Política de privacidad', 'Términos del Servicio',
                'Ayuda', 'Mail', 'Inicio', 'Ver más', 'Mostrar más',
                'Saltar a', 'Haz de Y!', 'tu página de inicio',
                'Correo electrónico', 'Facebook', 'Twitter',
                'Publicar como', 'Escribe un comentario',
                'Deja un comentario', 'Aún no Hay Comentarios',
                'PUBLICIDAD', 'Publicidad', 'Productos Yahoo!',
                'Más Buscados', 'Todo Sobre Los Mercados',
                'Cotizaciones recientes', 'Hoy En Yahoo!',
                'YAHOO! FINANZAS', 'Más Yahoo! Finanzas',
                # Additional web clutter patterns
                'Tweet', 'Share', 'LinkedIn', 'Reddit', 'Pinterest',
                'Read also:', 'Related articles:', 'You might also like:',
                'Trending now:', 'Most popular:', 'Recommended for you:',
                'Subscribe to', 'Newsletter', 'Follow us', 'Sign up',
                'This page has been shared', 'View these Tweets',
                'Paper Edition', 'Page:', 'Print', 'Email this',
                'Next threat:', 'Shuttlers win', 'Undervalued',
                'Glorious moment', 'A weekend at', 'Headlines News'
            ]
            
            # Skip lines that contain clutter indicators (but preserve timestamps in article context)
            skip_line = False
            for indicator in clutter_indicators:
                if indicator in line:
                    # Exception: keep Reuters timestamps and source attributions
                    if not (in_article_content and ('Reuters' in line or 'AFP' in line or 'EFE' in line) and ('Hace' in line or 'horas' in line or 'CDT' in line)):
                        skip_line = True
                        break
            
            if skip_line:
                continue
            
            # Skip lines that are mostly symbols/punctuation
            if len(line) < 20 and not any(char.isalnum() for char in line):
                continue
            
            # Skip lines that look like navigation (mostly links) unless they're article content
            if not in_article_content and (line.count('|') > 3 or line.count('»') > 0):
                continue
            
            # Skip single-word lines that are likely navigation
            if not in_article_content and len(line.split()) == 1 and len(line) < 15:
                continue
            
            # Skip table formatting lines
            if line.startswith('|') and line.endswith('|'):
                continue
            
            # Skip lines with just symbols
            if re.match(r'^[\s\-\|:\+\*=#]+$', line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _has_meaningful_content(self, content: str, content_type: ContentType) -> bool:
        """Check if content has meaningful information."""
        if not content or len(content.strip()) < 10:
            return False
        
        # Audio content gets special treatment
        if content_type == ContentType.AUDIO_ANNOTATION:
            # Audio content is meaningful if it has attachment references
            return '![[attachments/' in content or len(content.strip()) > 50
        
        # Check for substantial text content
        words = content.split()
        meaningful_words = [word for word in words if len(word) > 3 and word.isalpha()]
        
        if len(meaningful_words) < 5:
            return False
        
        # Check for repetitive or template content
        unique_words = set(meaningful_words)
        if len(unique_words) < len(meaningful_words) * 0.3:  # Too much repetition
            return False
        
        # Check for common empty content patterns
        empty_patterns = [
            r'^#+\s*$',  # Only headers
            r'^\s*$',    # Only whitespace
            r'^!?\[\[.*\]\]\s*$',  # Only links
            r'^https?://.*$',  # Only URLs
            r'^.*TODO.*$',  # TODO placeholders
            r'^.*placeholder.*$',  # Placeholder text
        ]
        
        # Check for web clutter patterns (Spanish and English)
        web_clutter_patterns = [
            r'^Secciones$',  # Section headers
            r'^Casa Real.*',  # Royal family section
            r'^Madrid.*',  # Madrid section
            r'^Sevilla.*',  # Sevilla section
            r'^Aragón.*',  # Aragon section
            r'^Canarias.*',  # Canary Islands section
            r'^Castilla y León.*',  # Castile and Leon section
            r'^Cataluña.*',  # Catalonia section
            r'^C\. Valenciana.*',  # Valencia section
            r'^Galicia.*',  # Galicia section
            r'^Navarra.*',  # Navarre section
            r'^País Vasco.*',  # Basque Country section
            r'^Toledo.*',  # Toledo section
            r'^Internacional.*',  # International section
            r'^Declaración Renta.*',  # Tax declaration section
            r'^Inmobiliario.*',  # Real estate section
            r'^Blogs.*',  # Blogs section
            r'^Fe De Ratas.*',  # Fe de Ratas section
            r'^El Astrolabio.*',  # El Astrolabio section
            r'^El Sacapuntas.*',  # El Sacapuntas section
            r'^Real Madrid.*',  # Real Madrid section
            r'^Atlético de Madrid.*',  # Atletico Madrid section
            r'^Fútbol.*',  # Football section
            r'^Baloncesto.*',  # Basketball section
            r'^Tenis.*',  # Tennis section
            r'^Fórmula 1.*',  # Formula 1 section
            r'^Motos.*',  # Motorcycles section
            r'^Náutica.*',  # Sailing section
            r'^Ciclismo.*',  # Cycling section
            r'^Torneo ACBNext.*',  # ACB Next tournament section
            r'^Ciencia.*',  # Science section
            r'^Salud.*',  # Health section
            r'^Es Noticia$',  # It's News
            r'^Castor.*',  # Castor news
            r'^Presupuestos Generales.*',  # General Budget news
            r'^Elecciones Francia.*',  # French elections news
            r'^Cita Previa.*',  # Tax appointment news
            r'^Regalos Día de la Madre.*',  # Mother's Day gifts news
            r'^Venezuela.*',  # Venezuela news
            r'^La Casa de Papel.*',  # Money Heist news
            r'^YouTube.*',  # YouTube news
            r'^Brexit.*',  # Brexit news
            r'^Identifíquese$',  # Identify yourself
            r'^Acceda a ClubABC.*',  # Access ClubABC
            r'^Entre$',  # Enter
            r'^¿Ha olvidado su contraseña\?$',  # Forgot password
            r'^Regístrese$',  # Register
            r'^Únase a ClubABC.*',  # Join ClubABC
            r'^Regístrese ahora$',  # Register now
            r'^Síguenos en$',  # Follow us
            r'^_ABC\.es_$',  # ABC.es header
        ]
        
        content_lines = [line.strip() for line in content.split('\n') if line.strip()]
        meaningful_lines = 0
        web_clutter_lines = 0
        
        for line in content_lines:
            # Check if line contains web clutter
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in web_clutter_patterns):
                web_clutter_lines += 1
            elif not any(re.match(pattern, line, re.IGNORECASE) for pattern in empty_patterns):
                meaningful_lines += 1
        
        # Calculate clutter ratio
        total_lines = meaningful_lines + web_clutter_lines
        if total_lines == 0:
            return False
        
        clutter_ratio = web_clutter_lines / total_lines
        
        # Reject if more than 60% is web clutter (more strict)
        if clutter_ratio > 0.6:
            return False
        
        # Must have at least 3 substantial content lines (more strict)
        return meaningful_lines >= 3
    
    def _clean_malformed_urls(self, content: str) -> str:
        """Clean malformed URLs and broken links that cause processing issues.
        
        Args:
            content: Content to clean
            
        Returns:
            Content with malformed URLs cleaned
        """
        if not content:
            return content
        
        # Patterns for malformed/problematic content that causes infinite loops
        malformed_patterns = [
            # Complex malformed Obsidian links with embedded markdown and URLs
            r'!\[\[attachments/[^\]]*\]\]!\[\[attachments/[^\]]*\]\]\]\(http[^\)]*\)',
            # URLs with trailing punctuation that breaks parsing
            r'(https?://[^\s\)]+)\)\s*\)',
            r'(https?://[^\s\)]+)\?\s*\)',
            # Malformed email tracking URLs (too long and complex)
            r'http://tk\.wsjemail\.com/track\?[^\s\)]{200,}',
            # Broken Obsidian link syntax
            r'!\[\[attachments/[^\]]*\]\]!\[\[attachments/[^\]]*\]\]',
            # URLs that look like filesystem paths (probably broken)
            r'https?://[^\s]*\$FILE/[^\s]*',
            # Complex malformed patterns with mixed syntax
            r'[![^]]*\]\([^)]*\$FILE[^)]*\)',
            # Social media and sharing URLs
            r'https?://twitter\.com/intent/tweet[^\s\)]*',
            r'https?://[^\s]*facebook[^\s\)]*',
            r'https?://[^\s]*linkedin[^\s\)]*',
            # Broken Obsidian references with unknown filenames
            r'!\[\[attachments/[^\]]*unknown_filename[^\]]*\]\]',
            r'!\[\[[^\]]*resources/[^\]]*\]\]',
            # Navigation links that are clearly not content
            r'\[[^\]]*\]\(http://www\.thejakartapost\.com/news/\d{4}/\d{2}/\d{2}/[^\)]*\)',
        ]
        
        # Apply cleaning patterns
        for pattern in malformed_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra whitespace left by removals
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'  +', ' ', content)
        
        return content.strip()
    

