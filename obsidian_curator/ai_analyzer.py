"""AI-powered content analysis using Ollama."""

import json
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import ollama
from loguru import logger

from .models import Note, QualityScore, Theme, CurationConfig


class AIAnalyzer:
    """AI-powered content analyzer using Ollama."""
    
    def __init__(self, config: CurationConfig):
        """Initialize the AI analyzer.
        
        Args:
            config: Curation configuration
        """
        self.config = config
        self.model = config.ai_model
        
        # Test connection to Ollama
        try:
            ollama.list()
            logger.info(f"Connected to Ollama, using model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise
    
    def analyze_note(self, note: Note) -> Tuple[QualityScore, List[Theme], str]:
        """Analyze a note for quality, themes, and curation decision.
        
        Args:
            note: Note to analyze
            
        Returns:
            Tuple of (quality_scores, themes, curation_reason)
        """
        logger.info(f"Analyzing note: {note.title}")
        
        try:
            # Prepare content for analysis
            analysis_content = self._prepare_analysis_content(note)
            
            # Analyze content quality
            quality_scores = self._analyze_quality(analysis_content, note)
            
            # Identify themes
            themes = self._identify_themes(analysis_content, note)
            
            # Determine curation decision
            curation_reason = self._determine_curation_decision(quality_scores, themes, note)
            
            return quality_scores, themes, curation_reason
            
        except Exception as e:
            logger.error(f"Failed to analyze note {note.title}: {e}")
            # Return default values on error
            default_scores = QualityScore(
                overall=0.5,
                relevance=0.5,
                completeness=0.5,
                credibility=0.5,
                clarity=0.5
            )
            default_themes = [Theme(name="unknown", confidence=0.5)]
            return default_scores, default_themes, f"Analysis failed: {str(e)}"
    
    def _prepare_analysis_content(self, note: Note) -> str:
        """Prepare note content for AI analysis.
        
        Args:
            note: Note to prepare
            
        Returns:
            Formatted content for analysis
        """
        # Limit content length to avoid token limits
        max_words = self.config.max_tokens // 2  # Rough estimate
        content = note.content
        
        if len(content.split()) > max_words:
            # Take first and last parts to preserve context
            words = content.split()
            first_part = ' '.join(words[:max_words//2])
            last_part = ' '.join(words[-max_words//2:])
            content = f"{first_part}\n\n[... content truncated ...]\n\n{last_part}"
        
        # Format for analysis
        analysis_content = f"""
TITLE: {note.title}
CONTENT TYPE: {note.content_type.value}
SOURCE: {note.source_url or 'Unknown'}
TAGS: {', '.join(note.tags) if note.tags else 'None'}

CONTENT:
{content}

Please analyze this content for:
1. Overall quality and usefulness
2. Relevance to infrastructure and construction professionals
3. Completeness of ideas and information
4. Credibility of source and content
5. Clarity of expression and organization
6. Main themes and topics covered
"""
        return analysis_content
    
    def _analyze_quality(self, analysis_content: str, note: Note) -> QualityScore:
        """Analyze content quality using AI.
        
        Args:
            analysis_content: Formatted content for analysis
            note: Note being analyzed
            
        Returns:
            QualityScore object
        """
        prompt = f"""
{analysis_content}

Please provide a quality assessment with scores from 0.0 to 1.0 for each category:

1. Overall Quality: How valuable and well-crafted is this content overall?
2. Relevance: How relevant is this to infrastructure and construction professionals?
3. Completeness: How complete and comprehensive are the ideas presented?
4. Credibility: How trustworthy and authoritative is the source and content?
5. Clarity: How clear, well-organized, and easy to understand is the content?

Respond with a JSON object like this:
{{
    "overall": 0.8,
    "relevance": 0.9,
    "completeness": 0.7,
    "credibility": 0.8,
    "clarity": 0.9
}}

Only provide the JSON response, no other text.
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}  # Lower temperature for more consistent scoring
            )
            
            content = response['message']['content'].strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                scores_data = json.loads(json_match.group())
                
                return QualityScore(
                    overall=float(scores_data.get('overall', 0.5)),
                    relevance=float(scores_data.get('relevance', 0.5)),
                    completeness=float(scores_data.get('completeness', 0.5)),
                    credibility=float(scores_data.get('credibility', 0.5)),
                    clarity=float(scores_data.get('clarity', 0.5))
                )
            else:
                logger.warning(f"Could not extract JSON from AI response: {content}")
                return self._default_quality_scores()
                
        except Exception as e:
            logger.error(f"Failed to analyze quality: {e}")
            return self._default_quality_scores()
    
    def _identify_themes(self, analysis_content: str, note: Note) -> List[Theme]:
        """Identify themes in the content using AI.
        
        Args:
            analysis_content: Formatted content for analysis
            note: Note being analyzed
            
        Returns:
            List of Theme objects
        """
        prompt = f"""
{analysis_content}

Please identify the main themes and topics in this content. Focus on themes relevant to infrastructure, construction, governance, and related professional fields.

For each theme, provide:
1. Theme name (e.g., "Public-Private Partnerships", "Infrastructure Resilience")
2. Confidence level (0.0 to 1.0)
3. Sub-themes (if any)
4. Keywords associated with the theme

Respond with a JSON array like this:
[
    {{
        "name": "Public-Private Partnerships",
        "confidence": 0.9,
        "subthemes": ["Financing", "Governance", "Risk Management"],
        "keywords": ["PPPs", "infrastructure", "private sector", "public sector"]
    }},
    {{
        "name": "Infrastructure Resilience",
        "confidence": 0.7,
        "subthemes": ["Climate Adaptation", "Disaster Recovery"],
        "keywords": ["resilience", "climate change", "disaster", "adaptation"]
    }}
]

Only provide the JSON response, no other text.
"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.4}
            )
            
            content = response['message']['content'].strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                themes_data = json.loads(json_match.group())
                
                themes = []
                for theme_data in themes_data:
                    theme = Theme(
                        name=theme_data.get('name', 'Unknown'),
                        confidence=float(theme_data.get('confidence', 0.5)),
                        subthemes=theme_data.get('subthemes', []),
                        keywords=theme_data.get('keywords', [])
                    )
                    themes.append(theme)
                
                return themes
            else:
                logger.warning(f"Could not extract themes JSON from AI response: {content}")
                return [self._default_theme()]
                
        except Exception as e:
            logger.error(f"Failed to identify themes: {e}")
            return [self._default_theme()]
    
    def _determine_curation_decision(self, quality_scores: QualityScore, themes: List[Theme], note: Note) -> str:
        """Determine whether to curate the note based on quality scores and themes.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            note: Note being evaluated
            
        Returns:
            Reason for curation decision
        """
        # Check quality thresholds
        quality_passed = quality_scores.overall >= self.config.quality_threshold
        relevance_passed = quality_scores.relevance >= self.config.relevance_threshold
        
        if not quality_passed and not relevance_passed:
            return f"Failed both quality ({quality_scores.overall:.2f} < {self.config.quality_threshold}) and relevance ({quality_scores.relevance:.2f} < {self.config.relevance_threshold}) thresholds"
        
        if not quality_passed:
            return f"Failed quality threshold: {quality_scores.overall:.2f} < {self.config.quality_threshold}"
        
        if not relevance_passed:
            return f"Failed relevance threshold: {quality_scores.relevance:.2f} < {self.config.relevance_threshold}"
        
        # Check if themes align with target themes
        if self.config.target_themes:
            theme_alignment = any(
                any(target in theme.name.lower() or target in theme.keywords for target in self.config.target_themes)
                for theme in themes
            )
            
            if not theme_alignment:
                return f"Content themes ({[t.name for t in themes]}) don't align with target themes ({self.config.target_themes})"
        
        # All checks passed
        return f"Passed all curation criteria: quality={quality_scores.overall:.2f}, relevance={quality_scores.relevance:.2f}"
    
    def _default_quality_scores(self) -> QualityScore:
        """Return default quality scores when AI analysis fails."""
        return QualityScore(
            overall=0.5,
            relevance=0.5,
            completeness=0.5,
            credibility=0.5,
            clarity=0.5
        )
    
    def _default_theme(self) -> Theme:
        """Return default theme when AI analysis fails."""
        return Theme(
            name="Unknown",
            confidence=0.5,
            subthemes=[],
            keywords=[]
        )
    
    def batch_analyze(self, notes: List[Note]) -> List[Tuple[Note, QualityScore, List[Theme], str]]:
        """Analyze multiple notes in batch.
        
        Args:
            notes: List of notes to analyze
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i, note in enumerate(notes):
            logger.info(f"Analyzing note {i+1}/{len(notes)}: {note.title}")
            
            try:
                quality_scores, themes, curation_reason = self.analyze_note(note)
                results.append((note, quality_scores, themes, curation_reason))
                
                # Add small delay to avoid overwhelming the AI service
                import time
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to analyze note {note.title}: {e}")
                # Add default results for failed analysis
                default_scores = self._default_quality_scores()
                default_themes = [self._default_theme()]
                results.append((note, default_scores, default_themes, f"Analysis failed: {str(e)}"))
        
        return results
