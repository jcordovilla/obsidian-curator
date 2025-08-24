"""AI-powered content classification and processing strategy determination."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import json

from loguru import logger

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available - AI content classification will be disabled")


class ContentCategory(Enum):
    """Detailed content categories for intelligent processing."""
    URL_BOOKMARK = "url_bookmark"           # Just title + URL, minimal description
    WEB_CLIPPING = "web_clipping"           # Full webpage content with navigation
    PDF_ANNOTATION = "pdf_annotation"       # PDF content + user notes
    IMAGE_ANNOTATION = "image_annotation"   # Image + explanatory text
    AUDIO_VIDEO_NOTE = "audio_video_note"   # Media file + transcript/notes
    PURE_TEXT_NOTE = "pure_text_note"       # Original writing, no external content
    MIXED_CONTENT = "mixed_content"         # Combination of multiple types
    SOCIAL_MEDIA_POST = "social_media_post" # Social media content
    ACADEMIC_PAPER = "academic_paper"       # Research papers, academic content
    CORPORATE_CONTENT = "corporate_content" # Business reports, corporate info
    NEWS_ARTICLE = "news_article"           # News content
    TECHNICAL_DOCUMENT = "technical_document" # Technical specs, manuals
    UNKNOWN = "unknown"                     # Unable to classify


@dataclass
class ContentAnalysis:
    """Result of AI content analysis."""
    category: ContentCategory
    confidence: float
    processing_strategy: str
    content_quality_score: float
    extraction_priority: List[str]
    cleaning_recommendations: List[str]
    metadata_suggestions: Dict[str, Any]
    ai_insights: str


class AIContentClassifier:
    """AI-powered content classification and processing strategy determination."""
    
    def __init__(self, 
                 model: str = "phi3:mini",
                 enable_ai: bool = True,
                 fallback_to_rules: bool = True):
        """Initialize the AI content classifier.
        
        Args:
            model: Ollama model to use for classification
            enable_ai: Whether to use AI classification
            fallback_to_rules: Whether to fall back to rule-based classification
        """
        self.model = model
        self.enable_ai = enable_ai and OLLAMA_AVAILABLE
        self.fallback_to_rules = fallback_to_rules
        
        # Initialize Ollama client if available
        self.ollama_client = None
        if self.enable_ai:
            try:
                self.ollama_client = ollama.Client()
                logger.info(f"AI content classification enabled with model: {model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama client: {e}")
                self.enable_ai = False
        
        # Rule-based classification patterns as fallback
        self.classification_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize rule-based classification patterns."""
        patterns = {
            'url_bookmark': [
                re.compile(r'^# .*\n\nhttps?://', re.MULTILINE),
                re.compile(r'^.*\n\nhttps?://[^\s]+\s*$', re.MULTILINE),
                re.compile(r'^.*\n\nwww\.[^\s]+\s*$', re.MULTILINE),
            ],
            'web_clipping': [
                re.compile(r'<div[^>]*>.*</div>', re.DOTALL),
                re.compile(r'<span[^>]*>.*</span>', re.DOTALL),
                re.compile(r'<p[^>]*>.*</p>', re.DOTALL),
                re.compile(r'Published by|By\s+[A-Z][a-z]+|Copyright\s+©', re.IGNORECASE),
            ],
            'pdf_annotation': [
                re.compile(r'!\[\[.*\.pdf\]\]', re.IGNORECASE),
                re.compile(r'\[\[.*\.pdf\]\]', re.IGNORECASE),
                re.compile(r'PDF|pdf', re.IGNORECASE),
            ],
            'image_annotation': [
                re.compile(r'!\[\[.*\.(png|jpg|jpeg|gif|svg|webp)\]\]', re.IGNORECASE),
                re.compile(r'!\[.*\]\(.*\.(png|jpg|jpeg|gif|svg|webp)\)', re.IGNORECASE),
            ],
            'audio_video_note': [
                re.compile(r'!\[\[.*\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\]\]', re.IGNORECASE),
                re.compile(r'!\[.*\]\(.*\.(mp3|mp4|wav|m4a|aac|flac|wma|ogg)\)', re.IGNORECASE),
                re.compile(r'!\[\[attachments/.*\.resources/.*\]\]', re.IGNORECASE),
            ],
            'social_media_post': [
                re.compile(r'linkedin\.com|twitter\.com|facebook\.com', re.IGNORECASE),
                re.compile(r'@\w+|#\w+', re.IGNORECASE),
                re.compile(r'Follow us|Share on|Like|Comment', re.IGNORECASE),
            ],
            'academic_paper': [
                re.compile(r'abstract|methodology|literature review|research|study', re.IGNORECASE),
                re.compile(r'doi:|journal:|conference:|proceedings:', re.IGNORECASE),
            ],
            'corporate_content': [
                re.compile(r'company|corporation|business|enterprise|organization', re.IGNORECASE),
                re.compile(r'annual report|quarterly|earnings|financial|investor', re.IGNORECASE),
            ],
            'news_article': [
                re.compile(r'reuters|afp|efe|associated press|news|breaking', re.IGNORECASE),
                re.compile(r'published|updated|reporter|journalist|correspondent', re.IGNORECASE),
            ],
            'technical_document': [
                re.compile(r'specification|technical|manual|guide|documentation', re.IGNORECASE),
                re.compile(r'api|sdk|framework|library|protocol', re.IGNORECASE),
            ]
        }
        return patterns
    
    def classify_content(self, 
                        content: str, 
                        metadata: Dict[str, Any], 
                        file_path: Path) -> ContentAnalysis:
        """Classify content using AI and determine processing strategy.
        
        Args:
            content: Raw note content
            metadata: Note metadata
            file_path: Path to the note file
            
        Returns:
            ContentAnalysis with classification and processing recommendations
        """
        if self.enable_ai and self.ollama_client:
            try:
                return self._ai_classify_content(content, metadata, file_path)
            except Exception as e:
                logger.warning(f"AI classification failed: {e}")
                if self.fallback_to_rules:
                    logger.info("Falling back to rule-based classification")
                    return self._rule_based_classify_content(content, metadata, file_path)
                else:
                    raise
        else:
            return self._rule_based_classify_content(content, metadata, file_path)
    
    def _ai_classify_content(self, 
                            content: str, 
                            metadata: Dict[str, Any], 
                            file_path: Path) -> ContentAnalysis:
        """Use AI to classify content and determine processing strategy."""
        
        # Prepare content sample for AI analysis
        content_sample = content[:2000] if len(content) > 2000 else content
        filename = file_path.name
        
        # Create comprehensive classification prompt
        prompt = f"""TASK: Analyze this note content and classify it for intelligent processing.

FILENAME: {filename}
CONTENT SAMPLE: {content_sample}

METADATA: {json.dumps(metadata, default=str)}

ANALYZE and classify this content into one of these categories:
1. URL_BOOKMARK - Just title + URL, minimal description
2. WEB_CLIPPING - Full webpage content with navigation/chrome
3. PDF_ANNOTATION - PDF content + user notes/annotations
4. IMAGE_ANNOTATION - Image + explanatory text
5. AUDIO_VIDEO_NOTE - Media file + transcript/notes
6. PURE_TEXT_NOTE - Original writing, no external content
7. MIXED_CONTENT - Combination of multiple types
8. SOCIAL_MEDIA_POST - Social media content
9. ACADEMIC_PAPER - Research papers, academic content
10. CORPORATE_CONTENT - Business reports, corporate info
11. NEWS_ARTICLE - News content
12. TECHNICAL_DOCUMENT - Technical specs, manuals

RESPOND in this exact JSON format:
{{
    "category": "category_name",
    "confidence": 0.95,
    "processing_strategy": "detailed description of how to process",
    "content_quality_score": 0.85,
    "extraction_priority": ["priority1", "priority2"],
    "cleaning_recommendations": ["recommendation1", "recommendation2"],
    "metadata_suggestions": {{"key": "value"}},
    "ai_insights": "Brief explanation of classification decision"
}}

Focus on infrastructure, business, and professional content relevance."""

        try:
            response = self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 800,
                    "stop": []
                }
            )
            
            ai_response = response.get('response', '').strip()
            
            # Try to extract JSON from response
            try:
                # Find JSON in the response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    analysis_data = json.loads(json_str)
                    
                    # Validate and create ContentAnalysis object
                    return self._create_content_analysis(analysis_data)
                else:
                    raise ValueError("No JSON found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Raw AI response: {ai_response}")
                # Fall back to rule-based classification
                return self._rule_based_classify_content(content, metadata, file_path)
                
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return self._rule_based_classify_content(content, metadata, file_path)
    
    def _rule_based_classify_content(self, 
                                   content: str, 
                                   metadata: Dict[str, Any], 
                                   file_path: Path) -> ContentAnalysis:
        """Fallback rule-based content classification."""
        
        # Score each category based on pattern matches
        category_scores = {}
        
        for category, patterns in self.classification_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(content)
                score += len(matches) * 0.3  # Weight for pattern matches
            
            # Additional heuristics
            if category == 'url_bookmark':
                # Check if content is very short with URL
                if len(content.strip()) < 300 and re.search(r'https?://', content):
                    score += 2.0
            elif category == 'web_clipping':
                # Check for HTML structure
                html_tags = len(re.findall(r'<[^>]+>', content))
                if html_tags > 5:
                    score += 1.5
            elif category == 'pure_text_note':
                # Check if content is substantial without external references
                if len(content.strip()) > 500 and not re.search(r'https?://|!\[\[|\[\[', content):
                    score += 1.0
            
            category_scores[category] = score
        
        # Find best category
        best_category = max(category_scores.items(), key=lambda x: x[1])
        category_name = best_category[0]
        confidence = min(0.9, best_category[1] / 3.0)  # Normalize confidence
        
        # Create processing strategy based on category
        strategy = self._get_processing_strategy(category_name, content, metadata)
        
        return ContentAnalysis(
            category=ContentCategory(category_name),
            confidence=confidence,
            processing_strategy=strategy,
            content_quality_score=0.7,  # Default for rule-based
            extraction_priority=["content", "metadata"],
            cleaning_recommendations=["basic_cleaning"],
            metadata_suggestions={},
            ai_insights=f"Rule-based classification: {category_name} (confidence: {confidence:.2f})"
        )
    
    def _create_content_analysis(self, analysis_data: Dict[str, Any]) -> ContentAnalysis:
        """Create ContentAnalysis object from AI response data."""
        try:
            # Normalize category name to lowercase for enum matching
            category_name = analysis_data.get('category', 'unknown')
            if isinstance(category_name, str):
                category_name = category_name.lower()
            
            # Try to create the category, with fallback to UNKNOWN
            try:
                category = ContentCategory(category_name)
            except ValueError:
                # If the exact name doesn't match, try to find a close match
                category = self._find_closest_category(category_name)
            
            confidence = float(analysis_data.get('confidence', 0.5))
            processing_strategy = str(analysis_data.get('processing_strategy', ''))
            content_quality_score = float(analysis_data.get('content_quality_score', 0.7))
            extraction_priority = list(analysis_data.get('extraction_priority', []))
            cleaning_recommendations = list(analysis_data.get('cleaning_recommendations', []))
            metadata_suggestions = dict(analysis_data.get('metadata_suggestions', {}))
            ai_insights = str(analysis_data.get('ai_insights', ''))
            
            return ContentAnalysis(
                category=category,
                confidence=confidence,
                processing_strategy=processing_strategy,
                content_quality_score=content_quality_score,
                extraction_priority=extraction_priority,
                cleaning_recommendations=cleaning_recommendations,
                metadata_suggestions=metadata_suggestions,
                ai_insights=ai_insights
            )
            
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Failed to create ContentAnalysis from AI data: {e}")
            # Return default analysis
            return ContentAnalysis(
                category=ContentCategory.UNKNOWN,
                confidence=0.5,
                processing_strategy="standard_processing",
                content_quality_score=0.5,
                extraction_priority=["content"],
                cleaning_recommendations=["basic_cleaning"],
                metadata_suggestions={},
                ai_insights=f"Failed to parse AI response: {e}"
            )
    
    def _find_closest_category(self, category_name: str) -> ContentCategory:
        """Find the closest matching content category."""
        # Normalize the input
        category_name = category_name.lower().replace('_', '').replace('-', '')
        
        # Define category mappings for common variations
        category_mappings = {
            'urlbookmark': ContentCategory.URL_BOOKMARK,
            'webclipping': ContentCategory.WEB_CLIPPING,
            'pdfannotation': ContentCategory.PDF_ANNOTATION,
            'imageannotation': ContentCategory.IMAGE_ANNOTATION,
            'audiovideonote': ContentCategory.AUDIO_VIDEO_NOTE,
            'puretextnote': ContentCategory.PURE_TEXT_NOTE,
            'mixedcontent': ContentCategory.MIXED_CONTENT,
            'socialmediapost': ContentCategory.SOCIAL_MEDIA_POST,
            'academicpaper': ContentCategory.ACADEMIC_PAPER,
            'corporatecontent': ContentCategory.CORPORATE_CONTENT,
            'newsarticle': ContentCategory.NEWS_ARTICLE,
            'technicaldocument': ContentCategory.TECHNICAL_DOCUMENT,
        }
        
        # Try exact match first
        if category_name in category_mappings:
            return category_mappings[category_name]
        
        # Try partial matches
        for key, category in category_mappings.items():
            if key in category_name or category_name in key:
                return category
        
        # Default to UNKNOWN
        return ContentCategory.UNKNOWN
    
    def _get_processing_strategy(self, 
                                category: str, 
                                content: str, 
                                metadata: Dict[str, Any]) -> str:
        """Get processing strategy based on content category."""
        
        strategies = {
            'url_bookmark': 'extract_title_and_url_only',
            'web_clipping': 'aggressive_web_cleaning_with_ai_validation',
            'pdf_annotation': 'preserve_both_pdf_and_annotations',
            'image_annotation': 'extract_image_reference_and_text',
            'audio_video_note': 'extract_media_reference_and_notes',
            'pure_text_note': 'minimal_cleaning_preserve_structure',
            'mixed_content': 'separate_and_process_each_type',
            'social_media_post': 'extract_post_content_remove_platform_chrome',
            'academic_paper': 'preserve_academic_structure_remove_formatting',
            'corporate_content': 'extract_business_content_remove_marketing',
            'news_article': 'extract_article_remove_navigation',
            'technical_document': 'preserve_technical_structure_clean_formatting'
        }
        
        return strategies.get(category, 'standard_processing')
    
    def get_processing_pipeline(self, analysis: ContentAnalysis) -> Dict[str, Any]:
        """Get the recommended processing pipeline based on content analysis."""
        
        pipelines = {
            'extract_title_and_url_only': {
                'extract_linked_content': False,
                'clean_html': False,
                'preserve_metadata': True,
                'content_cleaning_level': 'minimal',
                'ai_enhancement': False
            },
            'aggressive_web_cleaning_with_ai_validation': {
                'extract_linked_content': True,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'aggressive',
                'ai_enhancement': True,
                'web_content_validation': True
            },
            'preserve_both_pdf_and_annotations': {
                'extract_linked_content': True,
                'clean_html': False,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'separate_pdf_and_notes': True
            },
            'extract_image_reference_and_text': {
                'extract_linked_content': True,
                'clean_html': False,
                'preserve_metadata': True,
                'content_cleaning_level': 'minimal',
                'ai_enhancement': False
            },
            'extract_media_reference_and_notes': {
                'extract_linked_content': True,
                'clean_html': False,
                'preserve_metadata': True,
                'content_cleaning_level': 'minimal',
                'ai_enhancement': False
            },
            'minimal_cleaning_preserve_structure': {
                'extract_linked_content': False,
                'clean_html': False,
                'preserve_metadata': True,
                'content_cleaning_level': 'minimal',
                'ai_enhancement': False
            },
            'separate_and_process_each_type': {
                'extract_linked_content': True,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'adaptive',
                'ai_enhancement': True,
                'mixed_content_handling': True
            },
            'extract_post_content_remove_platform_chrome': {
                'extract_linked_content': False,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'social_media_cleaning': True
            },
            'preserve_academic_structure_remove_formatting': {
                'extract_linked_content': False,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'academic_structure_preservation': True
            },
            'extract_business_content_remove_marketing': {
                'extract_linked_content': False,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'business_content_extraction': True
            },
            'extract_article_remove_navigation': {
                'extract_linked_content': False,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'news_content_extraction': True
            },
            'preserve_technical_structure_clean_formatting': {
                'extract_linked_content': False,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False,
                'technical_structure_preservation': True
            },
            'standard_processing': {
                'extract_linked_content': True,
                'clean_html': True,
                'preserve_metadata': True,
                'content_cleaning_level': 'moderate',
                'ai_enhancement': False
            }
        }
        
        return pipelines.get(analysis.processing_strategy, pipelines['standard_processing'])
    
    def validate_content_quality(self, 
                                content: str, 
                                analysis: ContentAnalysis) -> Tuple[bool, str]:
        """Validate if content meets quality standards for the identified category.
        
        Args:
            content: Processed content to validate
            analysis: Content analysis result
            
        Returns:
            Tuple of (is_quality_content, reason)
        """
        
        if not content or len(content.strip()) < 50:
            return False, "Content too short or empty"
        
        # Category-specific quality checks
        if analysis.category == ContentCategory.URL_BOOKMARK:
            # URL bookmarks should have clear title and URL
            if not re.search(r'https?://', content):
                return False, "URL bookmark missing URL"
            if len(content.strip()) > 500:
                return False, "URL bookmark too verbose"
                
        elif analysis.category == ContentCategory.WEB_CLIPPING:
            # Web clippings should have substantial content
            words = content.split()
            if len(words) < 100:
                return False, "Web clipping too short"
            
            # Check for excessive navigation artifacts
            navigation_indicators = ['menu', 'navigation', 'footer', 'header', 'sidebar']
            nav_count = sum(1 for word in words if word.lower() in navigation_indicators)
            if nav_count > len(words) * 0.1:  # More than 10% navigation
                return False, "Web clipping contains too many navigation elements"
                
        elif analysis.category == ContentCategory.PDF_ANNOTATION:
            # PDF annotations should have both PDF content and user notes
            if not re.search(r'pdf|PDF', content, re.IGNORECASE):
                return False, "PDF annotation missing PDF reference"
            if len(content.strip()) < 200:
                return False, "PDF annotation too short"
                
        elif analysis.category == ContentCategory.PURE_TEXT_NOTE:
            # Pure text notes should have substantial original content
            if len(content.strip()) < 300:
                return False, "Pure text note too short"
            
            # Check for repetitive or template content
            lines = content.split('\n')
            unique_lines = set(line.strip() for line in lines if line.strip())
            if len(unique_lines) < len(lines) * 0.5:  # Too much repetition
                return False, "Pure text note contains too much repetitive content"
        
        # General quality checks
        if analysis.content_quality_score < 0.3:
            return False, f"Content quality score too low: {analysis.content_quality_score}"
        
        return True, "Content meets quality standards"
