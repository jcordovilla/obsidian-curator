"""AI-powered content analysis using Ollama."""

import json
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import ollama
from loguru import logger

from .models import Note, QualityScore, Theme, ContentStructure, CurationConfig


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

    def _chat_json(self, system_prompt: str, prompt: str, temperature: float = 0.1) -> Any:
        """Call Ollama chat API requesting JSON output."""
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": temperature},
        )
        content = response["message"]["content"].strip()
        return json.loads(content)
    
    def analyze_note(self, note: Note) -> Tuple[QualityScore, List[Theme], ContentStructure, str]:
        """Analyze a note for quality, themes, content structure, and curation decision.
        
        Args:
            note: Note to analyze
            
        Returns:
            Tuple of (quality_scores, themes, content_structure, curation_reason)
        """
        logger.info(f"Analyzing note: {note.title}")
        
        try:
            # Prepare content for analysis
            analysis_content = self._prepare_analysis_content(note)
            
            # Combined analysis in single AI call for better performance
            quality_scores, themes = self._combined_analysis(analysis_content, note)
            
            # Analyze content structure (NEW - targeting 90% accuracy)
            content_structure = self._analyze_content_structure(analysis_content, note)
            
            # Determine curation decision
            curation_reason = self._determine_curation_decision(quality_scores, themes, note)
            
            return quality_scores, themes, content_structure, curation_reason
            
        except Exception as e:
            logger.error(f"Failed to analyze note {note.title}: {e}")
            # Return default values on error
            default_scores = QualityScore(
                overall=0.5,
                relevance=0.5,
                completeness=0.5,
                credibility=0.5,
                clarity=0.5,
                analytical_depth=0.5,
                evidence_quality=0.5,
                critical_thinking=0.5,
                argument_structure=0.5,
                practical_value=0.5
            )
            default_themes = [Theme(
                name="unknown", 
                confidence=0.5,
                expertise_level="intermediate",
                content_category="technical",
                business_value="operational"
            )]
            default_structure = self._default_content_structure()
            return default_scores, default_themes, default_structure, f"Analysis failed: {str(e)}"
    
    def _prepare_analysis_content(self, note: Note) -> str:
        """Prepare note content for AI analysis.
        
        Args:
            note: Note to prepare
            
        Returns:
            Formatted content for analysis
        """
        # Intelligent content preparation for analysis
        content = note.content
        max_tokens = self.config.max_tokens
        
        # For very long content, create an intelligent summary instead of truncation
        words = content.split()
        if len(words) > max_tokens // 2:  # More generous limit for comprehensive analysis
            # Keep beginning and end, plus extract key sections
            beginning = ' '.join(words[:max_tokens // 4])
            ending = ' '.join(words[-max_tokens // 4:])
            
            # Try to extract key sections (headings, important paragraphs)
            key_sections = self._extract_key_sections(content, max_tokens // 4)
            
            content = f"{beginning}\n\n[... content summary ...]\n{key_sections}\n\n[... content continued ...]\n{ending}"
        
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
    
    def _extract_key_sections(self, content: str, max_words: int) -> str:
        """Extract key sections from content for analysis.
        
        Args:
            content: Full content to extract from
            max_words: Maximum words to extract
            
        Returns:
            Key sections content
        """
        lines = content.split('\n')
        key_lines = []
        word_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Prioritize headings, bullet points, and substantive paragraphs
            is_important = (
                line.startswith('#') or  # Headings
                line.startswith('- ') or line.startswith('* ') or  # Bullet points
                len(line.split()) > 10  # Substantive paragraphs
            )
            
            if is_important:
                line_words = len(line.split())
                if word_count + line_words <= max_words:
                    key_lines.append(line)
                    word_count += line_words
                else:
                    break
        
        return '\n'.join(key_lines) if key_lines else ""
    
    def _combined_analysis(self, analysis_content: str, note: Note) -> Tuple[QualityScore, List[Theme]]:
        """Combined quality and theme analysis in a single AI call for better performance.
        
        Args:
            analysis_content: Formatted content for analysis
            note: Note being analyzed
            
        Returns:
            Tuple of (QualityScore, List[Theme])
        """
        # Create system prompt with reasoning level
        system_prompt = f"""You are an expert content analyst specializing in infrastructure and construction content. Use {self.config.reasoning_level} reasoning to provide accurate, consistent quality assessments and theme identification."""
        
        prompt = f"""
{analysis_content}

Please provide a comprehensive professional writing quality assessment AND theme identification for this content.

1. PROFESSIONAL QUALITY ASSESSMENT - Provide scores from 0.0 to 1.0 for each category:

   CORE QUALITY METRICS:
   - Overall Quality: How valuable and well-crafted is this content overall?
   - Relevance: How relevant is this to infrastructure and construction professionals?
   - Completeness: How complete and comprehensive are the ideas presented?
   - Credibility: How trustworthy and authoritative is the source and content?
   - Clarity: How clear, well-organized, and easy to understand is the content?

   PROFESSIONAL WRITING METRICS (NEW - Target 90% accuracy):
   - Analytical Depth: How sophisticated and complex are the arguments? (0.1=simple fact, 0.9=multi-perspective analysis)
   - Evidence Quality: How strong are the data, studies, and references? (0.1=unsupported claims, 0.9=well-cited research)
   - Critical Thinking: How much does it challenge assumptions and provide critical perspective? (0.1=descriptive, 0.9=challenging conventional wisdom)
   - Argument Structure: How logical and coherent is the argument flow? (0.1=disorganized, 0.9=clear problem→analysis→conclusion)
   - Practical Value: How actionable and practically useful are the insights? (0.1=theoretical, 0.9=immediate practical application)

2. ENHANCED THEME IDENTIFICATION - Identify themes with professional insight classification:
   - Focus on infrastructure, construction, governance themes
   - For each theme, provide:
     * name, confidence (0.0-1.0), subthemes, keywords
     * expertise_level: "entry", "intermediate", "expert", or "thought_leader"
     * content_category: "strategic", "tactical", "policy", "technical", or "operational"
     * business_value: "operational", "strategic", "governance", or "innovation"

Respond with a JSON object like this:
{{
    "quality": {{
        "overall": 0.8,
        "relevance": 0.9,
        "completeness": 0.7,
        "credibility": 0.8,
        "clarity": 0.9,
        "analytical_depth": 0.8,
        "evidence_quality": 0.7,
        "critical_thinking": 0.9,
        "argument_structure": 0.8,
        "practical_value": 0.8
    }},
    "themes": [
        {{
            "name": "Infrastructure Governance",
            "confidence": 0.9,
            "subthemes": ["PPPs", "Regulation"],
            "keywords": ["governance", "policy", "regulation"],
            "expertise_level": "expert",
            "content_category": "strategic",
            "business_value": "governance"
        }}
    ]
}}

Only provide the JSON response, no other text.
"""
        
        try:
            response_data = self._chat_json(system_prompt, prompt, temperature=0.15)

            # Parse quality scores with new professional writing metrics
            quality_data = response_data.get("quality", {})
            quality_scores = QualityScore(
                overall=float(quality_data.get("overall", 0.5)),
                relevance=float(quality_data.get("relevance", 0.5)),
                completeness=float(quality_data.get("completeness", 0.5)),
                credibility=float(quality_data.get("credibility", 0.5)),
                clarity=float(quality_data.get("clarity", 0.5)),
                analytical_depth=float(quality_data.get("analytical_depth", 0.5)),
                evidence_quality=float(quality_data.get("evidence_quality", 0.5)),
                critical_thinking=float(quality_data.get("critical_thinking", 0.5)),
                argument_structure=float(quality_data.get("argument_structure", 0.5)),
                practical_value=float(quality_data.get("practical_value", 0.5)),
            )

            themes_data = response_data.get("themes", [])
            themes: List[Theme] = []
            for theme_data in themes_data:
                theme = Theme(
                    name=theme_data.get("name", "Unknown"),
                    confidence=float(theme_data.get("confidence", 0.5)),
                    subthemes=theme_data.get("subthemes", []),
                    keywords=theme_data.get("keywords", []),
                    expertise_level=theme_data.get("expertise_level", "intermediate"),
                    content_category=theme_data.get("content_category", "technical"),
                    business_value=theme_data.get("business_value", "operational"),
                )
                themes.append(theme)

            if not themes:
                themes = [self._default_theme()]

            return quality_scores, themes
        except Exception as e:
            logger.error(f"Failed to perform combined analysis: {e}")
            return self._default_quality_scores(), [self._default_theme()]
    
    def _analyze_quality(self, analysis_content: str, note: Note) -> QualityScore:
        """Analyze content quality using AI.
        
        Args:
            analysis_content: Formatted content for analysis
            note: Note being analyzed
            
        Returns:
            QualityScore object
        """
        # Create system prompt with reasoning level
        system_prompt = f"""You are an expert content analyst specializing in infrastructure and construction content. Use {self.config.reasoning_level} reasoning to provide accurate, consistent quality assessments."""
        
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
            scores_data = self._chat_json(system_prompt, prompt, temperature=0.1)
            return QualityScore(
                overall=float(scores_data.get("overall", 0.5)),
                relevance=float(scores_data.get("relevance", 0.5)),
                completeness=float(scores_data.get("completeness", 0.5)),
                credibility=float(scores_data.get("credibility", 0.5)),
                clarity=float(scores_data.get("clarity", 0.5)),
            )
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
        # Create system prompt with reasoning level
        system_prompt = f"""You are an expert thematic analyst specializing in infrastructure, construction, and governance content. Use {self.config.reasoning_level} reasoning to identify relevant themes accurately and consistently."""
        
        prompt = f"""
{analysis_content}

Please identify the main themes and topics in this content with professional insight classification. Focus on themes relevant to infrastructure, construction, governance, and related professional fields.

For each theme, provide:
1. Theme name (e.g., "Public-Private Partnerships", "Infrastructure Resilience")
2. Confidence level (0.0 to 1.0)
3. Sub-themes (if any)
4. Keywords associated with the theme
5. Expertise level: "entry", "intermediate", "expert", or "thought_leader"
6. Content category: "strategic", "tactical", "policy", "technical", or "operational"
7. Business value: "operational", "strategic", "governance", or "innovation"

Respond with a JSON array like this:
[
    {{
        "name": "Public-Private Partnerships",
        "confidence": 0.9,
        "subthemes": ["Financing", "Governance", "Risk Management"],
        "keywords": ["PPPs", "infrastructure", "private sector", "public sector"],
        "expertise_level": "expert",
        "content_category": "strategic",
        "business_value": "governance"
    }},
    {{
        "name": "Infrastructure Resilience",
        "confidence": 0.7,
        "subthemes": ["Climate Adaptation", "Disaster Recovery"],
        "keywords": ["resilience", "climate change", "disaster", "adaptation"],
        "expertise_level": "intermediate",
        "content_category": "technical",
        "business_value": "operational"
    }}
]

Only provide the JSON response, no other text.
"""
        
        try:
            themes_data = self._chat_json(system_prompt, prompt, temperature=0.2)

            themes: List[Theme] = []
            for theme_data in themes_data:
                theme = Theme(
                    name=theme_data.get("name", "Unknown"),
                    confidence=float(theme_data.get("confidence", 0.5)),
                    subthemes=theme_data.get("subthemes", []),
                    keywords=theme_data.get("keywords", []),
                    expertise_level=theme_data.get("expertise_level", "intermediate"),
                    content_category=theme_data.get("content_category", "technical"),
                    business_value=theme_data.get("business_value", "operational"),
                )
                themes.append(theme)

            return themes
        except Exception as e:
            logger.error(f"Failed to identify themes: {e}")
            return [self._default_theme()]
    
    def _analyze_content_structure(self, analysis_content: str, note: Note) -> ContentStructure:
        """Analyze content structure and logical flow using AI.
        
        Args:
            analysis_content: Formatted content for analysis
            note: Note being analyzed
            
        Returns:
            ContentStructure object with structural analysis
        """
        system_prompt = f"""You are an expert content structure analyst specializing in professional writing. Use {self.config.reasoning_level} reasoning to analyze the logical flow and argument structure of content."""
        
        prompt = f"""
{analysis_content}

Please analyze the STRUCTURE and LOGICAL FLOW of this content for professional writing quality.

Evaluate the following structural elements (provide boolean true/false):
1. Has Clear Problem: Does the content clearly identify a problem, question, or challenge?
2. Has Evidence: Does the content provide supporting evidence, data, or references?
3. Has Multiple Perspectives: Does the content consider multiple viewpoints or approaches?
4. Has Actionable Conclusions: Does the content provide actionable insights or recommendations?

Also provide quality scores (0.0-1.0) for:
- Logical Flow Score: How well does the content progress logically from start to finish?
- Argument Coherence: How consistent and coherent are the arguments presented?
- Conclusion Strength: How strong and valid are the conclusions drawn?

Respond with a JSON object like this:
{{
    "has_clear_problem": true,
    "has_evidence": true,
    "has_multiple_perspectives": false,
    "has_actionable_conclusions": true,
    "logical_flow_score": 0.8,
    "argument_coherence": 0.7,
    "conclusion_strength": 0.9
}}

Only provide the JSON response, no other text.
"""
        
        try:
            structure_data = self._chat_json(system_prompt, prompt, temperature=0.1)

            return ContentStructure(
                has_clear_problem=structure_data.get("has_clear_problem", False),
                has_evidence=structure_data.get("has_evidence", False),
                has_multiple_perspectives=structure_data.get("has_multiple_perspectives", False),
                has_actionable_conclusions=structure_data.get("has_actionable_conclusions", False),
                logical_flow_score=float(structure_data.get("logical_flow_score", 0.5)),
                argument_coherence=float(structure_data.get("argument_coherence", 0.5)),
                conclusion_strength=float(structure_data.get("conclusion_strength", 0.5)),
            )
        except Exception as e:
            logger.error(f"Failed to analyze content structure: {e}")
            return self._default_content_structure()
    
    def _default_content_structure(self) -> ContentStructure:
        """Return default content structure when AI analysis fails."""
        return ContentStructure(
            has_clear_problem=False,
            has_evidence=False,
            has_multiple_perspectives=False,
            has_actionable_conclusions=False,
            logical_flow_score=0.5,
            argument_coherence=0.5,
            conclusion_strength=0.5
        )
    
    def _determine_curation_decision(self, quality_scores: QualityScore, themes: List[Theme], note: Note) -> str:
        """Determine whether to curate the note based on quality scores and themes.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            note: Note being evaluated
            
        Returns:
            Reason for curation decision
        """
        # Check core quality thresholds
        quality_passed = quality_scores.overall >= self.config.quality_threshold
        relevance_passed = quality_scores.relevance >= self.config.relevance_threshold
        
        # Check professional writing quality (NEW - targeting 9/10 readiness)
        professional_score = quality_scores.professional_writing_score
        professional_threshold = 0.7  # 70% threshold for professional quality
        professional_passed = professional_score >= professional_threshold
        
        # Enhanced decision logic
        if not quality_passed and not relevance_passed and not professional_passed:
            return f"Failed all thresholds: quality={quality_scores.overall:.2f}, relevance={quality_scores.relevance:.2f}, professional={professional_score:.2f}"
        
        if not quality_passed and not relevance_passed:
            return f"Failed both quality ({quality_scores.overall:.2f} < {self.config.quality_threshold}) and relevance ({quality_scores.relevance:.2f} < {self.config.relevance_threshold}) thresholds"
        
        if not quality_passed:
            return f"Failed quality threshold: {quality_scores.overall:.2f} < {self.config.quality_threshold}"
        
        if not relevance_passed:
            return f"Failed relevance threshold: {quality_scores.relevance:.2f} < {self.config.relevance_threshold}"
        
        # Professional writing quality bonus (NEW)
        if professional_passed:
            professional_bonus = " (Professional writing quality bonus)"
        else:
            professional_bonus = f" (Professional writing: {professional_score:.2f} < {professional_threshold})"
        
        # Check if themes align with target themes
        if self.config.target_themes:
            theme_alignment = any(
                any(target in theme.name.lower() or target in theme.keywords for target in self.config.target_themes)
                for theme in themes
            )
            
            if not theme_alignment:
                return f"Content themes ({[t.name for t in themes]}) don't align with target themes ({self.config.target_themes})"
        
        # All checks passed
        return f"Passed all curation criteria: quality={quality_scores.overall:.2f}, relevance={quality_scores.relevance:.2f}{professional_bonus}"
    
    def _default_quality_scores(self) -> QualityScore:
        """Return default quality scores when AI analysis fails."""
        return QualityScore(
            # Core metrics
            overall=0.5,
            relevance=0.5,
            completeness=0.5,
            credibility=0.5,
            clarity=0.5,
            # Professional writing metrics (NEW)
            analytical_depth=0.5,
            evidence_quality=0.5,
            critical_thinking=0.5,
            argument_structure=0.5,
            practical_value=0.5
        )
    
    def _default_theme(self) -> Theme:
        """Return default theme when AI analysis fails."""
        return Theme(
            # Core theme fields
            name="Unknown",
            confidence=0.5,
            subthemes=[],
            keywords=[],
            # Professional insight classification (NEW)
            expertise_level="intermediate",
            content_category="technical",
            business_value="operational"
        )
    
    def batch_analyze(self, notes: List[Note]) -> List[Tuple[Note, QualityScore, List[Theme], ContentStructure, str]]:
        """Analyze multiple notes in batch.
        
        Args:
            notes: List of notes to analyze
            
        Returns:
            List of analysis results with content structure
        """
        results = []
        
        for i, note in enumerate(notes):
            logger.info(f"Analyzing note {i+1}/{len(notes)}: {note.title}")
            
            try:
                quality_scores, themes, content_structure, curation_reason = self.analyze_note(note)
                results.append((note, quality_scores, themes, content_structure, curation_reason))
                
                # Add small delay to avoid overwhelming the AI service
                import time
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to analyze note {note.title}: {e}")
                # Add default results for failed analysis
                default_scores = self._default_quality_scores()
                default_themes = [self._default_theme()]
                default_structure = self._default_content_structure()
                results.append((note, default_scores, default_themes, default_structure, f"Analysis failed: {str(e)}"))
        
        return results
