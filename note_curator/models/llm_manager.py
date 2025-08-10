"""High-performance LLM manager for note classification using Ollama API."""

import asyncio
import logging
import os
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
import hashlib
from functools import lru_cache
import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.models import PillarType, NoteType, CurationAction, QualityScore, PillarAnalysis

logger = logging.getLogger(__name__)
console = Console()


class LLMManager:
    """High-performance LLM manager using Ollama API with caching and parallel processing."""
    
    def __init__(self, config_path: Path = Path("config/models_config.yaml")):
        """Initialize the LLM manager."""
        self.config_path = config_path
        self.config = self._load_config()
        self.cache: Dict[str, Dict] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Performance optimizations
        self.quick_filter_enabled = self.config.get('performance', {}).get('enable_quick_filter', True)
        self.batch_processing_enabled = self.config.get('performance', {}).get('enable_batch_processing', True)
        self.max_concurrent_requests = self.config.get('performance', {}).get('max_concurrent_requests', 1)
        self.cache_enabled = self.config.get('performance', {}).get('enable_caching', True)
        
        # Ollama settings
        self.ollama_base_url = self.config.get('performance', {}).get('ollama_base_url', 'http://localhost:11434')
        self.request_timeout = self.config.get('performance', {}).get('request_timeout', 30)
        self.max_retries = self.config.get('performance', {}).get('max_retries', 3)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Model config not found: {self.config_path}")
            raise
    
    def _make_ollama_request(self, model: str, prompt: str, options: Dict[str, Any] = None) -> str:
        """Make a request to Ollama API."""
        url = f"{self.ollama_base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if options:
            payload.update(options)
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=self.request_timeout)
                response.raise_for_status()
                result = response.json()
                return result.get('response', '')
            except requests.exceptions.RequestException as e:
                logger.warning(f"Ollama request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)  # Brief delay before retry
        
        return ""
    
    def _get_cache_key(self, content: str, task: str) -> str:
        """Generate cache key for content and task."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{content_hash}:{task}"
    
    @lru_cache(maxsize=1000)
    def _cached_analysis(self, content_hash: str, task: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result."""
        cache_key = f"{content_hash}:{task}"
        return self.cache.get(cache_key)
    
    def _cache_result(self, content_hash: str, task: str, result: Dict[str, Any]):
        """Cache analysis result."""
        if self.cache_enabled:
            cache_key = f"{content_hash}:{task}"
            self.cache[cache_key] = result
    
    def quick_filter(self, content: str) -> Tuple[bool, float]:
        """Quick filter to determine if content is relevant."""
        if not self.quick_filter_enabled:
            return True, 1.0
        
        cache_key = self._get_cache_key(content, "quick_filter")
        cached_result = self._cached_analysis(cache_key.split(':')[0], "quick_filter")
        
        if cached_result:
            self.cache_hits += 1
            return cached_result['relevant'], cached_result['confidence']
        
        self.cache_misses += 1
        
        try:
            model_config = self.config['models']['quick_filter']
            model_name = model_config['ollama_model']
            
            prompt = f"""Quick filter: Is this content relevant for note curation? Answer with 'YES' or 'NO' and confidence 0-1.

Content: {content[:500]}...

Answer:"""
            
            response = self._make_ollama_request(
                model_name,
                prompt,
                {
                    "temperature": model_config.get('temperature', 0.01),
                    "top_p": model_config.get('top_p', 0.99),
                    "num_predict": model_config.get('max_tokens', 32)
                }
            )
            
            # Parse response
            response_lower = response.lower().strip()
            relevant = 'yes' in response_lower
            confidence = 0.8  # Default confidence for quick filter
            
            # Try to extract confidence from response
            if 'confidence' in response_lower or '0.' in response_lower:
                import re
                confidence_match = re.search(r'0\.\d+', response_lower)
                if confidence_match:
                    confidence = float(confidence_match.group())
            
            result = {'relevant': relevant, 'confidence': confidence}
            self._cache_result(cache_key.split(':')[0], "quick_filter", result)
            
            return relevant, confidence
            
        except Exception as e:
            logger.error(f"Quick filter failed: {e}")
            return True, 0.5  # Default to relevant with low confidence
    
    def analyze_notes_batch(self, notes_data: List[Tuple[Path, str]]) -> List[Dict[str, Any]]:
        """Analyze multiple notes in batch using Ollama."""
        if not self.batch_processing_enabled:
            return [self.analyze_note_content(content, file_path) for file_path, content in notes_data]
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            future_to_note = {
                executor.submit(self.analyze_note_content, content, file_path): (file_path, content)
                for file_path, content in notes_data
            }
            
            for future in as_completed(future_to_note):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_path, content = future_to_note[future]
                    logger.error(f"Failed to analyze {file_path}: {e}")
                    results.append(self._create_default_analysis())
        
        return results
    
    def analyze_note_content(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze note content using Ollama."""
        cache_key = self._get_cache_key(content, "analysis")
        cached_result = self._cached_analysis(cache_key.split(':')[0], "analysis")
        
        if cached_result:
            self.cache_hits += 1
            return cached_result
        
        self.cache_misses += 1
        
        try:
            model_config = self.config['models']['detailed_analysis']
            model_name = model_config['ollama_model']
            
            prompt = self._build_analysis_prompt(content, file_path)
            
            response = self._make_ollama_request(
                model_name,
                prompt,
                {
                    "temperature": model_config.get('temperature', 0.1),
                    "top_p": model_config.get('top_p', 0.9),
                    "num_predict": model_config.get('max_tokens', 512)
                }
            )
            
            result = self._parse_analysis_response(response)
            self._cache_result(cache_key.split(':')[0], "analysis", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self._create_default_analysis()
    
    def analyze_and_classify_note(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze and classify note content using Ollama."""
        cache_key = self._get_cache_key(content, "classification")
        cached_result = self._cached_analysis(cache_key.split(':')[0], "classification")
        
        if cached_result:
            self.cache_hits += 1
            return cached_result
        
        self.cache_misses += 1
        
        try:
            # First, perform quick filter
            if self.quick_filter_enabled:
                relevant, confidence = self.quick_filter(content)
                if not relevant or confidence < 0.3:
                    return {
                        'note_type': NoteType.UNCATEGORIZED,
                        'pillar_type': PillarType.UNCATEGORIZED,
                        'curation_action': CurationAction.SKIP,
                        'quality_score': QualityScore.LOW,
                        'confidence': confidence,
                        'reasoning': 'Content filtered out by quick filter'
                    }
            
            # Perform detailed analysis
            analysis = self.analyze_note_content(content, file_path)
            
            # Perform classification
            classification = self._perform_classification(content, analysis)
            
            # Combine results
            result = {**analysis, **classification}
            self._cache_result(cache_key.split(':')[0], "classification", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._create_default_classification()
    
    def _perform_classification(self, content: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform note classification using Ollama."""
        try:
            model_config = self.config['models']['fast_classification']
            model_name = model_config['ollama_model']
            
            prompt = self._build_classification_prompt(content, analysis)
            
            response = self._make_ollama_request(
                model_name,
                prompt,
                {
                    "temperature": model_config.get('temperature', 0.05),
                    "top_p": model_config.get('top_p', 0.95),
                    "num_predict": model_config.get('max_tokens', 128)
                }
            )
            
            return self._parse_classification_response(response)
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                'note_type': NoteType.UNCATEGORIZED,
                'pillar_type': PillarType.UNCATEGORIZED,
                'curation_action': CurationAction.SKIP,
                'quality_score': QualityScore.LOW,
                'confidence': 0.0,
                'reasoning': f'Classification failed: {e}'
            }
    
    def _build_analysis_prompt(self, content: str, file_path: Path) -> str:
        """Build analysis prompt for Ollama."""
        return f"""Analyze this note content and provide structured analysis:

File: {file_path.name}
Content: {content[:1000]}...

Provide analysis in this JSON format:
{{
    "summary": "Brief summary of the content",
    "key_topics": ["topic1", "topic2"],
    "content_type": "article|note|reference|other",
    "complexity": "simple|moderate|complex",
    "relevance_score": 0.0-1.0,
    "quality_indicators": ["well_structured", "clear_writing", "original_content"]
}}

Analysis:"""
    
    def _build_classification_prompt(self, content: str, analysis: Dict[str, Any]) -> str:
        """Build classification prompt for Ollama."""
        return f"""Classify this note based on the analysis:

Content: {content[:500]}...
Analysis: {analysis.get('summary', 'N/A')}

Classify in this JSON format:
{{
    "note_type": "ARTICLE|REFERENCE|PERSONAL|PROJECT|OTHER",
    "pillar_type": "KNOWLEDGE|PROCESS|OUTPUT|OTHER",
    "curation_action": "KEEP|MODIFY|ARCHIVE|DELETE",
    "quality_score": "HIGH|MEDIUM|LOW",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification"
}}

Classification:"""
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response from Ollama."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback parsing
        return {
            'summary': response[:200] if response else 'No analysis available',
            'key_topics': [],
            'content_type': 'other',
            'complexity': 'moderate',
            'relevance_score': 0.5,
            'quality_indicators': []
        }
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse classification response from Ollama."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback parsing
        return {
            'note_type': NoteType.UNCATEGORIZED,
            'pillar_type': PillarType.UNCATEGORIZED,
            'curation_action': CurationAction.SKIP,
            'quality_score': QualityScore.LOW,
            'confidence': 0.0,
            'reasoning': 'Failed to parse classification response'
        }
    
    def _create_default_analysis(self) -> Dict[str, Any]:
        """Create default analysis result."""
        return {
            'summary': 'Analysis failed',
            'key_topics': [],
            'content_type': 'other',
            'complexity': 'moderate',
            'relevance_score': 0.0,
            'quality_indicators': []
        }
    
    def _create_default_classification(self) -> Dict[str, Any]:
        """Create default classification result."""
        return {
            'note_type': NoteType.UNCATEGORIZED,
            'pillar_type': PillarType.UNCATEGORIZED,
            'curation_action': CurationAction.SKIP,
            'quality_score': QualityScore.LOW,
            'confidence': 0.0,
            'reasoning': 'Classification failed'
        }
    
    def complete_prompt(self, prompt: str, model_type: str = None, max_tokens: int = 1024, temperature: float = 0.2) -> str:
        """Complete a prompt using Ollama."""
        try:
            if model_type and model_type in self.config['models']:
                model_config = self.config['models'][model_type]
                model_name = model_config['ollama_model']
                options = {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            else:
                # Use fallback model
                fallback_config = self.config.get('fallback', {})
                model_name = fallback_config.get('ollama_model', 'phi2')
                options = {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            
            return self._make_ollama_request(model_name, prompt, options)
            
        except Exception as e:
            logger.error(f"Prompt completion failed: {e}")
            return f"Error: {e}"
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'cache_size': len(self.cache),
            'ollama_base_url': self.ollama_base_url,
            'request_timeout': self.request_timeout,
            'max_retries': self.max_retries
        } 