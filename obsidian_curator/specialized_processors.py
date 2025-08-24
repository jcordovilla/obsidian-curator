"""Specialized content processors for different content types."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass

from loguru import logger

from .ai_content_classifier import ContentCategory, ContentAnalysis
from .models import ContentType


@dataclass
class ProcessingResult:
    """Result of specialized content processing."""
    cleaned_content: str
    extracted_metadata: Dict[str, Any]
    processing_notes: List[str]
    quality_score: float
    content_type: ContentType


class SpecializedContentProcessor:
    """Specialized content processors for different content types."""
    
    def __init__(self):
        """Initialize the specialized content processor."""
        self.processors = {
            ContentCategory.URL_BOOKMARK: self._process_url_bookmark,
            ContentCategory.WEB_CLIPPING: self._process_web_clipping,
            ContentCategory.PDF_ANNOTATION: self._process_pdf_annotation,
            ContentCategory.IMAGE_ANNOTATION: self._process_image_annotation,
            ContentCategory.AUDIO_VIDEO_NOTE: self._process_audio_video_note,
            ContentCategory.PURE_TEXT_NOTE: self._process_pure_text_note,
            ContentCategory.MIXED_CONTENT: self._process_mixed_content,
            ContentCategory.SOCIAL_MEDIA_POST: self._process_social_media_post,
            ContentCategory.ACADEMIC_PAPER: self._process_academic_paper,
            ContentCategory.CORPORATE_CONTENT: self._process_corporate_content,
            ContentCategory.NEWS_ARTICLE: self._process_news_article,
            ContentCategory.TECHNICAL_DOCUMENT: self._process_technical_document,
            ContentCategory.UNKNOWN: self._process_unknown_content,
        }
    
    def process_content(self, 
                       content: str, 
                       analysis: ContentAnalysis, 
                       metadata: Dict[str, Any],
                       file_path: Path) -> ProcessingResult:
        """Process content using the appropriate specialized processor.
        
        Args:
            content: Raw content to process
            analysis: AI content analysis result
            metadata: Note metadata
            file_path: Path to the note file
            
        Returns:
            ProcessingResult with cleaned content and metadata
        """
        processor = self.processors.get(analysis.category)
        if processor:
            return processor(content, analysis, metadata, file_path)
        else:
            logger.warning(f"No specialized processor for category: {analysis.category}")
            return self._process_unknown_content(content, analysis, metadata, file_path)
    
    def _process_url_bookmark(self, 
                             content: str, 
                             analysis: ContentAnalysis, 
                             metadata: Dict[str, Any],
                             file_path: Path) -> ProcessingResult:
        """Process URL bookmark content - extract title and URL only."""
        processing_notes = ["Processing as URL bookmark"]
        
        # Extract title and URL
        lines = content.split('\n')
        title = ""
        url = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
            elif re.match(r'https?://', line):
                url = line.strip()
            elif re.match(r'www\.', line):
                url = f"https://{line.strip()}"
        
        # Create clean content
        if title and url:
            cleaned_content = f"# {title}\n\n{url}"
            quality_score = 0.9
            processing_notes.append("Successfully extracted title and URL")
        else:
            cleaned_content = content
            quality_score = 0.5
            processing_notes.append("Failed to extract clean title/URL structure")
        
        # Extract metadata
        extracted_metadata = {
            'title': title or metadata.get('title', ''),
            'url': url,
            'content_type': 'url_bookmark',
            'processing_strategy': 'minimal_cleaning'
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.URL_REFERENCE
        )
    
    def _process_web_clipping(self, 
                             content: str, 
                             analysis: ContentAnalysis, 
                             metadata: Dict[str, Any],
                             file_path: Path) -> ProcessingResult:
        """Process web clipping content with aggressive cleaning."""
        processing_notes = ["Processing as web clipping with aggressive cleaning"]
        
        # Apply aggressive web cleaning patterns
        cleaned_content = self._aggressive_web_cleaning(content)
        
        # Validate cleaned content quality
        if len(cleaned_content.strip()) < 100:
            processing_notes.append("Warning: Content too short after cleaning")
            quality_score = 0.3
        elif self._has_excessive_navigation(cleaned_content):
            processing_notes.append("Warning: Still contains excessive navigation elements")
            quality_score = 0.5
        else:
            processing_notes.append("Successfully cleaned web content")
            quality_score = 0.8
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'web_clipping',
            'processing_strategy': 'aggressive_web_cleaning',
            'original_length': len(content),
            'cleaned_length': len(cleaned_content),
            'cleaning_ratio': len(cleaned_content) / max(1, len(content))
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.WEB_CLIPPING
        )
    
    def _process_pdf_annotation(self, 
                               content: str, 
                               analysis: ContentAnalysis, 
                               metadata: Dict[str, Any],
                               file_path: Path) -> ProcessingResult:
        """Process PDF annotation content - preserve both PDF and user notes."""
        processing_notes = ["Processing as PDF annotation"]
        
        # Separate PDF content from user annotations
        pdf_content = []
        user_notes = []
        
        lines = content.split('\n')
        in_pdf_section = False
        
        for line in lines:
            if re.search(r'!\[\[.*\.pdf\]\]|\[\[.*\.pdf\]\]|PDF|pdf', line, re.IGNORECASE):
                in_pdf_section = True
                pdf_content.append(line)
            elif in_pdf_section and line.strip():
                pdf_content.append(line)
            elif line.strip() and not line.startswith('---'):
                user_notes.append(line)
        
        # Reconstruct content with clear separation
        cleaned_content = ""
        if pdf_content:
            cleaned_content += "## PDF Content\n\n" + "\n".join(pdf_content) + "\n\n"
        if user_notes:
            cleaned_content += "## User Notes\n\n" + "\n".join(user_notes)
        
        # Quality assessment
        if pdf_content and user_notes:
            quality_score = 0.9
            processing_notes.append("Successfully separated PDF content and user notes")
        elif pdf_content or user_notes:
            quality_score = 0.7
            processing_notes.append("Partial content found")
        else:
            quality_score = 0.3
            processing_notes.append("No clear PDF or annotation content found")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'pdf_annotation',
            'processing_strategy': 'preserve_both_pdf_and_annotations',
            'has_pdf_content': bool(pdf_content),
            'has_user_notes': bool(user_notes),
            'pdf_lines': len(pdf_content),
            'annotation_lines': len(user_notes)
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.PDF_ANNOTATION
        )
    
    def _process_image_annotation(self, 
                                 content: str, 
                                 analysis: ContentAnalysis, 
                                 metadata: Dict[str, Any],
                                 file_path: Path) -> ProcessingResult:
        """Process image annotation content."""
        processing_notes = ["Processing as image annotation"]
        
        # Extract image references and explanatory text
        image_refs = re.findall(r'!\[\[.*\.(png|jpg|jpeg|gif|svg|webp)\]\]', content, re.IGNORECASE)
        markdown_images = re.findall(r'!\[.*?\]\(.*?\.(png|jpg|jpeg|gif|svg|webp)\)', content, re.IGNORECASE)
        
        # Remove image references to get clean text
        clean_text = re.sub(r'!\[\[.*?\.(png|jpg|jpeg|gif|svg|webp)\]\]', '', content, flags=re.IGNORECASE)
        clean_text = re.sub(r'!\[.*?\]\(.*?\.(png|jpg|jpeg|gif|svg|webp)\)', '', clean_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)
        clean_text = clean_text.strip()
        
        # Quality assessment
        if image_refs or markdown_images:
            if len(clean_text.strip()) > 50:
                quality_score = 0.8
                processing_notes.append("Successfully extracted image references and explanatory text")
            else:
                quality_score = 0.6
                processing_notes.append("Image references found but minimal explanatory text")
        else:
            quality_score = 0.4
            processing_notes.append("No clear image references found")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'image_annotation',
            'processing_strategy': 'extract_image_reference_and_text',
            'image_references': image_refs + markdown_images,
            'explanatory_text_length': len(clean_text.strip())
        }
        
        return ProcessingResult(
            cleaned_content=clean_text,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.IMAGE_ANNOTATION
        )
    
    def _process_audio_video_note(self, 
                                 content: str, 
                                 analysis: ContentAnalysis, 
                                 metadata: Dict[str, Any],
                                 file_path: Path) -> ProcessingResult:
        """Process audio/video note content."""
        processing_notes = ["Processing as audio/video note"]
        
        # Extract media references and notes
        media_refs = re.findall(r'!\[\[.*\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\]\]', content, re.IGNORECASE)
        markdown_media = re.findall(r'!\[.*?\]\(.*?\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\)', content, re.IGNORECASE)
        obsidian_resources = re.findall(r'!\[\[attachments/.*\.resources/.*\]\]', content, re.IGNORECASE)
        
        # Remove media references to get clean text
        clean_text = re.sub(r'!\[\[.*?\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\]\]', '', content, flags=re.IGNORECASE)
        clean_text = re.sub(r'!\[.*?\]\(.*?\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\)', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'!\[\[attachments/.*\.resources/.*\]\]', '', clean_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)
        clean_text = clean_text.strip()
        
        # Quality assessment
        if media_refs or markdown_media or obsidian_resources:
            if len(clean_text.strip()) > 30:
                quality_score = 0.8
                processing_notes.append("Successfully extracted media references and notes")
            else:
                quality_score = 0.6
                processing_notes.append("Media references found but minimal notes")
        else:
            quality_score = 0.4
            processing_notes.append("No clear media references found")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'audio_video_note',
            'processing_strategy': 'extract_media_reference_and_notes',
            'media_references': media_refs + markdown_media + obsidian_resources,
            'notes_length': len(clean_text.strip())
        }
        
        return ProcessingResult(
            cleaned_content=clean_text,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.AUDIO_ANNOTATION
        )
    
    def _process_pure_text_note(self, 
                               content: str, 
                               analysis: ContentAnalysis, 
                               metadata: Dict[str, Any],
                               file_path: Path) -> ProcessingResult:
        """Process pure text note content with minimal cleaning."""
        processing_notes = ["Processing as pure text note with minimal cleaning"]
        
        # Apply minimal cleaning - just normalize whitespace
        cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        cleaned_content = cleaned_content.strip()
        
        # Quality assessment
        if len(cleaned_content) > 300:
            quality_score = 0.9
            processing_notes.append("Substantial text content preserved")
        elif len(cleaned_content) > 100:
            quality_score = 0.7
            processing_notes.append("Moderate text content preserved")
        else:
            quality_score = 0.5
            processing_notes.append("Limited text content")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'pure_text_note',
            'processing_strategy': 'minimal_cleaning_preserve_structure',
            'original_length': len(content),
            'cleaned_length': len(cleaned_content),
            'word_count': len(cleaned_content.split())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.PERSONAL_NOTE
        )
    
    def _process_mixed_content(self, 
                             content: str, 
                             analysis: ContentAnalysis, 
                             metadata: Dict[str, Any],
                             file_path: Path) -> ProcessingResult:
        """Process mixed content by identifying and processing each type separately."""
        processing_notes = ["Processing as mixed content"]
        
        # Identify content sections
        sections = self._identify_content_sections(content)
        
        # Process each section with appropriate strategy
        processed_sections = []
        total_quality = 0
        
        for section_type, section_content in sections:
            if section_type == 'text':
                processed_content = self._process_pure_text_note(section_content, analysis, metadata, file_path)
                processed_sections.append(('Text', processed_content.cleaned_content))
                total_quality += processed_content.quality_score
            elif section_type == 'web':
                processed_content = self._process_web_clipping(section_content, analysis, metadata, file_path)
                processed_sections.append(('Web Content', processed_content.cleaned_content))
                total_quality += processed_content.quality_score
            elif section_type == 'url':
                processed_content = self._process_url_bookmark(section_content, analysis, metadata, file_path)
                processed_sections.append(('URL Reference', processed_content.cleaned_content))
                total_quality += processed_content.quality_score
            else:
                processed_sections.append(('Other', section_content))
                total_quality += 0.5
        
        # Reconstruct content with clear section headers
        cleaned_content = ""
        for section_name, section_content in processed_sections:
            if section_content.strip():
                cleaned_content += f"## {section_name}\n\n{section_content.strip()}\n\n"
        
        cleaned_content = cleaned_content.strip()
        
        # Calculate average quality
        avg_quality = total_quality / max(1, len(sections))
        
        processing_notes.append(f"Identified {len(sections)} content sections")
        processing_notes.append(f"Processed each section with appropriate strategy")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'mixed_content',
            'processing_strategy': 'separate_and_process_each_type',
            'sections_identified': len(sections),
            'section_types': [s[0] for s in sections],
            'average_quality': avg_quality
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=avg_quality,
            content_type=ContentType.WEB_CLIPPING  # Default for mixed content
        )
    
    def _process_social_media_post(self, 
                                  content: str, 
                                  analysis: ContentAnalysis, 
                                  metadata: Dict[str, Any],
                                  file_path: Path) -> ProcessingResult:
        """Process social media post content."""
        processing_notes = ["Processing as social media post"]
        
        # Remove platform-specific chrome
        cleaned_content = self._remove_social_media_chrome(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 100:
            quality_score = 0.8
            processing_notes.append("Successfully extracted post content")
        else:
            quality_score = 0.5
            processing_notes.append("Limited post content extracted")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'social_media_post',
            'processing_strategy': 'extract_post_content_remove_platform_chrome',
            'platform_indicators': self._detect_social_platforms(content),
            'post_content_length': len(cleaned_content.strip())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.WEB_CLIPPING
        )
    
    def _process_academic_paper(self, 
                               content: str, 
                               analysis: ContentAnalysis, 
                               metadata: Dict[str, Any],
                               file_path: Path) -> ProcessingResult:
        """Process academic paper content."""
        processing_notes = ["Processing as academic paper"]
        
        # Preserve academic structure while cleaning formatting
        cleaned_content = self._preserve_academic_structure(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 200:
            quality_score = 0.9
            processing_notes.append("Successfully preserved academic structure")
        else:
            quality_score = 0.6
            processing_notes.append("Limited academic content")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'academic_paper',
            'processing_strategy': 'preserve_academic_structure_remove_formatting',
            'has_abstract': 'abstract' in content.lower(),
            'has_methodology': 'methodology' in content.lower(),
            'academic_length': len(cleaned_content.strip())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.ACADEMIC_PAPER
        )
    
    def _process_corporate_content(self, 
                                  content: str, 
                                  analysis: ContentAnalysis, 
                                  metadata: Dict[str, Any],
                                  file_path: Path) -> ProcessingResult:
        """Process corporate content."""
        processing_notes = ["Processing as corporate content"]
        
        # Extract business content while removing marketing
        cleaned_content = self._extract_business_content(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 150:
            quality_score = 0.8
            processing_notes.append("Successfully extracted business content")
        else:
            quality_score = 0.5
            processing_notes.append("Limited business content")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'corporate_content',
            'processing_strategy': 'extract_business_content_remove_marketing',
            'business_indicators': self._detect_business_content(content),
            'business_content_length': len(cleaned_content.strip())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.WEB_CLIPPING
        )
    
    def _process_news_article(self, 
                             content: str, 
                             analysis: ContentAnalysis, 
                             metadata: Dict[str, Any],
                             file_path: Path) -> ProcessingResult:
        """Process news article content."""
        processing_notes = ["Processing as news article"]
        
        # Extract article content while removing navigation
        cleaned_content = self._extract_news_content(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 200:
            quality_score = 0.8
            processing_notes.append("Successfully extracted news content")
        else:
            quality_score = 0.5
            processing_notes.append("Limited news content")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'news_article',
            'processing_strategy': 'extract_article_remove_navigation',
            'news_indicators': self._detect_news_content(content),
            'article_length': len(cleaned_content.strip())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.WEB_CLIPPING
        )
    
    def _process_technical_document(self, 
                                   content: str, 
                                   analysis: ContentAnalysis, 
                                   metadata: Dict[str, Any],
                                   file_path: Path) -> ProcessingResult:
        """Process technical document content."""
        processing_notes = ["Processing as technical document"]
        
        # Preserve technical structure while cleaning formatting
        cleaned_content = self._preserve_technical_structure(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 150:
            quality_score = 0.9
            processing_notes.append("Successfully preserved technical structure")
        else:
            quality_score = 0.6
            processing_notes.append("Limited technical content")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'technical_document',
            'processing_strategy': 'preserve_technical_structure_clean_formatting',
            'technical_indicators': self._detect_technical_content(content),
            'technical_length': len(cleaned_content.strip())
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.PDF_ANNOTATION  # Often technical docs are PDFs
        )
    
    def _process_unknown_content(self, 
                                content: str, 
                                analysis: ContentAnalysis, 
                                metadata: Dict[str, Any],
                                file_path: Path) -> ProcessingResult:
        """Process unknown content type with standard cleaning."""
        processing_notes = ["Processing as unknown content type with standard cleaning"]
        
        # Apply standard cleaning
        cleaned_content = self._standard_content_cleaning(content)
        
        # Quality assessment
        if len(cleaned_content.strip()) > 100:
            quality_score = 0.6
            processing_notes.append("Applied standard cleaning")
        else:
            quality_score = 0.3
            processing_notes.append("Limited content after standard cleaning")
        
        # Extract metadata
        extracted_metadata = {
            'content_type': 'unknown',
            'processing_strategy': 'standard_processing',
            'original_length': len(content),
            'cleaned_length': len(cleaned_content)
        }
        
        return ProcessingResult(
            cleaned_content=cleaned_content,
            extracted_metadata=extracted_metadata,
            processing_notes=processing_notes,
            quality_score=quality_score,
            content_type=ContentType.PERSONAL_NOTE
        )
    
    # Helper methods for content processing
    
    def _aggressive_web_cleaning(self, content: str) -> str:
        """Apply aggressive web content cleaning."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove common web clutter
        clutter_patterns = [
            r'Skip to main content',
            r'Navigation',
            r'Menu',
            r'Footer',
            r'Header',
            r'Sidebar',
            r'Advertisement',
            r'Share on',
            r'Follow us',
            r'Subscribe',
            r'Cookie notice',
            r'Privacy policy',
            r'Terms of service',
            r'Copyright',
            r'All rights reserved'
        ]
        
        for pattern in clutter_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'  +', ' ', content)
        
        return content.strip()
    
    def _has_excessive_navigation(self, content: str) -> bool:
        """Check if content has excessive navigation elements."""
        navigation_words = ['menu', 'navigation', 'footer', 'header', 'sidebar', 'nav']
        words = content.lower().split()
        nav_count = sum(1 for word in words if word in navigation_words)
        return nav_count > len(words) * 0.05  # More than 5% navigation words
    
    def _identify_content_sections(self, content: str) -> List[Tuple[str, str]]:
        """Identify different content sections in mixed content."""
        sections = []
        
        # Split by common separators
        parts = re.split(r'---|\n\s*\n\s*\n', content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Classify part type
            if re.search(r'https?://|www\.', part):
                sections.append(('url', part))
            elif re.search(r'<[^>]+>', part):
                sections.append(('web', part))
            else:
                sections.append(('text', part))
        
        return sections
    
    def _remove_social_media_chrome(self, content: str) -> str:
        """Remove social media platform chrome."""
        chrome_patterns = [
            r'Skip to main content',
            r'Find People, Jobs, Companies',
            r'Grow my network',
            r'Pending invitations',
            r'People you may know',
            r'Add contacts',
            r'Account & settings',
            r'Sign out',
            r'Upgrade.*account',
            r'Job posting manage',
            r'Company page manage',
            r'Privacy.*settings',
            r'Help center',
            r'Get help',
            r'Edit profile',
            r'Who.*viewed.*profile',
            r'Your updates',
            r'Connections',
            r'Find alumni',
            r'Learning',
            r'Talent solutions',
            r'Sales solutions',
            r'Try premium',
            r'User agreement',
            r'Privacy policy',
            r'Ad choices',
            r'Community guidelines',
            r'Cookie policy'
        ]
        
        for pattern in chrome_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _detect_social_platforms(self, content: str) -> List[str]:
        """Detect social media platforms in content."""
        platforms = []
        if 'linkedin.com' in content.lower():
            platforms.append('LinkedIn')
        if 'twitter.com' in content.lower():
            platforms.append('Twitter')
        if 'facebook.com' in content.lower():
            platforms.append('Facebook')
        return platforms
    
    def _preserve_academic_structure(self, content: str) -> str:
        """Preserve academic structure while cleaning formatting."""
        # Keep academic headers
        content = re.sub(r'^Abstract\s*:', '## Abstract\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Introduction\s*:', '## Introduction\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Methodology\s*:', '## Methodology\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Results\s*:', '## Results\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Conclusion\s*:', '## Conclusion\n\n', content, flags=re.MULTILINE)
        
        # Clean up formatting
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def _extract_business_content(self, content: str) -> str:
        """Extract business content while removing marketing."""
        # Remove marketing language
        marketing_patterns = [
            r'Contact us today',
            r'Get started now',
            r'Limited time offer',
            r'Special pricing',
            r'Call now',
            r'Act fast',
            r'Don\'t miss out',
            r'Exclusive deal'
        ]
        
        for pattern in marketing_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _detect_business_content(self, content: str) -> List[str]:
        """Detect business content indicators."""
        indicators = []
        business_words = ['company', 'business', 'enterprise', 'organization', 'corporate']
        for word in business_words:
            if word in content.lower():
                indicators.append(word)
        return indicators
    
    def _extract_news_content(self, content: str) -> str:
        """Extract news article content while removing navigation."""
        # Remove news navigation
        nav_patterns = [
            r'Related articles',
            r'More from',
            r'Trending',
            r'Popular',
            r'Recommended',
            r'Read also',
            r'You might also like'
        ]
        
        for pattern in nav_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _detect_news_content(self, content: str) -> List[str]:
        """Detect news content indicators."""
        indicators = []
        news_words = ['reuters', 'afp', 'efe', 'news', 'breaking', 'published', 'reporter']
        for word in news_words:
            if word in content.lower():
                indicators.append(word)
        return indicators
    
    def _preserve_technical_structure(self, content: str) -> str:
        """Preserve technical structure while cleaning formatting."""
        # Keep technical headers
        content = re.sub(r'^Specification\s*:', '## Specification\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Requirements\s*:', '## Requirements\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Installation\s*:', '## Installation\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^Usage\s*:', '## Usage\n\n', content, flags=re.MULTILINE)
        content = re.sub(r'^API\s*:', '## API\n\n', content, flags=re.MULTILINE)
        
        # Clean up formatting
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def _detect_technical_content(self, content: str) -> List[str]:
        """Detect technical content indicators."""
        indicators = []
        technical_words = ['api', 'sdk', 'framework', 'library', 'protocol', 'specification']
        for word in technical_words:
            if word in content.lower():
                indicators.append(word)
        return indicators
    
    def _standard_content_cleaning(self, content: str) -> str:
        """Apply standard content cleaning."""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'  +', ' ', content)
        
        # Remove common clutter
        content = re.sub(r'^\s*$', '', content, flags=re.MULTILINE)
        
        return content.strip()
