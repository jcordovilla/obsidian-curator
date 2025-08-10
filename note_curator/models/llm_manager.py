"""High-performance LLM manager for note classification."""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
import hashlib
import json
from functools import lru_cache
import time

# Set environment variables to disable Metal GPU warnings
os.environ["LLAMA_CPP_DISABLE_METAL"] = "1"
os.environ["GGML_METAL_DISABLE"] = "1"
os.environ["LLAMA_CPP_USE_METAL"] = "0"

from llama_cpp import Llama
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.models import PillarType, NoteType, CurationAction, QualityScore, PillarAnalysis

logger = logging.getLogger(__name__)
console = Console()


class LLMManager:
    """High-performance LLM manager with caching and parallel processing."""
    
    def __init__(self, config_path: Path = Path("config/models_config.yaml")):
        """Initialize the LLM manager."""
        self.config_path = config_path
        self.config = self._load_config()
        self.models: Dict[str, Llama] = {}
        self.cache: Dict[str, Dict] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Performance optimizations
        self.quick_filter_enabled = self.config.get('performance', {}).get('enable_quick_filter', True)
        self.batch_processing_enabled = self.config.get('performance', {}).get('enable_batch_processing', True)
        self.max_concurrent_requests = self.config.get('performance', {}).get('max_concurrent_requests', 1)
        self.cache_enabled = self.config.get('performance', {}).get('enable_caching', True)
        
        self._initialize_models()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Model config not found: {self.config_path}")
            raise
    
    def _initialize_models(self):
        """Initialize optimized LLM models with hybrid approach."""
        # Load model configurations from config file
        model_configs = self.config.get("models", {})
        
        for model_type, config in model_configs.items():
            try:
                # Try relative to config file first, then relative to current directory
                model_path = Path(config["path"])
                if not model_path.exists():
                    # Try relative to config file location
                    config_dir = self.config_path.parent
                    model_path = config_dir / config["path"]
                    if not model_path.exists():
                        # Try relative to project root (assuming config is in project root)
                        project_root = config_dir.parent
                        model_path = project_root / config["path"]
                        if not model_path.exists():
                            logger.warning(f"Model not found: {config['path']} for {model_type}")
                            # Try fallback model if available
                            fallback_config = self.config.get("fallback", {})
                            if fallback_config and "model_path" in fallback_config:
                                fallback_path = Path(fallback_config["model_path"])
                                if not fallback_path.exists():
                                    fallback_path = config_dir / fallback_config["model_path"]
                                    if not fallback_path.exists():
                                        fallback_path = project_root / fallback_config["model_path"]
                                if fallback_path.exists():
                                    logger.info(f"Using fallback model for {model_type}: {fallback_path}")
                                    config = fallback_config
                                    model_path = fallback_path
                                else:
                                    logger.error(f"Fallback model also not found: {fallback_config['model_path']}")
                                    continue
                            else:
                                continue
                
                self.models[model_type] = Llama(
                    model_path=str(model_path),
                    n_ctx=config.get("context_window", 2048),
                    n_gpu_layers=config.get("n_gpu_layers", 0),
                    n_threads=config.get("n_threads", 4),
                    verbose=False,
                    use_mmap=True,
                    use_mlock=False,
                    logits_all=False,
                    embedding=False,
                    rope_scaling=None
                )
                logger.info(f"Initialized {model_type} model: {model_path}")
                
            except Exception as e:
                logger.error(f"Failed to initialize {model_type} model: {e}")
                # Try fallback if main model fails
                try:
                    fallback_config = self.config.get("fallback", {})
                    if fallback_config and "model_path" in fallback_config:
                        fallback_path = Path(fallback_config["model_path"])
                        if not fallback_path.exists():
                            config_dir = self.config_path.parent
                            fallback_path = config_dir / fallback_config["model_path"]
                            if not fallback_path.exists():
                                project_root = config_dir.parent
                                fallback_path = project_root / fallback_config["model_path"]
                        if fallback_path.exists():
                            logger.info(f"Using fallback model for {model_type}: {fallback_path}")
                            self.models[model_type] = Llama(
                                model_path=str(fallback_path),
                                n_ctx=fallback_config.get("context_window", 2048),
                                n_gpu_layers=fallback_config.get("n_gpu_layers", 0),
                                n_threads=fallback_config.get("n_threads", 4),
                                verbose=False,
                                use_mmap=True,
                                use_mlock=False,
                                logits_all=False,
                                embedding=False,
                                rope_scaling=None
                            )
                            logger.info(f"Fallback model initialized for {model_type}")
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed for {model_type}: {fallback_error}")
    
    def _get_cache_key(self, content: str, task: str) -> str:
        """Generate cache key for content and task."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{task}_{content_hash}"
    
    @lru_cache(maxsize=1000)
    def _cached_analysis(self, content_hash: str, task: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result."""
        cache_key = f"{task}_{content_hash}"
        result = self.cache.get(cache_key)
        if result:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        return result
    
    def _cache_result(self, content_hash: str, task: str, result: Dict[str, Any]):
        """Cache analysis result."""
        self.cache[f"{task}_{content_hash}"] = result
    
    def quick_filter(self, content: str) -> Tuple[bool, float]:
        """Quick filter to determine if note is worth detailed analysis."""
        if len(content) < 50:  # Very short notes
            return False, 0.0
        
        # Check for obvious indicators
        low_value_indicators = [
            'test', 'draft', 'temp', 'todo', 'reminder', 'note to self',
            'placeholder', 'template', 'example', 'sample'
        ]
        
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in low_value_indicators):
            return False, 0.1
        
        # Quick AI check for relevance - OPTIMIZED for speed
        prompt = f"""Quick check: Is this note relevant to infrastructure, PPP, or digital transformation?

Content: {content[:300]}...

Answer with only: relevant/not_relevant confidence_score(0-1)"""
        
        try:
            model = self._get_model('quick_filter')
            if model:
                response = model(
                    prompt=prompt,
                    max_tokens=32,  # Reduced for speed
                    temperature=0.01,
                    stop=["\n"]
                )
                
                if 'choices' in response:
                    result = response['choices'][0]['text'].strip()
                    if 'relevant' in result.lower():
                        # Extract confidence score
                        import re
                        confidence_match = re.search(r'(\d+\.?\d*)', result)
                        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
                        return True, confidence
                
        except Exception as e:
            logger.warning(f"Quick filter failed: {e}")
        
        # Default to processing if filter fails
        return True, 0.5
    
    def analyze_notes_batch(self, notes_data: List[Tuple[Path, str]]) -> List[Dict[str, Any]]:
        """Analyze multiple notes sequentially with optimized processing."""
        results = []
        
        # Quick filter first - OPTIMIZED: Use smaller model and shorter prompts
        filtered_notes = []
        for note_path, content in notes_data:
            should_process, confidence = self.quick_filter(content)
            if should_process:
                filtered_notes.append((note_path, content, confidence))
            else:
                results.append({
                    'file_path': note_path,
                    'analysis': self._create_default_analysis(),
                    'classification': {
                        'curation_action': 'delete',
                        'curation_reasoning': 'Quick filtered - low relevance',
                        'confidence': confidence
                    }
                })
        
        # Process filtered notes sequentially - OPTIMIZED: Better caching and processing
        for note_path, content, confidence in filtered_notes:
            try:
                result = self._analyze_single_note_optimized(note_path, content, confidence)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {note_path}: {e}")
                results.append({
                    'file_path': note_path,
                    'analysis': self._create_default_analysis(),
                    'classification': {
                        'curation_action': 'archive',
                        'curation_reasoning': f'Analysis failed: {e}',
                        'confidence': 0.0
                    }
                })
        
        return results
    
    def _analyze_single_note_optimized(self, file_path: Path, content: str, confidence: float) -> Dict[str, Any]:
        """Analyze a single note with optimized caching and processing."""
        # Check cache first
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cached_analysis = self._cached_analysis(content_hash, 'analysis')
        cached_classification = self._cached_analysis(content_hash, 'classification')
        
        if cached_analysis and cached_classification:
            logger.debug(f"Using cached results for {file_path.name}")
            return {
                'file_path': file_path,
                'analysis': cached_analysis,
                'classification': cached_classification
            }
        
        # OPTIMIZED: Use combined analysis for better performance
        combined_result = self._perform_combined_analysis_optimized(content, file_path)
        
        # Split result into analysis and classification
        analysis_result = {
            'primary_pillar': combined_result.get('primary_pillar'),
            'secondary_pillars': [],
            'note_type': combined_result.get('note_type'),
            'quality_scores': combined_result.get('quality_scores', {}),
            'pillar_analyses': []
        }
        
        classification_result = {
            'curation_action': combined_result.get('curation_action', 'archive'),
            'curation_reasoning': combined_result.get('curation_reasoning', 'Analysis completed'),
            'confidence': combined_result.get('confidence', 0.5)
        }
        
        # Cache results
        self._cache_result(content_hash, 'analysis', analysis_result)
        self._cache_result(content_hash, 'classification', classification_result)
        
        return {
            'file_path': file_path,
            'analysis': analysis_result,
            'classification': classification_result
        }
    
    def _perform_combined_analysis_optimized(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Perform optimized combined analysis and classification."""
        try:
            # OPTIMIZED: Use Phi-2 model for faster processing
            model = self._get_model('fast_classification')
            if not model:
                model = self._get_model('detailed_analysis')
            
            if not model:
                return self._create_default_analysis()
            
            # OPTIMIZED: Shorter, more focused prompt
            combined_prompt = f"""Analyze this note for infrastructure/PPP relevance:

File: {file_path.name}
Content: {content[:800]}...

Return JSON:
{{
    "primary_pillar": "pillar_type",
    "note_type": "note_type", 
    "quality_scores": {{
        "relevance": 0.0-1.0,
        "depth": 0.0-1.0,
        "actionability": 0.0-1.0,
        "uniqueness": 0.0-1.0,
        "structure": 0.0-1.0
    }},
    "curation_action": "keep/refine/archive/delete",
    "curation_reasoning": "brief explanation",
    "confidence": 0.0-1.0
}}

Pillars: ppp_fundamentals, operational_risk, value_for_money, digital_transformation, governance_transparency
Types: literature_research, project_workflow, personal_reflection, technical_code, meeting_template, community_event"""
            
            response = model(
                prompt=combined_prompt,
                max_tokens=256,  # Reduced for speed
                temperature=0.1,
                top_p=0.9,
                stop=["\n\n", "```"]
            )
            
            if 'choices' in response:
                result_text = response['choices'][0]['text'].strip()
                return self._parse_combined_response_optimized(result_text)
            else:
                return self._create_default_analysis()
                
        except Exception as e:
            logger.error(f"Combined analysis failed for {file_path}: {e}")
            return self._create_default_analysis()
    
    def _parse_combined_response_optimized(self, response: str) -> Dict[str, Any]:
        """Parse combined analysis and classification response - optimized."""
        try:
            import re
            import json
            
            # Clean the response - remove any non-JSON text
            response = response.strip()
            
            # Try to find JSON object with multiple patterns
            json_patterns = [
                r'\{[^{}]*"primary_pillar"[^{}]*\}',  # JSON with primary_pillar
                r'\{[^{}]*"curation_action"[^{}]*\}',  # JSON with curation_action
                r'\{[^{}]*"quality_scores"[^{}]*\}',   # JSON with quality_scores
                r'\{.*\}',  # Basic JSON object
            ]
            
            parsed_data = None
            for pattern in json_patterns:
                json_match = re.search(pattern, response, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group()
                        # Clean up common JSON issues
                        json_str = re.sub(r'[\n\r\t]', ' ', json_str)  # Remove newlines/tabs
                        json_str = re.sub(r',\s*}', '}', json_str)     # Remove trailing commas
                        json_str = re.sub(r',\s*]', ']', json_str)     # Remove trailing commas in arrays
                        
                        parsed_data = json.loads(json_str)
                        break
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode failed for pattern {pattern}: {e}")
                        continue
            
            if parsed_data:
                # Extract and validate quality scores
                quality_scores = parsed_data.get('quality_scores', {})
                if not isinstance(quality_scores, dict):
                    quality_scores = {}
                
                # Ensure all quality score fields exist
                required_scores = ['relevance', 'depth', 'actionability', 'uniqueness', 'structure']
                for score in required_scores:
                    if score not in quality_scores:
                        quality_scores[score] = 0.1
                
                # Validate score ranges
                for score in quality_scores:
                    try:
                        quality_scores[score] = max(0.0, min(1.0, float(quality_scores[score])))
                    except (ValueError, TypeError):
                        quality_scores[score] = 0.1
                
                # Build result with all required fields
                result = {
                    "primary_pillar": parsed_data.get('primary_pillar'),
                    "secondary_pillars": [],  # Simplified - no secondary pillars
                    "note_type": parsed_data.get('note_type'),
                    "quality_scores": quality_scores,
                    "curation_action": parsed_data.get('curation_action', 'archive'),
                    "curation_reasoning": parsed_data.get('curation_reasoning', 'Parsed from LLM response'),
                    "confidence": max(0.0, min(1.0, float(parsed_data.get('confidence', 0.5)))),
                    "pillar_analyses": []
                }
                
                # Add default values for missing fields
                if not result["primary_pillar"]:
                    result["primary_pillar"] = None
                if not result["note_type"]:
                    result["note_type"] = None
                if not result["curation_reasoning"]:
                    result["curation_reasoning"] = "Classification completed"
                
                return result
                
        except Exception as e:
            logger.warning(f"Could not parse combined response: {e}")
        
        return self._create_default_analysis()
    
    def analyze_note_content(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze note content using the analysis model."""
        try:
            model = self._get_model('detailed_analysis')
            if not model:
                return self._create_default_analysis()
            
            prompt = self._build_analysis_prompt(content, file_path)
            response = model(
                prompt=prompt,
                max_tokens=512,
                temperature=0.1,
                top_p=0.9,
                stop=["</s>", "###"]
            )
            
            if 'choices' in response:
                result_text = response['choices'][0]['text'].strip()
                return self._parse_analysis_response(result_text)
            else:
                return self._create_default_analysis()
                
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}")
            return self._create_default_analysis()
    
    def analyze_and_classify_note(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Single optimized function that combines analysis and classification."""
        try:
            # Use the larger Llama 3.1 8B model for better reliability
            model = self._get_model('detailed_analysis')
            if not model:
                # Fallback to fast classification model
                model = self._get_model('fast_classification')
            
            if not model:
                return self._create_default_analysis()
            
            # Build improved combined prompt
            folder_name = file_path.parent.name
            combined_prompt = f"""<|system|>
You are a JSON generator. You must respond with ONLY a valid JSON object, no other text.
</s>
<|user|>
Analyze this note for infrastructure/PPP consulting relevance:

File: {file_path.name}
Content: {content[:1200]}...

Return ONLY a JSON object in this format:

{{
    "primary_pillar": "ppp_fundamentals",
    "note_type": "literature_research",
    "quality_scores": {{
        "relevance": 0.8,
        "depth": 0.6,
        "actionability": 0.7,
        "uniqueness": 0.5,
        "structure": 0.8
    }},
    "curation_action": "keep",
    "curation_reasoning": "This note discusses PPP fundamentals and infrastructure development with actionable insights",
    "confidence": 0.8
}}

Valid values:
- primary_pillar: ppp_fundamentals, operational_risk, value_for_money, digital_transformation, governance_transparency
- note_type: literature_research, project_workflow, personal_reflection, technical_code, meeting_template, community_event
- curation_action: keep, refine, archive, delete
- quality_scores: 0.0 to 1.0 for each dimension
- confidence: 0.0 to 1.0
</s>
<|assistant|>"""
            
            response = model(
                prompt=combined_prompt,
                max_tokens=512,  # Increased from 256
                temperature=0.1,
                top_p=0.9,
                stop=["\n\n", "```"]
            )
            
            if 'choices' in response:
                result_text = response['choices'][0]['text'].strip()
                logger.info(f"LLM Response for {file_path.name}: {result_text[:200]}...")
                return self._parse_combined_response(result_text)
            else:
                logger.warning(f"No choices in response for {file_path.name}")
                return self._create_default_analysis()
                
        except Exception as e:
            logger.error(f"Combined analysis failed for {file_path}: {e}")
            return self._create_default_analysis()
    
    def _parse_combined_response(self, response: str) -> Dict[str, Any]:
        """Parse combined analysis and classification response."""
        try:
            import re
            import json
            
            # Clean the response - remove any non-JSON text
            response = response.strip()
            
            # Try to find JSON object with multiple patterns
            json_patterns = [
                r'\{[^{}]*"primary_pillar"[^{}]*\}',  # JSON with primary_pillar
                r'\{[^{}]*"curation_action"[^{}]*\}',  # JSON with curation_action
                r'\{[^{}]*"quality_scores"[^{}]*\}',   # JSON with quality_scores
                r'\{.*\}',  # Basic JSON object
            ]
            
            parsed_data = None
            for pattern in json_patterns:
                json_match = re.search(pattern, response, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group()
                        # Clean up common JSON issues
                        json_str = re.sub(r'[\n\r\t]', ' ', json_str)  # Remove newlines/tabs
                        json_str = re.sub(r',\s*}', '}', json_str)     # Remove trailing commas
                        json_str = re.sub(r',\s*]', ']', json_str)     # Remove trailing commas in arrays
                        
                        parsed_data = json.loads(json_str)
                        break
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode failed for pattern {pattern}: {e}")
                        continue
            
            if parsed_data:
                # Extract and validate quality scores
                quality_scores = parsed_data.get('quality_scores', {})
                if not isinstance(quality_scores, dict):
                    quality_scores = {}
                
                # Ensure all quality score fields exist
                required_scores = ['relevance', 'depth', 'actionability', 'uniqueness', 'structure']
                for score in required_scores:
                    if score not in quality_scores:
                        quality_scores[score] = 0.1
                
                # Validate score ranges
                for score in quality_scores:
                    try:
                        quality_scores[score] = max(0.0, min(1.0, float(quality_scores[score])))
                    except (ValueError, TypeError):
                        quality_scores[score] = 0.1
                
                # Build result with all required fields
                result = {
                    "primary_pillar": parsed_data.get('primary_pillar'),
                    "secondary_pillars": [],  # Simplified - no secondary pillars
                    "note_type": parsed_data.get('note_type'),
                    "quality_scores": quality_scores,
                    "curation_action": parsed_data.get('curation_action', 'archive'),
                    "curation_reasoning": parsed_data.get('curation_reasoning', 'Parsed from LLM response'),
                    "confidence": max(0.0, min(1.0, float(parsed_data.get('confidence', 0.5)))),
                    "pillar_analyses": []
                }
                
                # Add default values for missing fields
                if not result["primary_pillar"]:
                    result["primary_pillar"] = None
                if not result["note_type"]:
                    result["note_type"] = None
                if not result["curation_reasoning"]:
                    result["curation_reasoning"] = "Classification completed"
                
                logger.info(f"Successfully parsed JSON response: {result.get('primary_pillar')}, {result.get('note_type')}, {result.get('curation_action')}")
                return result
                
        except Exception as e:
            logger.warning(f"Could not parse combined response: {e}")
            logger.debug(f"Raw response: {response}")
            logger.info(f"Response length: {len(response)}")
            logger.info(f"Response preview: {response[:300]}...")
        
        return self._create_default_analysis()
    
    def _perform_analysis(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Perform detailed content analysis."""
        # Optimized prompt for faster processing
        prompt = f"""Analyze this note for infrastructure/PPP relevance:

{content[:1500]}...

JSON response:
{{
    "primary_pillar": "pillar_type",
    "note_type": "note_type",
    "quality_scores": {{
        "relevance": 0.0-1.0,
        "depth": 0.0-1.0,
        "actionability": 0.0-1.0,
        "uniqueness": 0.0-1.0,
        "structure": 0.0-1.0
    }}
}}

Pillars: ppp_fundamentals, operational_risk, value_for_money, digital_transformation, governance_transparency
Types: literature_research, project_workflow, personal_reflection, technical_code, meeting_template, community_event"""
        
        try:
            model = self._get_model('detailed_analysis')
            if model:
                response = model(
                    prompt=prompt,
                    max_tokens=512,
                    temperature=0.1,
                    stop=["\n\n", "```"]
                )
                
                if 'choices' in response:
                    return self._parse_analysis_response(response['choices'][0]['text'].strip())
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}")
        
        return self._create_default_analysis()
    
    def _perform_classification(self, content: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform classification with optimized prompt."""
        # Calculate overall score
        scores = analysis.get('quality_scores', {})
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0
        
        # Optimized classification prompt
        prompt = f"""Classify this note (score: {overall_score:.2f}):

{content[:300]}...

Action: keep/refine/archive/delete
Reason: brief explanation
Confidence: 0.0-1.0

JSON: {{"action": "action", "reason": "reason", "confidence": 0.0}}"""
        
        try:
            model = self._get_model('fast_classification')
            if model:
                response = model(
                    prompt=prompt,
                    max_tokens=256,
                    temperature=0.05,
                    stop=["\n\n"]
                )
                
                if 'choices' in response:
                    return self._parse_classification_response(response['choices'][0]['text'].strip())
        except Exception as e:
            logger.error(f"Classification failed: {e}")
        
        return self._create_default_classification()
    
    def _get_model(self, model_type: str) -> Optional[Llama]:
        """Get a specific model by type."""
        return self.models.get(model_type)
    
    def _get_model_config(self, model: Llama) -> Dict[str, Any]:
        """Get configuration for a specific model."""
        # Find which model type this is
        for model_type, model_instance in self.models.items():
            if model_instance == model:
                return self.config.get("models", {}).get(model_type, {})
        return {}
    
    def _get_model_name(self, model: Llama) -> str:
        """Get the name/type of a model instance."""
        for model_type, model_instance in self.models.items():
            if model_instance == model:
                return model_type
        return "unknown"
    
    def _build_combined_analysis_prompt(self, content: str, file_path: Path) -> str:
        """Build optimized combined analysis and classification prompt."""
        folder_name = file_path.parent.name
        
        return f"""<|system|>
You are a JSON generator for infrastructure/PPP consulting note analysis. Respond with ONLY valid JSON.
</s>
<|user|>
Analyze this note for infrastructure/PPP consulting relevance:

File: {file_path.name}
Folder: {folder_name}
Content: {content[:1000]}...

Return ONLY a JSON object:

{{
    "primary_pillar": "ppp_fundamentals",
    "note_type": "literature_research", 
    "quality_scores": {{
        "relevance": 0.8,
        "depth": 0.6,
        "actionability": 0.7,
        "uniqueness": 0.5,
        "structure": 0.8
    }},
    "curation_action": "keep",
    "curation_reasoning": "Brief reasoning",
    "confidence": 0.8
}}

Valid values:
- primary_pillar: ppp_fundamentals, operational_risk, value_for_money, digital_transformation, governance_transparency
- note_type: literature_research, project_workflow, personal_reflection, technical_code, meeting_template, community_event
- curation_action: keep, refine, archive, delete
- quality_scores: 0.0 to 1.0 for each dimension
- confidence: 0.0 to 1.0
</s>
<|assistant|>"""
    
    def _build_analysis_prompt(self, content: str, file_path: Path) -> str:
        """Build prompt for content analysis."""
        # Extract folder context
        folder_path = str(file_path.parent)
        folder_name = file_path.parent.name
        
        return f"""You are an expert knowledge management analyst specializing in infrastructure, PPP, and digital transformation.

Analyze the following note from a personal knowledge base:

File: {file_path.name}
Location: {folder_path}
Folder Context: {folder_name}
Content:
{content[:2000]}...

CRITICAL ANALYSIS REQUIREMENTS:
1. **Strict Pillar Classification**: Only assign pillars if the content has SUBSTANTIVE relevance to the expert domain. Do NOT classify based on folder names alone.
2. **Evidence-Based Scoring**: Quality scores must reflect actual content quality, not assumptions.
3. **Content Depth Assessment**: Evaluate whether the note provides meaningful analysis or just surface-level information.
4. **Expert Domain Focus**: Only classify as relevant if content directly relates to infrastructure, PPP, digital transformation, governance, or operational risk.

Provide a detailed analysis in the following JSON format:
{{
    "word_count": <int>,
    "has_frontmatter": <bool>,
    "has_attachments": <bool>,
    "attachment_count": <int>,
    "primary_pillar": "<pillar_type>",
    "secondary_pillars": ["<pillar_type>", ...],
    "note_type": "<note_type>",
    "quality_scores": {{
        "relevance": <float 0-1>,
        "depth": <float 0-1>,
        "actionability": <float 0-1>,
        "uniqueness": <float 0-1>,
        "structure": <float 0-1>
    }},
    "pillar_analyses": [
        {{
            "pillar": "<pillar_type>",
            "relevance_score": <float 0-1>,
            "confidence": <float 0-1>,
            "reasoning": "<explanation>",
            "keywords_found": ["<keyword>", ...]
        }}
    ]
}}

Pillar types: ppp_fundamentals, operational_risk, value_for_money, digital_transformation, governance_transparency
Note types: literature_research, project_workflow, personal_reflection, technical_code, meeting_template, community_event

IMPORTANT GUIDELINES:
- **Be conservative** with pillar assignments. If content is unclear or minimal, assign "None" for primary_pillar.
- **Quality scores should be low** for notes with minimal content, poor structure, or unclear relevance.
- **Require clear evidence** of expert domain relevance before assigning high relevance scores.
- **Consider folder context** but do not rely on it exclusively for classification.
- **Focus on substantive content** that contributes to infrastructure consulting, PPP, or digital transformation knowledge."""

    def _build_classification_prompt(self, content: str, analysis: Dict[str, Any]) -> str:
        """Build prompt for note classification."""
        return f"""Based on the previous analysis, determine the best curation action for this note.

Analysis Summary:
- Primary Pillar: {analysis.get('primary_pillar', 'None')}
- Note Type: {analysis.get('note_type', 'None')}
- Quality Scores: {analysis.get('quality_scores', {})}
- Folder Context: {analysis.get('folder_context', 'None')}

Content Preview:
{content[:500]}...

CRITICAL EVALUATION CRITERIA:
1. **Relevance to Expert Domains**: Does this note contain substantive content related to infrastructure, PPP, digital transformation, governance, or operational risk?
2. **Content Depth**: Does it provide meaningful analysis, insights, or actionable information?
3. **Uniqueness**: Does it offer unique perspectives or information not easily found elsewhere?
4. **Actionability**: Can this content be directly applied to consulting work or knowledge development?
5. **Quality**: Is the content well-structured, accurate, and professionally presented?

Determine the appropriate curation action and provide reasoning in JSON format:
{{
    "action": "<action>",
    "reason": "<detailed explanation>",
    "confidence": <float 0-1>
}}

Curation actions (be STRICT and CRITICAL):
- "keep": ONLY high-value content with clear relevance to expert domains, substantial depth, and unique insights
- "refine": Good content that needs improvement but has clear potential value for expert work
- "archive": Potentially useful but not immediately actionable or lacks depth
- "delete": Low value, irrelevant to expert domains, redundant, or poor quality

IMPORTANT: Be conservative. If in doubt, choose "archive" or "delete". Only "keep" notes that clearly contribute to infrastructure consulting, PPP, or digital transformation knowledge."""

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response from LLM."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"Could not parse analysis response: {e}")
        
        return self._create_default_analysis()
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse classification response from LLM."""
        try:
            import re
            # Look for JSON pattern in the response
            json_match = re.search(r'\{[^{}]*"action"[^{}]*"reason"[^{}]*"confidence"[^{}]*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    'curation_action': parsed.get('action', 'archive'),
                    'curation_reasoning': parsed.get('reason', 'Unable to parse'),
                    'confidence': parsed.get('confidence', 0.0)
                }
            else:
                # Try to extract action from text if JSON parsing fails
                action_match = re.search(r'"action":\s*"([^"]+)"', response)
                reason_match = re.search(r'"reason":\s*"([^"]+)"', response)
                confidence_match = re.search(r'"confidence":\s*([0-9.]+)', response)
                
                action = action_match.group(1) if action_match else 'archive'
                reason = reason_match.group(1) if reason_match else 'Unable to parse classification response'
                confidence = float(confidence_match.group(1)) if confidence_match else 0.0
                
                return {
                    'curation_action': action,
                    'curation_reasoning': reason,
                    'confidence': confidence
                }
        except Exception as e:
            logger.warning(f"Could not parse classification response: {e}")
            logger.debug(f"Raw response: {response}")
        
        return self._create_default_classification()
    
    def _create_default_analysis(self) -> Dict[str, Any]:
        """Create default analysis when parsing fails."""
        return {
            "word_count": 0,
            "has_frontmatter": False,
            "has_attachments": False,
            "attachment_count": 0,
            "primary_pillar": None,
            "secondary_pillars": [],
            "note_type": None,
            "quality_scores": {
                "relevance": 0.1,
                "depth": 0.1,
                "actionability": 0.1,
                "uniqueness": 0.1,
                "structure": 0.1
            },
            "pillar_analyses": [],
            "curation_action": "archive",
            "curation_reasoning": "Analysis failed - defaulting to archive",
            "confidence": 0.1
        }
    
    def _create_default_classification(self) -> Dict[str, Any]:
        """Create default classification when parsing fails."""
        return {
            "curation_action": "archive",
            "curation_reasoning": "Unable to parse classification response",
            "confidence": 0.0
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self.cache),
            'models_loaded': len(self.models),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate
        } 

    def complete_prompt(self, prompt: str, model_type: str = None, max_tokens: int = 1024, temperature: float = 0.2) -> str:
        """
        Complete a generic prompt using the LLM, returning the raw output.
        This is for meta-evaluation or general-purpose LLM use, not note classification.
        """
        if not model_type:
            # Use the first available model as default
            if self.models:
                model_type = next(iter(self.models))
            else:
                raise RuntimeError("No LLM models are loaded.")
        model = self.models[model_type]
        response = model(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=None
        )
        # The Llama API returns a dict with 'choices' key
        if isinstance(response, dict) and 'choices' in response and response['choices']:
            return response['choices'][0]['text'].strip()
        # Fallback: try to get text directly
        if isinstance(response, str):
            return response.strip()
        return str(response).strip() 