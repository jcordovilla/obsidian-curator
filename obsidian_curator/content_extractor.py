"""Content extraction utilities for PDFs, images, and URLs."""

import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
import requests
from PIL import Image
import fitz  # PyMuPDF
from loguru import logger

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available - image OCR will be disabled")


class ContentExtractor:
    """Extracts content from various sources including PDFs, images, and URLs."""
    
    def __init__(self, 
                 max_pdf_pages: int = 100,  # Increased from 50 to 100
                 max_url_content_length: int = 50000,
                 request_timeout: int = 5,  # Reduced from 10 to 5 seconds
                 max_urls_per_note: int = 2,
                 intelligent_extraction: bool = True,
                 ai_model: str = None):
        """Initialize the content extractor.
        
        Args:
            max_pdf_pages: Maximum number of PDF pages to process
            max_url_content_length: Maximum characters to extract from URLs
            request_timeout: Timeout for HTTP requests in seconds
            max_urls_per_note: Maximum number of URLs to process per note
            intelligent_extraction: Use AI to filter and summarize extracted content
            ai_model: AI model to use for intelligent extraction (if None, uses raw extraction)
        """
        self.max_pdf_pages = max_pdf_pages
        self.max_url_content_length = max_url_content_length
        self.request_timeout = request_timeout
        self.max_urls_per_note = max_urls_per_note
        self.intelligent_extraction = intelligent_extraction
        self.ai_model = ai_model
        
        # Configure requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Obsidian-Curator) Content Extractor'
        })
        
        # Initialize AI client for intelligent extraction
        self.ollama_client = None
        if self.intelligent_extraction and self.ai_model:
            try:
                import ollama
                self.ollama_client = ollama.Client()
                logger.info(f"Intelligent extraction enabled with model: {self.ai_model}")
            except ImportError:
                logger.warning("Ollama not available - falling back to raw extraction")
                self.intelligent_extraction = False
    
    def extract_pdf_content(self, pdf_path: Path, vault_root: Path) -> Optional[str]:
        """Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to PDF file (can be relative to vault root)
            vault_root: Root path of the vault for resolving relative paths
            
        Returns:
            Extracted text content or None if extraction fails
        """
        # Resolve PDF path
        if not pdf_path.is_absolute():
            resolved_path = vault_root / pdf_path
        else:
            resolved_path = pdf_path
            
        if not resolved_path.exists():
            logger.warning(f"PDF file not found: {resolved_path}")
            return None
            
        try:
            logger.info(f"Extracting content from PDF: {resolved_path}")
            
            with fitz.open(resolved_path) as doc:
                text_content = []
                pages_processed = 0
                
                # Process all pages if max_pdf_pages is 0 or negative, otherwise respect limit
                max_pages = len(doc) if self.max_pdf_pages <= 0 else min(len(doc), self.max_pdf_pages)
                for page_num in range(max_pages):
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        text_content.append(f"## Page {page_num + 1}\n\n{page_text.strip()}")
                        pages_processed += 1
                
                if text_content:
                    full_text = "\n\n".join(text_content)
                    logger.info(f"Extracted {len(full_text)} characters from {pages_processed} pages")
                    return full_text
                else:
                    logger.warning(f"No extractable text found in PDF: {resolved_path}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to extract PDF content from {resolved_path}: {e}")
            return None
    
    def extract_image_content(self, image_path: Path, vault_root: Path) -> Optional[str]:
        """Extract text content from an image using OCR.
        
        Args:
            image_path: Path to image file
            vault_root: Root path of the vault for resolving relative paths
            
        Returns:
            Extracted text content or None if extraction fails
        """
        if not TESSERACT_AVAILABLE:
            logger.warning("OCR not available - skipping image content extraction")
            return None
            
        # Resolve image path
        if not image_path.is_absolute():
            resolved_path = vault_root / image_path
        else:
            resolved_path = image_path
            
        if not resolved_path.exists():
            logger.warning(f"Image file not found: {resolved_path}")
            return None
            
        try:
            logger.info(f"Extracting content from image: {resolved_path}")
            
            with Image.open(resolved_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Extract text using OCR
                extracted_text = pytesseract.image_to_string(img)
                
                if extracted_text.strip():
                    logger.info(f"Extracted {len(extracted_text)} characters from image")
                    return f"## Image Content\n\n{extracted_text.strip()}"
                else:
                    logger.info("No text detected in image")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to extract image content from {resolved_path}: {e}")
            return None
    
    def extract_url_content(self, url: str) -> Optional[str]:
        """Extract content from a URL.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted content or None if extraction fails
        """
        try:
            logger.info(f"Extracting content from URL: {url}")
            
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            
            # Basic HTML content extraction
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Try to find main content
            main_content = None
            for selector in ['article', 'main', '.content', '.post', '.entry']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Extract text
            content_text = main_content.get_text(separator='\n', strip=True)
            
            # Limit content length
            if len(content_text) > self.max_url_content_length:
                content_text = content_text[:self.max_url_content_length] + "\n\n[... content truncated ...]"
            
            if content_text.strip():
                logger.info(f"Extracted {len(content_text)} characters from URL")
                return f"## Web Content\n\n{content_text.strip()}"
            else:
                logger.warning("No content extracted from URL")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract content from URL {url}: {e}")
            return None
    
    def find_linked_content(self, content: str, vault_root: Path) -> Dict[str, str]:
        """Find and extract content from linked files and URLs in note content.
        
        Args:
            content: Note content to scan for links
            vault_root: Root path of the vault
            
        Returns:
            Dictionary mapping link types to extracted content
        """
        extracted_content = {}
        
        # Find PDF links
        pdf_patterns = [
            r'!\[\[([^]]+\.pdf)\]\]',  # Obsidian PDF embeds
            r'\[\[([^]]+\.pdf)\]\]',   # Obsidian PDF links
            r'([^)\s]+\.pdf)',         # Direct PDF references
        ]
        
        for pattern in pdf_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                pdf_path = Path(match)
                pdf_content = self.extract_pdf_content(pdf_path, vault_root)
                if pdf_content:
                    # Include the original link reference in the extracted content
                    original_link = f"[[{match}]]" if "[[" not in match else match
                    extracted_content[f"PDF: {pdf_path.name}"] = f"**Document Link:** {original_link}\n\n**Content:**\n{pdf_content}"
        
        # Find image links
        image_patterns = [
            r'!\[\[([^]]+\.(png|jpg|jpeg|gif|bmp|tiff))\]\]',  # Obsidian image embeds
            r'!\[.*?\]\(([^)]+\.(png|jpg|jpeg|gif|bmp|tiff))\)',  # Markdown images
        ]
        
        for pattern in image_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                image_path = Path(match[0] if isinstance(match, tuple) else match)
                image_content = self.extract_image_content(image_path, vault_root)
                if image_content:
                    extracted_content[f"Image: {image_path.name}"] = image_content
        
        # Find URLs
        url_patterns = [
            r'<(https?://[^>]+)>',  # Angle bracket URLs
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # Direct URLs
        ]
        
        urls_found = set()
        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                if url not in urls_found and len(urls_found) < self.max_urls_per_note:
                    urls_found.add(url)
                    try:
                        url_content = self.extract_url_content(url)
                        if url_content:
                            extracted_content[f"URL: {urlparse(url).netloc}"] = url_content
                    except Exception as e:
                        logger.warning(f"Failed to extract URL content from {url}: {e}")
                        continue  # Skip this URL and try the next one
        
        return extracted_content
    
    def enhance_note_content(self, original_content: str, vault_root: Path) -> str:
        """Enhance note content by extracting linked content.
        
        Args:
            original_content: Original note content
            vault_root: Root path of the vault
            
        Returns:
            Enhanced content with extracted linked content
        """
        # Find and extract linked content
        extracted_content = self.find_linked_content(original_content, vault_root)
        
        if not extracted_content:
            return original_content
        
        # Use intelligent extraction if enabled
        if self.intelligent_extraction and self.ollama_client:
            curated_extracts = self._curate_extracted_content(original_content, extracted_content)
            if not curated_extracts:
                return original_content
                
            enhanced_parts = [original_content]
            enhanced_parts.append("\n\n---\n\n# Relevant Extracted Content")
            
            for source, content in curated_extracts.items():
                enhanced_parts.append(f"\n\n## From {source}\n\n{content}")
        else:
            # Fallback to raw extraction (original behavior)
            enhanced_parts = [original_content]
            enhanced_parts.append("\n\n---\n\n# Extracted Content")
            for source, content in extracted_content.items():
                enhanced_parts.append(f"\n\n## From {source}\n\n{content}")
        
        enhanced_content = "\n".join(enhanced_parts)
        
        logger.info(f"Enhanced content: {len(original_content)} → {len(enhanced_content)} characters")
        return enhanced_content
    
    def _curate_extracted_content(self, original_content: str, extracted_content: Dict[str, str]) -> Dict[str, str]:
        """Use AI to curate and filter extracted content for relevance and value.
        
        Args:
            original_content: The original note content for context
            extracted_content: Raw extracted content from various sources
            
        Returns:
            Dictionary of curated content that adds value to the original note
        """
        if not self.ollama_client or not extracted_content:
            return {}
            
        curated_extracts = {}
        
        for source, raw_content in extracted_content.items():
            try:
                # Determine content type for better prompting
                is_pdf = source.startswith("PDF:")
                is_image = source.startswith("Image:")
                is_url = source.startswith("URL:")
                
                # Create tailored prompt based on content type
                if is_pdf:
                    curation_prompt = f"""You are helping curate PDF document content for infrastructure professionals. 

ORIGINAL NOTE CONTENT:
{original_content[:1000]}...

EXTRACTED PDF CONTENT FROM {source}:
{raw_content[:3000]}...

This PDF content is being evaluated for inclusion in a professional infrastructure note. Consider that infrastructure encompasses: transport, energy, water, digital, construction, engineering, sustainability, climate, governance, and related professional topics.

For PDFs, be INCLUSIVE and consider valuable:
1. Technical reports, policy documents, industry analysis
2. Infrastructure project information, case studies, best practices  
3. Engineering specifications, standards, guidance documents
4. Market analysis, financial models, regulatory information
5. Research findings, innovation, technology developments
6. Professional development content, training materials

ONLY reject if the content is clearly:
- Personal/private information with no professional relevance
- Completely unrelated to infrastructure, engineering, or professional practice
- Purely administrative (meeting minutes, contact lists, etc.)
- Duplicate of information already in the original note

If valuable, provide:
- ALWAYS preserve the document link (if present)
- A professional summary focusing on key insights (max 400 words)
- Highlight main findings, recommendations, or actionable information

Response:"""
                else:
                    curation_prompt = f"""You are helping curate extracted content for a professional note. 

ORIGINAL NOTE CONTENT:
{original_content[:1000]}...

EXTRACTED CONTENT FROM {source}:
{raw_content[:2000]}...

Please analyze if this extracted content adds significant value to the original note. Consider:
1. Does it provide new, relevant information not in the original?
2. Is it professionally valuable for infrastructure/construction professionals?
3. Does it contain actionable insights, data, or important context?
4. Is the content substantive (not just metadata, headers, or formatting)?

If valuable, provide a clean, concise summary of the key information (max 300 words).
If not valuable, respond with "NOT_RELEVANT".

Response:"""

                # Adjust token limit based on content type
                max_tokens = 800 if is_pdf else 500
                
                response = self.ollama_client.generate(
                    model=self.ai_model,
                    prompt=curation_prompt,
                    options={"temperature": 0.1, "num_predict": max_tokens, "stop": []}
                )
                
                ai_response = response.get('response', '').strip()
                
                if ai_response and ai_response != "NOT_RELEVANT" and len(ai_response) > 50:
                    curated_extracts[source] = ai_response
                    logger.info(f"AI curated content from {source}: {len(ai_response)} chars")
                else:
                    logger.info(f"AI determined content from {source} not relevant")
                    
            except Exception as e:
                logger.warning(f"AI curation failed for {source}: {e}")
                # Fallback: include if content seems substantial
                if len(raw_content.strip()) > 200:
                    curated_extracts[source] = raw_content[:500] + "..."
        
        return curated_extracts
