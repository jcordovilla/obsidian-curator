"""Content processing and cleaning for Obsidian notes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import markdown
from bs4 import BeautifulSoup
from loguru import logger

from .models import Note, ContentType


class ContentProcessor:
    """Processes and cleans Obsidian note content."""
    
    def __init__(self, clean_html: bool = True, preserve_metadata: bool = True):
        """Initialize the content processor.
        
        Args:
            clean_html: Whether to clean HTML content
            preserve_metadata: Whether to preserve original metadata
        """
        self.clean_html = clean_html
        self.preserve_metadata = preserve_metadata
        
        # Common HTML elements to remove
        self.html_elements_to_remove = [
            'script', 'style', 'noscript', 'iframe', 'embed', 'object',
            'form', 'input', 'button', 'select', 'textarea'
        ]
        
        # Common web clutter patterns
        self.clutter_patterns = [
            r'<!--.*?-->',  # HTML comments
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',  # Ad containers
            r'<div[^>]*class="[^"]*social[^"]*"[^>]*>.*?</div>',  # Social media widgets
            r'<div[^>]*class="[^"]*cookie[^"]*"[^>]*>.*?</div>',  # Cookie notices
            r'<div[^>]*class="[^"]*popup[^"]*"[^>]*>.*?</div>',  # Popup overlays
        ]
    
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
        
        # Determine content type
        content_type = self._determine_content_type(metadata, clean_content)
        
        # Clean content if needed
        if self.clean_html and content_type == ContentType.WEB_CLIPPING:
            clean_content = self._clean_html_content(clean_content)
        
        # Extract title
        title = self._extract_title(metadata, clean_content, file_path)
        
        # Extract dates
        created_date, modified_date = self._extract_dates(metadata, file_path)
        
        # Extract tags
        tags = self._extract_tags(metadata, clean_content)
        
        # Extract source URL
        source_url = self._extract_source_url(metadata, clean_content)
        
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
    
    def _determine_content_type(self, metadata: Dict[str, Any], content: str) -> ContentType:
        """Determine the type of content based on metadata and content.
        
        Args:
            metadata: Note metadata
            content: Note content
            
        Returns:
            ContentType enum value
        """
        # Check metadata for content type indicators
        if 'source' in metadata and metadata['source'].startswith('http'):
            return ContentType.WEB_CLIPPING
        
        if 'source' in metadata and metadata['source'].endswith('.pdf'):
            return ContentType.PDF_ANNOTATION
        
        # Check content for indicators
        content_lower = content.lower()
        
        if any(pattern in content_lower for pattern in ['<html', '<div', '<span', '<p>']):
            return ContentType.WEB_CLIPPING
        
        if any(pattern in content_lower for pattern in ['academic', 'research', 'study', 'paper']):
            return ContentType.ACADEMIC_PAPER
        
        if any(pattern in content_lower for pattern in ['professional', 'industry', 'business']):
            return ContentType.PROFESSIONAL_PUBLICATION
        
        # Default to personal note if no clear indicators
        return ContentType.PERSONAL_NOTE
    
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
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
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
        
        # Convert to markdown
        try:
            # Use markdownify or similar for better conversion
            cleaned_content = self._html_to_markdown(soup)
        except Exception as e:
            logger.warning(f"Failed to convert HTML to markdown: {e}")
            cleaned_content = soup.get_text(separator='\n', strip=True)
        
        return cleaned_content
    
    def _clean_web_elements(self, soup: BeautifulSoup) -> None:
        """Clean up common web elements that add clutter.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove navigation elements
        for nav in soup.find_all(['nav', 'header', 'footer']):
            nav.decompose()
        
        # Remove common web clutter
        clutter_classes = [
            'advertisement', 'ad', 'banner', 'sidebar', 'navigation',
            'menu', 'footer', 'header', 'social', 'share', 'comment',
            'related', 'recommended', 'popular', 'trending'
        ]
        
        for element in soup.find_all(class_=clutter_classes):
            element.decompose()
        
        # Remove elements with common clutter IDs
        clutter_ids = ['ad', 'banner', 'sidebar', 'nav', 'menu', 'footer', 'header']
        for element in soup.find_all(id=clutter_ids):
            element.decompose()
    
    def _html_to_markdown(self, soup: BeautifulSoup) -> str:
        """Convert cleaned HTML to markdown.
        
        Args:
            soup: Cleaned BeautifulSoup object
            
        Returns:
            Markdown content
        """
        # Convert common HTML elements to markdown
        markdown_content = ""
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                markdown_content += f"{'#' * level} {element.get_text().strip()}\n\n"
            elif element.name == 'p':
                text = element.get_text().strip()
                if text:
                    markdown_content += f"{text}\n\n"
            elif element.name == 'ul':
                for li in element.find_all('li', recursive=False):
                    markdown_content += f"- {li.get_text().strip()}\n"
                markdown_content += "\n"
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li', recursive=False), 1):
                    markdown_content += f"{i}. {li.get_text().strip()}\n"
                markdown_content += "\n"
            elif element.name == 'blockquote':
                text = element.get_text().strip()
                if text:
                    markdown_content += f"> {text}\n\n"
            elif element.name == 'code':
                text = element.get_text().strip()
                if text:
                    markdown_content += f"`{text}`"
            elif element.name == 'pre':
                text = element.get_text().strip()
                if text:
                    markdown_content += f"```\n{text}\n```\n\n"
        
        return markdown_content.strip()
    
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
