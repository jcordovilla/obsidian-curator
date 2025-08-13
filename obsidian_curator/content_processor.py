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


class ContentProcessor:
    """Processes and cleans Obsidian note content."""
    
    def __init__(self, 
                 clean_html: bool = True, 
                 preserve_metadata: bool = True,
                 extract_linked_content: bool = True,
                 max_pdf_pages: int = 100,
                 intelligent_extraction: bool = True,
                 ai_model: str = None):
        """Initialize the content processor.
        
        Args:
            clean_html: Whether to clean HTML content
            preserve_metadata: Whether to preserve original metadata
            extract_linked_content: Whether to extract content from linked PDFs, images, URLs
            max_pdf_pages: Maximum number of PDF pages to process
            intelligent_extraction: Use AI to filter and summarize extracted content
            ai_model: AI model to use for intelligent extraction
        """
        self.clean_html = clean_html
        self.preserve_metadata = preserve_metadata
        self.extract_linked_content = extract_linked_content
        
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
        self.clutter_patterns = [
            r'<!--.*?-->',  # HTML comments
            r'<script[^>]*>.*?</script>',  # JavaScript
            r'<style[^>]*>.*?</style>',  # CSS
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',  # Ad containers
            r'<div[^>]*class="[^"]*social[^"]*"[^>]*>.*?</div>',  # Social media widgets
            r'<div[^>]*class="[^"]*cookie[^"]*"[^>]*>.*?</div>',  # Cookie notices
            r'<div[^>]*class="[^"]*popup[^"]*"[^>]*>.*?</div>',  # Popup overlays
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',  # Navigation
            r'<div[^>]*class="[^"]*menu[^"]*"[^>]*>.*?</div>',  # Menus
            r'<div[^>]*class="[^"]*header[^"]*"[^>]*>.*?</div>',  # Headers
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',  # Footers
            r'<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>.*?</div>',  # Sidebars
            r'<nav[^>]*>.*?</nav>',  # Navigation elements
            r'<header[^>]*>.*?</header>',  # Header elements
            r'<footer[^>]*>.*?</footer>',  # Footer elements
            r'<aside[^>]*>.*?</aside>',  # Aside elements
            r'\[Saltar a.*?\]',  # Skip navigation links
            r'\(Publicidad\)',  # Advertisement markers
            r'PUBLICIDAD',  # Advertisement text
            r'Copyright.*?\..*?$',  # Copyright notices
            r'Cotizaciones.*?redistribuir.*?información.*?$',  # Legal disclaimers
            r'Yahoo!.*?Finanzas.*?México',  # Site branding
            r'Haz de Y! tu página.*?inicio',  # Yahoo branding
            r'@\w+\s+en\s+Twitter',  # Social media links
            r'hazte fan en.*?Facebook',  # Facebook links
            r'Ver más.*?»',  # "See more" links
            r'Mostrar más',  # "Show more" links
            r'\d+\s*-\s*\d+\s+de\s+\d+',  # Pagination
            r'mar,.*?\d{4}.*?CDT',  # Date/time stamps
            r'Hace \d+.*?horas?',  # "X hours ago" timestamps
            r'Reuters.*?Hace.*?horas?',  # News source timestamps
            r'AFP.*?Hace.*?horas?',  # News source timestamps
            r'EFE.*?Hace.*?horas?',  # News source timestamps
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
        
        # Clean content if needed - apply only to content types that actually contain HTML
        if self.clean_html and content_type in [ContentType.WEB_CLIPPING, ContentType.IMAGE_ANNOTATION, ContentType.PDF_ANNOTATION]:
            clean_content = self._clean_html_content(clean_content)
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
        # Check for PDF annotations first (highest priority for specific content)
        if self._contains_pdf_references(content):
            return ContentType.PDF_ANNOTATION
        
        # Check for image annotations
        if self._contains_image_references(content):
            return ContentType.IMAGE_ANNOTATION
        
        # Check for web clippings vs URL references vs personal notes with URLs
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
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
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
            # Content is already Markdown - just apply text cleanup
            cleaned_content = content
        
        # Final cleanup of remaining clutter
        cleaned_content = self._final_text_cleanup(cleaned_content)
        
        return cleaned_content
    
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
            'subscribe', 'newsletter', 'signup', 'login', 'search'
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
            
            # Detect when we're in article content (starts with Reuters, etc.)
            if ('REUTERS' in line or 'Reuters' in line or 
                any(phrase in line for phrase in ['officials said', 'according to', 'announced']) and len(line) > 50):
                in_article_content = True
            
            # If we're in article content, be much more conservative about removal
            if in_article_content:
                # Only remove very obvious clutter in article content
                skip_indicators = [
                    'PUBLICIDAD', 'Publicidad', 'Productos Yahoo!',
                    'Más Buscados', 'Todo Sobre Los Mercados',
                    'YAHOO! FINANZAS', 'Más Yahoo! Finanzas',
                    'Correo electrónico'
                ]
                
                # Only skip if it's clearly not article content
                if any(indicator in line for indicator in skip_indicators):
                    continue
                
                # Don't skip lines with substantive content (> 30 chars and has meaningful words)
                if len(line) > 30 and any(word in line.lower() for word in ['the', 'and', 'said', 'project', 'company', 'government', 'will', 'would', 'can']):
                    cleaned_lines.append(line)
                    continue
            
            # Standard clutter removal for non-article content
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
                'YAHOO! FINANZAS', 'Más Yahoo! Finanzas'
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
        ]
        
        # Apply cleaning patterns
        for pattern in malformed_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra whitespace left by removals
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'  +', ' ', content)
        
        return content.strip()
    

