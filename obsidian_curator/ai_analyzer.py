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
        self.model = config.ai_model  # Default/fallback model
        
        # Test connection to Ollama and validate models
        try:
            available_models = ollama.list()
            model_names = [m['name'] for m in available_models.get('models', [])]
            
            # Validate that all configured models are available
            missing_models = []
            for task, model_name in {
                'content_curation': config.models.content_curation,
                'quality_analysis': config.models.quality_analysis,
                'theme_classification': config.models.theme_classification,
                'structure_analysis': config.models.structure_analysis,
                'fallback': config.models.fallback
            }.items():
                if model_name not in model_names:
                    missing_models.append(f"{task}: {model_name}")
            
            if missing_models:
                logger.warning(f"Missing models: {', '.join(missing_models)}. Will use fallback model.")
            
            logger.info(f"Connected to Ollama with multi-model setup:")
            logger.info(f"  Content Curation: {config.models.content_curation}")
            logger.info(f"  Quality Analysis: {config.models.quality_analysis}")
            logger.info(f"  Theme Classification: {config.models.theme_classification}")
            logger.info(f"  Structure Analysis: {config.models.structure_analysis}")
            logger.info(f"  Fallback: {config.models.fallback}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise

    def _get_model_for_task(self, task: str) -> str:
        """Get the optimal model for a specific task.
        
        Args:
            task: Task name (content_curation, quality_analysis, theme_classification, structure_analysis)
            
        Returns:
            Model name to use for the task
        """
        task_models = {
            'content_curation': self.config.models.content_curation,
            'quality_analysis': self.config.models.quality_analysis,  
            'theme_classification': self.config.models.theme_classification,
            'structure_analysis': self.config.models.structure_analysis
        }
        
        model = task_models.get(task, self.config.models.fallback)
        logger.debug(f"Using model '{model}' for task '{task}'")
        return model

    def _chat_json(self, system_prompt: str, prompt: str, temperature: float = 0.1, task: str = "fallback") -> Any:
        """Call Ollama chat API requesting JSON output."""
        try:
            model = self._get_model_for_task(task)
            logger.debug(f"Calling Ollama model '{model}' for task '{task}'")
            
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                format="json",
                options={"temperature": temperature},
            )
            content = response["message"]["content"].strip()
            
            # Debug: Log the raw response for troubleshooting
            logger.info(f"Ollama response length: {len(content)} chars")
            logger.debug(f"Raw Ollama response: {repr(content)}")
            
            # Handle empty responses
            if not content:
                logger.warning("Empty response from Ollama, using fallback")
                return {}
            
            # Clean up potential control characters
            content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
            
            # Try to extract JSON if response contains extra text
            if '{' in content and '}' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                json_content = content[start:end]
                
                # Fix common malformed JSON patterns
                json_content = self._fix_malformed_json(json_content)
                logger.debug(f"Extracted JSON content: {repr(json_content)}")
            else:
                # Try to find array format
                if '[' in content and ']' in content:
                    start = content.find('[')
                    end = content.rfind(']') + 1
                    json_content = content[start:end]
                    json_content = self._fix_malformed_json(json_content)
                    logger.debug(f"Extracted array content: {repr(json_content)}")
                else:
                    logger.warning("No JSON structure found in response")
                    return {}
            
            # Try to parse the cleaned JSON
            try:
                parsed_json = json.loads(json_content)
                logger.debug(f"Successfully parsed JSON: {type(parsed_json)}")
                return parsed_json
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse cleaned JSON: {e}")
                logger.debug(f"Cleaned JSON content: {repr(json_content)}")
                
                # Last resort: try to extract just the essential data
                return self._extract_fallback_data(content)
                
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return {}
    
    def _extract_fallback_data(self, content: str) -> Any:
        """Extract basic data when JSON parsing completely fails."""
        try:
            # Try to extract basic theme information from text
            if "theme" in content.lower() or "themes" in content.lower():
                # Extract theme names that might be mentioned
                import re
                theme_matches = re.findall(r'["\']([^"\']*(?:infrastructure|construction|governance|policy|technical|strategic)[^"\']*)["\']', content, re.IGNORECASE)
                
                if theme_matches:
                    return [{
                        "name": theme_matches[0],
                        "confidence": 0.6,
                        "subthemes": [],
                        "keywords": [theme_matches[0].lower()],
                        "expertise_level": "intermediate",
                        "content_category": "technical",
                        "business_value": "operational"
                    }]
            
            # Return empty structure for structure analysis
            return {
                "has_clear_problem": True,
                "has_evidence": False,
                "has_multiple_perspectives": False,
                "has_actionable_conclusions": True,
                "logical_flow_score": 0.6,
                "argument_coherence": 0.6,
                "conclusion_strength": 0.6
            }
            
        except Exception as e:
            logger.warning(f"Fallback data extraction failed: {e}")
            return {}
    
    def _fix_malformed_json(self, json_str: str) -> str:
        """Fix common JSON malformation patterns seen in Ollama responses."""
        import re
        
        # Remove any text before the first {
        if '{' in json_str:
            start = json_str.find('{')
            json_str = json_str[start:]
        
        # Remove any text after the last }
        if '}' in json_str:
            end = json_str.rfind('}') + 1
            json_str = json_str[:end]
        
        # Fix: {": "quality" -> {"quality" (the main issue from the logs)
        json_str = re.sub(r'\{":\s*"([^"]+)"', r'{"\1"', json_str)
        
        # Fix: Missing quotes around property names  
        json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # Fix: Trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix: Single quotes to double quotes (in case AI uses single quotes)
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        
        # Fix: Remove any remaining text that's not JSON - BUT PRESERVE LETTERS IN FIELD NAMES
        # Only remove truly problematic characters, not letters
        json_str = re.sub(r'[^\w\{\}\[\]",:0-9.\-truefalse\s]', '', json_str)
        
        # Fix: Ensure proper boolean values
        json_str = re.sub(r':\s*true\s*([,}])', r': true\1', json_str)
        json_str = re.sub(r':\s*false\s*([,}])', r': false\1', json_str)
        
        return json_str
    
    def _analyze_quality_with_routing(self, note: Note) -> Tuple[QualityScore, Dict[str, Any]]:
        """Analyze quality using routing cascade with escalation.
        
        Args:
            note: Note to analyze
            
        Returns:
            Tuple of (quality_scores, route_info)
        """
        import time
        
        route_info = {
            "stages_used": [],
            "total_latency_ms": 0,
            "escalation_reason": None,
            "final_stage": None
        }
        
        content = note.content[:2000] if note.content else ""
        if not content or len(content.strip()) < 50:
            # For very short content, use fast assessment
            quality_scores = self._get_short_content_scores(note)
            route_info.update({
                "stages_used": ["short_content_bypass"],
                "final_stage": "short_content_bypass",
                "total_latency_ms": 0
            })
            return quality_scores, route_info
        
        for stage_idx, stage in enumerate(self.config.routing.stages):
            start_time = time.time()
            
            try:
                # Analyze with current stage model
                logger.debug(f"Trying stage {stage_idx + 1}: {stage.model}")
                quality_scores = self._analyze_quality_with_model(note, content, stage.model)
                
                latency_ms = (time.time() - start_time) * 1000
                route_info["stages_used"].append({
                    "stage": stage_idx + 1,
                    "model": stage.model,
                    "latency_ms": latency_ms
                })
                route_info["total_latency_ms"] += latency_ms
                
                # Check if latency exceeded threshold
                if stage.max_latency_ms and latency_ms > stage.max_latency_ms:
                    logger.warning(f"Stage {stage_idx + 1} exceeded latency threshold: {latency_ms:.1f}ms > {stage.max_latency_ms}ms")
                    route_info["escalation_reason"] = f"latency_exceeded_{stage.max_latency_ms}ms"
                    continue
                
                # Check if scores are in gray zone (need escalation)
                if self._is_in_gray_zone(quality_scores, stage.gray_margin):
                    logger.info(f"Stage {stage_idx + 1} result in gray zone, escalating...")
                    route_info["escalation_reason"] = f"gray_zone_margin_{stage.gray_margin}"
                    # Continue to next stage if available
                    if stage_idx < len(self.config.routing.stages) - 1:
                        continue
                
                # Success - return results
                route_info["final_stage"] = stage.model
                if self.config.routing.log_route:
                    logger.info(f"Quality analysis completed using {stage.model} in {latency_ms:.1f}ms")
                
                return quality_scores, route_info
                
            except Exception as e:
                logger.warning(f"Stage {stage_idx + 1} ({stage.model}) failed: {e}")
                route_info["stages_used"].append({
                    "stage": stage_idx + 1,
                    "model": stage.model,
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000
                })
                route_info["escalation_reason"] = f"stage_error_{stage.model}"
                continue
        
        # All stages failed or exhausted - use fallback
        logger.warning("All routing stages failed or exhausted, using fallback analysis")
        quality_scores = self._analyze_quality(note)
        route_info["final_stage"] = "fallback"
        route_info["escalation_reason"] = "all_stages_exhausted"
        
        return quality_scores, route_info
    
    def _analyze_quality_with_model(self, note: Note, content: str, model: str) -> QualityScore:
        """Analyze quality using a specific model.
        
        Args:
            note: Note to analyze
            content: Content to analyze
            model: Model to use
            
        Returns:
            QualityScore object
        """
        # Override the model for this analysis
        original_model = self.model
        self.model = model
        
        try:
            return self._ai_analyze_quality(note, content)
        finally:
            # Restore original model
            self.model = original_model
    
    def _is_in_gray_zone(self, quality_scores: QualityScore, gray_margin: float) -> bool:
        """Check if quality scores are in the gray zone around thresholds.
        
        Args:
            quality_scores: Quality scores to check
            gray_margin: Gray zone margin
            
        Returns:
            True if in gray zone
        """
        # Check key thresholds for gray zone
        thresholds_to_check = [
            (quality_scores.overall, self.config.quality_threshold),
            (quality_scores.relevance, self.config.relevance_threshold),
        ]
        
        # Add analytical depth if configured
        if hasattr(self.config, 'analytical_depth_threshold'):
            thresholds_to_check.append(
                (quality_scores.analytical_depth, self.config.analytical_depth_threshold)
            )
        
        for score, threshold in thresholds_to_check:
            if abs(score - threshold) <= gray_margin:
                return True
        
        return False
    
    def _get_short_content_scores(self, note: Note) -> QualityScore:
        """Get quality scores for short content without full AI analysis.
        
        Args:
            note: Note to analyze
            
        Returns:
            QualityScore object
        """
        # Audio content gets special treatment
        if note.content_type == "audio_annotation":
            return QualityScore(
                overall=0.4, relevance=0.5, completeness=0.3, credibility=0.4, clarity=0.3,
                analytical_depth=0.2, evidence_quality=0.3, critical_thinking=0.2,
                argument_structure=0.2, practical_value=0.4
            )
        else:
            return QualityScore(
                overall=0.2, relevance=0.3, completeness=0.1, credibility=0.2, clarity=0.1,
                analytical_depth=0.1, evidence_quality=0.1, critical_thinking=0.1,
                argument_structure=0.1, practical_value=0.1
            )
    
    def analyze_note(self, note: Note) -> Tuple[QualityScore, List[Theme], ContentStructure, str, Optional[Dict[str, Any]]]:
        """Analyze a note for quality, themes, and structure.
        
        Args:
            note: Note to analyze
            
        Returns:
            Tuple of (quality_scores, themes, content_structure, curation_reason, route_info)
        """
        try:
            # Check if routing is enabled
            if self.config.routing.enabled and self.config.routing.stages:
                # Use routing cascade for quality analysis
                quality_scores, route_info = self._analyze_quality_with_routing(note)
            else:
                # Standard analysis
                quality_scores = self._analyze_quality(note)
                route_info = None
            
            # Identify themes
            themes = self._identify_themes(note)
            
            # Analyze content structure
            content_structure = self._analyze_structure(note)
            
            # Determine curation reason
            curation_reason = self._determine_curation_reason(quality_scores, themes, content_structure, note)
            
            return quality_scores, themes, content_structure, curation_reason, route_info
            
        except Exception as e:
            logger.error(f"Failed to analyze note {note.title}: {e}")
            # Return default scores on failure
            return self._get_default_scores(), [], self._get_default_structure(), f"Analysis failed: {str(e)}", None
    
    def _analyze_quality(self, note: Note) -> QualityScore:
        """Analyze the quality of a note's content using AI.
        
        Args:
            note: Note to analyze
            
        Returns:
            QualityScore object
        """
        # Prepare content for analysis
        content = note.content[:2000] if note.content else ""  # Limit content length for analysis
        
        if not content or len(content.strip()) < 50:
            # Very short content gets low scores - NO ARTIFICIAL BOOSTING
            # Exception: Audio content might have minimal text but still be valuable
            if note.content_type == "audio_annotation":
                result = QualityScore(
                    overall=0.4, relevance=0.5, completeness=0.3, credibility=0.4, clarity=0.3,
                    analytical_depth=0.2, evidence_quality=0.3, critical_thinking=0.2,
                    argument_structure=0.2, practical_value=0.4
                )
            else:
                result = QualityScore(
                    overall=0.2, relevance=0.3, completeness=0.1, credibility=0.2, clarity=0.1,
                    analytical_depth=0.1, evidence_quality=0.1, critical_thinking=0.1,
                    argument_structure=0.1, practical_value=0.1
                )
            logger.debug(f"Short content quality analysis: overall={result.overall}, relevance={result.relevance}")
            return result
        
        # Try AI analysis first
        try:
            logger.debug(f"Attempting AI quality analysis for note: {note.title}")
            ai_result = self._ai_analyze_quality(note, content)
            logger.debug(f"AI quality analysis SUCCESS: overall={ai_result.overall}, relevance={ai_result.relevance}")
            return ai_result
        except Exception as e:
            logger.warning(f"AI quality analysis failed for note '{note.title}', using heuristic fallback: {e}")
            logger.debug(f"Content preview: {content[:200]}...")
            heuristic_result = self._heuristic_quality_analysis(note, content)
            logger.debug(f"Heuristic quality analysis: overall={heuristic_result.overall}, relevance={heuristic_result.relevance}")
            return heuristic_result
    
    def _ai_analyze_quality(self, note: Note, content: str) -> QualityScore:
        """Use AI to analyze content quality."""
        system_prompt = f"""You are an expert content quality analyst specializing in infrastructure, construction, and governance content. Use {self.config.reasoning_level} reasoning to assess content quality objectively.

CRITICAL: You must respond with ONLY valid JSON. No explanations, no additional text, no markdown formatting. Just the JSON object."""
        
        prompt = f"""Analyze the QUALITY of this content for professional infrastructure/construction/governance work.

Content:
{content}

Assess each dimension on a 0.0-1.0 scale where:
- 0.0-0.3: Poor quality, not suitable for professional use
- 0.4-0.6: Average quality, some value but limited
- 0.7-0.9: Good quality, suitable for professional reference
- 0.9-1.0: Excellent quality, publication-ready

Return ONLY a JSON object with this exact format (no other text):
{{
    "overall": 0.7,
    "relevance": 0.8,
    "completeness": 0.6,
    "credibility": 0.7,
    "clarity": 0.8,
    "analytical_depth": 0.6,
    "evidence_quality": 0.7,
    "critical_thinking": 0.5,
    "argument_structure": 0.6,
    "practical_value": 0.7
}}

Rules:
- Be honest about quality - don't inflate scores
- All scores must be numbers between 0.0 and 1.0
- Consider the content's actual value to infrastructure professionals
- Provide ONLY the JSON object, no other text whatsoever"""
        
        logger.debug(f"Calling AI for quality analysis with prompt length: {len(prompt)}")
        quality_data = self._chat_json(system_prompt, prompt, temperature=0.1, task="quality_analysis")
        
        logger.debug(f"AI response type: {type(quality_data)}, content: {repr(quality_data)}")
        
        if not quality_data or not isinstance(quality_data, dict):
            logger.error(f"Invalid AI response for quality analysis: {type(quality_data)} - {repr(quality_data)}")
            raise ValueError("Invalid AI response for quality analysis")
        
        # Extract scores with validation
        try:
            # Debug: Log the actual values being extracted
            overall_score = float(quality_data.get("overall", 0.3))
            relevance_score = float(quality_data.get("relevance", 0.3))
            
            logger.debug(f"Parsed scores from AI: overall={overall_score}, relevance={relevance_score}")
            
            result = QualityScore(
                overall=overall_score,
                relevance=relevance_score,
                completeness=float(quality_data.get("completeness", 0.3)),
                credibility=float(quality_data.get("credibility", 0.3)),
                clarity=float(quality_data.get("clarity", 0.3)),
                analytical_depth=float(quality_data.get("analytical_depth", 0.3)),
                evidence_quality=float(quality_data.get("evidence_quality", 0.3)),
                critical_thinking=float(quality_data.get("critical_thinking", 0.3)),
                argument_structure=float(quality_data.get("argument_structure", 0.3)),
                practical_value=float(quality_data.get("practical_value", 0.3))
            )
            
            logger.debug(f"QualityScore created: overall={result.overall}, relevance={result.relevance}")
            return result
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse quality scores from AI response: {e}")
            logger.error(f"Raw AI response: {repr(quality_data)}")
            raise ValueError(f"Failed to parse quality scores: {e}")
    
    def _heuristic_quality_analysis(self, note: Note, content: str) -> QualityScore:
        """Fallback heuristic quality analysis when AI fails."""
        # Check for obvious quality indicators
        quality_indicators = {
            'has_clear_structure': any(marker in content.lower() for marker in ['##', '###', '**', '- ']),
            'has_substantial_content': len(content.split()) > 100,
            'has_professional_language': any(word in content.lower() for word in ['analysis', 'research', 'study', 'report', 'findings', 'project', 'development', 'management', 'infrastructure', 'construction']),
            'has_citations': any(marker in content for marker in ['http', 'www', 'doi:', 'arxiv:', 'icex', 'rand', 'eleconomista']),
            'has_data': any(marker in content for marker in ['%', 'million', 'billion', 'data', 'statistics', '2014', '2019', '2020', '2021', '2022', '2023', '2024', '2025'])
        }
        
        # Calculate realistic base scores - NO ARTIFICIAL INFLATION
        base_scores = {
            'relevance': 0.6 if quality_indicators['has_substantial_content'] else 0.3,
            'completeness': 0.5 if quality_indicators['has_clear_structure'] else 0.2,
            'credibility': 0.6 if quality_indicators['has_citations'] else 0.3,
            'clarity': 0.5 if quality_indicators['has_clear_structure'] else 0.2,
            'analytical_depth': 0.5 if quality_indicators['has_professional_language'] else 0.2,
            'evidence_quality': 0.5 if quality_indicators['has_data'] else 0.2,
            'critical_thinking': 0.4 if quality_indicators['has_professional_language'] else 0.2,
            'argument_structure': 0.5 if quality_indicators['has_clear_structure'] else 0.2,
            'practical_value': 0.4 if quality_indicators['has_substantial_content'] else 0.2
        }
        
        # Calculate overall score - NO BOOSTING
        overall = sum(base_scores.values()) / len(base_scores)
        
        return QualityScore(
            overall=overall,
            **base_scores
        )
    
    def _identify_themes(self, note: Note) -> List[Theme]:
        """Identify themes in the content using AI with better fallback.
        
        Args:
            note: Note to analyze
            
        Returns:
            List of Theme objects
        """
        # Prepare content for analysis
        content = note.content[:2000] if note.content else ""  # Limit content length for analysis
        
        if not content or len(content.strip()) < 50:
            return [self._default_theme()]
        
        # Try AI analysis first
        try:
            return self._ai_identify_themes(note, content)
        except Exception as e:
            logger.warning(f"AI theme analysis failed, using heuristic fallback: {e}")
            return self._heuristic_theme_analysis(note, content)
    
    def _ai_identify_themes(self, note: Note, content: str) -> List[Theme]:
        """Use AI to identify themes."""
        system_prompt = f"""You are an expert thematic analyst specializing in infrastructure, construction, and governance content. Use {self.config.reasoning_level} reasoning to identify relevant themes accurately and consistently.

CRITICAL: You must respond with ONLY valid JSON. No explanations, no additional text, no markdown formatting. Just the JSON array."""
        
        prompt = f"""Analyze this content and identify the main themes relevant to infrastructure, construction, governance, and related professional fields.

Content:
{content}

Return ONLY a JSON array with this exact format (no other text):
[
    {{
        "name": "Infrastructure Development",
        "confidence": 0.85,
        "subthemes": ["transportation", "public works"],
        "keywords": ["highway", "construction", "infrastructure"],
        "expertise_level": "intermediate",
        "content_category": "technical",
        "business_value": "operational"
    }}
]

Rules:
- Use only the exact field names shown above
- Name should be specific and descriptive (not "Unknown")
- Confidence must be a number between 0.0 and 1.0
- Expertise level must be one of: "entry", "intermediate", "expert", "thought_leader"
- Content category must be one of: "strategic", "tactical", "policy", "technical", "operational"
- Business value must be one of: "operational", "strategic", "governance", "innovation"
- If content is not infrastructure-related, use low confidence (0.3-0.5)
- Provide ONLY the JSON array, no other text whatsoever"""
        
        themes_data = self._chat_json(system_prompt, prompt, temperature=0.1, task="theme_classification")
        
        # Handle case where response is not a list
        if not isinstance(themes_data, list):
            logger.warning(f"Theme classification returned non-list: {type(themes_data)}")
            # If it's a single theme object, convert it to a list
            if isinstance(themes_data, dict):
                themes_data = [themes_data]
                logger.info("Converted single theme object to list")
            else:
                raise ValueError("Invalid AI response for theme classification")

        themes: List[Theme] = []
        for theme_data in themes_data:
            if isinstance(theme_data, dict):
                try:
                    # Validate required fields
                    name = theme_data.get("name", "").strip()
                    if not name or name.lower() == "unknown":
                        logger.warning("Skipping theme with missing or unknown name")
                        continue
                    
                    theme = Theme(
                        name=name,
                        confidence=float(theme_data.get("confidence", 0.5)),
                        subthemes=theme_data.get("subthemes", []),
                        keywords=theme_data.get("keywords", []),
                        expertise_level=theme_data.get("expertise_level", "intermediate"),
                        content_category=theme_data.get("content_category", "technical"),
                        business_value=theme_data.get("business_value", "operational"),
                    )
                    themes.append(theme)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse theme data: {e}")
                    continue
        
        # If no themes were successfully parsed, raise error to trigger fallback
        if not themes:
            raise ValueError("No valid themes identified by AI")

        return themes
    
    def _heuristic_theme_analysis(self, note: Note, content: str) -> List[Theme]:
        """Fallback heuristic theme analysis when AI fails."""
        # Define theme keywords for pattern matching
        theme_patterns = {
            "Infrastructure Development": {
                "keywords": ["infrastructure", "highway", "road", "bridge", "transportation", "public works", "construction projects"],
                "confidence": 0.7
            },
            "Public-Private Partnerships": {
                "keywords": ["ppp", "public-private partnership", "concession", "privatization", "public sector", "private sector"],
                "confidence": 0.8
            },
            "Construction Management": {
                "keywords": ["construction", "building", "project management", "engineering", "contractor", "building site"],
                "confidence": 0.7
            },
            "Economic Policy": {
                "keywords": ["economic", "policy", "government", "regulation", "finance", "investment", "funding"],
                "confidence": 0.6
            },
            "Urban Planning": {
                "keywords": ["urban", "city", "planning", "development", "zoning", "municipal", "metropolitan"],
                "confidence": 0.6
            },
            "Technology Systems": {
                "keywords": ["technology", "software", "system", "digital", "automation", "technical", "programming"],
                "confidence": 0.5
            }
        }
        
        content_lower = content.lower()
        identified_themes = []
        
        for theme_name, pattern_info in theme_patterns.items():
            keyword_matches = sum(1 for keyword in pattern_info["keywords"] if keyword in content_lower)
            if keyword_matches > 0:
                # Calculate confidence based on keyword density
                confidence = min(pattern_info["confidence"], keyword_matches * 0.2 + 0.3)
                
                identified_themes.append(Theme(
                    name=theme_name,
                    confidence=confidence,
                    subthemes=[],
                    keywords=pattern_info["keywords"][:3],  # Top 3 keywords
                    expertise_level="intermediate",
                    content_category="technical",
                    business_value="operational"
                ))
        
        # If no themes found, return a general one
        if not identified_themes:
            identified_themes = [self._default_theme()]
        
        # Sort by confidence and return top themes
        identified_themes.sort(key=lambda x: x.confidence, reverse=True)
        return identified_themes[:3]  # Return top 3 themes
    
    def _analyze_structure(self, note: Note) -> ContentStructure:
        """Analyze content structure and logical flow using AI.
        
        Args:
            note: Note to analyze
            
        Returns:
            ContentStructure object with structural analysis
        """
        # Prepare content for analysis
        content = note.content[:2000] if note.content else ""  # Limit content length for analysis
        
        if not content or len(content.strip()) < 50:
            return self._default_content_structure()
        
        system_prompt = f"""You are an expert content structure analyst specializing in professional writing. Use {self.config.reasoning_level} reasoning to analyze the logical flow and argument structure of content.

CRITICAL: You must respond with ONLY valid JSON. No explanations, no additional text, no markdown formatting. Just the JSON object."""
        
        prompt = f"""Analyze the STRUCTURE and LOGICAL FLOW of this content for professional writing quality.

Content:
{content}

Return ONLY a JSON object with this exact format (no other text):
{{
    "has_clear_problem": true,
    "has_evidence": true,
    "has_multiple_perspectives": false,
    "has_actionable_conclusions": true,
    "logical_flow_score": 0.8,
    "argument_coherence": 0.7,
    "conclusion_strength": 0.9
}}

Rules:
- All boolean fields must be true or false (not strings)
- All score fields must be numbers between 0.0 and 1.0
- Provide ONLY the JSON object, no other text whatsoever"""
        
        try:
            structure_data = self._chat_json(system_prompt, prompt, temperature=0.1, task="structure_analysis")

            # Handle empty or invalid JSON response
            if not structure_data or not isinstance(structure_data, dict):
                logger.warning(f"Structure analysis returned invalid data: {type(structure_data)}")
                return self._default_content_structure()

            # Extract values with defaults
            try:
                return ContentStructure(
                    has_clear_problem=bool(structure_data.get("has_clear_problem", False)),
                    has_evidence=bool(structure_data.get("has_evidence", False)),
                    has_multiple_perspectives=bool(structure_data.get("has_multiple_perspectives", False)),
                    has_actionable_conclusions=bool(structure_data.get("has_actionable_conclusions", False)),
                    logical_flow_score=float(structure_data.get("logical_flow_score", 0.5)),
                    argument_coherence=float(structure_data.get("argument_coherence", 0.5)),
                    conclusion_strength=float(structure_data.get("conclusion_strength", 0.5))
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse structure data: {e}")
                return self._default_content_structure()
            
        except Exception as e:
            logger.error(f"Failed to analyze structure: {e}")
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
    
    def _determine_curation_reason(self, quality_scores: QualityScore, themes: List[Theme], 
                                  content_structure: ContentStructure, note: Note) -> str:
        """Determine why a note was curated or rejected.
        
        Args:
            quality_scores: Quality assessment scores
            themes: Identified themes
            content_structure: Content structure analysis
            note: The note being analyzed
            
        Returns:
            String explaining the curation decision
        """
        try:
            # Check if we have valid analysis results
            if not quality_scores or not themes or not content_structure:
                return "Analysis incomplete - using fallback assessment"
            
            # Determine primary reason for curation
            reasons = []
            
            # Quality-based reasons
            if quality_scores.overall >= 0.8:
                reasons.append("High overall quality")
            elif quality_scores.overall >= 0.6:
                reasons.append("Good overall quality")
            
            if quality_scores.relevance >= 0.8:
                reasons.append("Highly relevant content")
            elif quality_scores.relevance >= 0.6:
                reasons.append("Relevant content")
            
            # Theme-based reasons
            if themes:
                confident_themes = [t for t in themes if t.confidence >= 0.7]
                if confident_themes:
                    theme_names = [t.name for t in confident_themes[:2]]  # Top 2 themes
                    reasons.append(f"Strong themes: {', '.join(theme_names)}")
            
            # Structure-based reasons
            if content_structure.has_clear_problem:
                reasons.append("Clear problem statement")
            if content_structure.has_actionable_conclusions:
                reasons.append("Actionable insights")
            if content_structure.logical_flow_score >= 0.7:
                reasons.append("Good logical flow")
            
            # Content length consideration
            content_length = len(note.content) if note.content else 0
            if content_length > 500:
                reasons.append("Substantial content")
            elif content_length > 200:
                reasons.append("Adequate content length")
            
            if reasons:
                return "; ".join(reasons)
            else:
                return "Meets basic curation criteria"
                
        except Exception as e:
            logger.warning(f"Failed to determine curation reason: {e}")
            return "Analysis completed with fallback assessment"
    
    def _get_default_scores(self) -> QualityScore:
        """Get default quality scores for failed analysis."""
        return QualityScore(
            overall=0.5, relevance=0.6, completeness=0.4, credibility=0.5, clarity=0.4,
            analytical_depth=0.4, evidence_quality=0.4, critical_thinking=0.4,
            argument_structure=0.4, practical_value=0.4
        )
    
    def _get_default_structure(self) -> ContentStructure:
        """Get default content structure for failed analysis."""
        return ContentStructure(
            has_clear_problem=True,
            has_evidence=False,
            has_multiple_perspectives=False,
            has_actionable_conclusions=True,
            logical_flow_score=0.5,
            argument_coherence=0.5,
            conclusion_strength=0.5
        )
    
    def _default_theme(self) -> Theme:
        """Get default theme for failed analysis."""
        return Theme(
            name="General Infrastructure",
            confidence=0.5,
            subthemes=[],
            keywords=["infrastructure", "general"],
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
                default_scores = self._get_default_scores()
                default_themes = [self._default_theme()]
                default_structure = self._get_default_structure()
                results.append((note, default_scores, default_themes, default_structure, f"Analysis failed: {str(e)}"))
        
        return results
