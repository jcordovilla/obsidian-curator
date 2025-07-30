"""Evernote clipping content cleaner and extractor."""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from bs4 import BeautifulSoup
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class EvernoteCleaningResult:
    """Result of cleaning an Evernote clipping."""
    original_content: str
    cleaned_content: str
    extracted_title: Optional[str]
    extracted_url: Optional[str]
    extracted_tags: List[str]
    extracted_date: Optional[str]
    cleaning_stats: Dict[str, Any]
    is_evernote_clipping: bool


class EvernoteClippingCleaner:
    """Specialized cleaner for Evernote web clippings."""
    
    def __init__(self):
        """Initialize the cleaner."""
        # Evernote clipping patterns
        self.evernote_patterns = {
            'clipping_header': [
                r'---\s*\n(?:.*?\n)*?---\s*\n',
                r'Clipped from:.*?\n',
                r'Saved from:.*?\n',
                r'Source:.*?\n',
                r'Original URL:.*?\n',
                r'Clipped on:.*?\n',
                r'Tags:.*?\n',
                r'Notebook:.*?\n'
            ],
            'metadata_sections': [
                r'---\s*\n(?:.*?\n)*?---\s*\n',
                r'# Evernote Web Clipper.*?\n',
                r'# Saved from.*?\n',
                r'# Clipped from.*?\n'
            ],
            'evernote_footer': [
                r'\n---\s*\nEvernote.*?\n',
                r'\n---\s*\nSaved with Evernote.*?\n',
                r'\n---\s*\nClipped with Evernote.*?\n'
            ]
        }
        
        # Content extraction patterns
        self.extraction_patterns = {
            'title': [
                r'title:\s*(.+?)(?:\n|$)',
                r'#\s*(.+?)(?:\n|$)',
                r'<title>(.+?)</title>',
                r'<h1[^>]*>(.+?)</h1>'
            ],
            'url': [
                r'source:\s*(https?://[^\s\n]+)',
                r'Original URL:\s*(https?://[^\s\n]+)',
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            ],
            'tags': [
                r'tags:\s*(.+?)(?:\n|$)',
                r'Tags:\s*(.+?)(?:\n|$)',
                r'-\s*([A-Z][A-Z\s]+)(?:\n|$)',
                r'#(\w+)'
            ],
            'date': [
                r'Clipped on:\s*(.+?)(?:\n|$)',
                r'Date:\s*(.+?)(?:\n|$)',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
        }
    
    def is_evernote_clipping(self, content: str) -> bool:
        """Check if content is an Evernote clipping."""
        content_lower = content.lower()
        
        # Check for Evernote indicators
        evernote_indicators = [
            'clipped from', 'evernote', 'web clipper', 'saved from', 
            'source:', 'original url', 'clipped on', 'tags:', 'notebook:',
            'saved with evernote', 'clipped with evernote'
        ]
        
        return any(indicator in content_lower for indicator in evernote_indicators)
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from Evernote clipping."""
        metadata = {
            'title': None,
            'url': None,
            'tags': [],
            'date': None
        }
        
        # Extract title
        for pattern in self.extraction_patterns['title']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['title'] = match.group(1).strip()
                break
        
        # Extract URL
        for pattern in self.extraction_patterns['url']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['url'] = match.group(1).strip()
                break
        
        # Extract tags
        for pattern in self.extraction_patterns['tags']:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        tags = [tag.strip() for tag in match if tag.strip()]
                    else:
                        tags = [match.strip()]
                    metadata['tags'].extend(tags)
        
        # Extract date
        for pattern in self.extraction_patterns['date']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['date'] = match.group(1).strip()
                break
        
        return metadata
    
    def clean_evernote_clipping(self, content: str, file_path: Path) -> EvernoteCleaningResult:
        """Clean and extract content from Evernote clipping."""
        if not self.is_evernote_clipping(content):
            return EvernoteCleaningResult(
                original_content=content,
                cleaned_content=content,
                extracted_title=None,
                extracted_url=None,
                extracted_tags=[],
                extracted_date=None,
                cleaning_stats={'is_evernote_clipping': False},
                is_evernote_clipping=False
            )
        
        original_length = len(content)
        cleaned_content = content
        
        # Step 1: Remove Evernote header metadata
        for pattern in self.evernote_patterns['clipping_header']:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Step 2: Remove metadata sections
        for pattern in self.evernote_patterns['metadata_sections']:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Step 3: Remove Evernote footer
        for pattern in self.evernote_patterns['evernote_footer']:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Step 4: Extract metadata before cleaning
        metadata = self.extract_metadata(content)
        
        # Step 5: Clean HTML content if present
        cleaned_content = self._clean_html_content(cleaned_content)
        
        # Step 6: Remove excessive whitespace and normalize
        cleaned_content = self._normalize_content(cleaned_content)
        
        # Step 7: Calculate cleaning statistics
        cleaning_stats = self._calculate_cleaning_stats(original_length, len(cleaned_content))
        
        return EvernoteCleaningResult(
            original_content=content,
            cleaned_content=cleaned_content,
            extracted_title=metadata['title'],
            extracted_url=metadata['url'],
            extracted_tags=metadata['tags'],
            extracted_date=metadata['date'],
            cleaning_stats=cleaning_stats,
            is_evernote_clipping=True
        )
    
    def _clean_html_content(self, content: str) -> str:
        """Clean HTML content using BeautifulSoup."""
        try:
            # Check if content contains HTML
            if '<html' in content.lower() or '<body' in content.lower():
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Remove navigation and footer elements
                for element in soup.find_all(['nav', 'footer', 'header', 'aside']):
                    element.decompose()
                
                # Remove elements with common ad/analytics classes
                for element in soup.find_all(class_=re.compile(r'(ad|ads|advertisement|analytics|tracking|social|share|comment)')):
                    element.decompose()
                
                # Extract text content
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
            else:
                return content
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return content
    
    def _normalize_content(self, content: str) -> str:
        """Normalize and clean up content."""
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove excessive spaces
        content = re.sub(r' {2,}', ' ', content)
        
        # Remove empty lines at beginning and end
        content = content.strip()
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        return content
    
    def _calculate_cleaning_stats(self, original_length: int, cleaned_length: int) -> Dict[str, Any]:
        """Calculate cleaning statistics."""
        reduction_ratio = (original_length - cleaned_length) / original_length if original_length > 0 else 0
        
        return {
            'original_length': original_length,
            'cleaned_length': cleaned_length,
            'reduction_ratio': reduction_ratio,
            'bytes_saved': original_length - cleaned_length,
            'is_evernote_clipping': True
        }
    
    def batch_clean_clippings(self, notes_data: List[Tuple[Path, str]]) -> List[EvernoteCleaningResult]:
        """Clean multiple Evernote clippings in batch."""
        results = []
        
        for file_path, content in notes_data:
            try:
                result = self.clean_evernote_clipping(content, file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error cleaning {file_path}: {e}")
                # Return original content on error
                results.append(EvernoteCleaningResult(
                    original_content=content,
                    cleaned_content=content,
                    extracted_title=None,
                    extracted_url=None,
                    extracted_tags=[],
                    extracted_date=None,
                    cleaning_stats={'error': str(e)},
                    is_evernote_clipping=False
                ))
        
        return results
    
    def get_cleaning_stats(self, results: List[EvernoteCleaningResult]) -> Dict[str, Any]:
        """Get statistics from cleaning results."""
        if not results:
            return {}
        
        total_notes = len(results)
        evernote_clippings = sum(1 for r in results if r.is_evernote_clipping)
        
        # Calculate average reduction
        reductions = [r.cleaning_stats.get('reduction_ratio', 0) for r in results if r.is_evernote_clipping]
        avg_reduction = sum(reductions) / len(reductions) if reductions else 0
        
        # Calculate total bytes saved
        total_bytes_saved = sum(r.cleaning_stats.get('bytes_saved', 0) for r in results)
        
        # Tag distribution
        all_tags = []
        for result in results:
            all_tags.extend(result.extracted_tags)
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            'total_notes': total_notes,
            'evernote_clippings': evernote_clippings,
            'clipping_percentage': evernote_clippings / total_notes if total_notes > 0 else 0,
            'average_reduction_ratio': avg_reduction,
            'total_bytes_saved': total_bytes_saved,
            'tag_distribution': tag_counts,
            'successful_cleanings': sum(1 for r in results if r.is_evernote_clipping and 'error' not in r.cleaning_stats)
        } 