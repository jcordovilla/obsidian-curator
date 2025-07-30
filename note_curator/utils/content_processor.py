"""Content processor for enhanced preprocessing and normalization."""

import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Enhanced content processing for Evernote web clippings and note normalization."""
    
    def __init__(self):
        """Initialize the content processor."""
        # Common Evernote web clipping patterns
        self.evernote_patterns = {
            'clipping_header': r'^.*?Clipped from.*?on.*?\n',
            'evernote_footer': r'\n.*?Evernote.*?$',
            'web_annotations': r'\[.*?\]\s*\(https?://.*?\)',
            'navigation_elements': r'(Home|About|Contact|Privacy|Terms|Login|Sign up|Subscribe|Follow|Share|Tweet|Like|Comment)',
            'ad_patterns': r'(Advertisement|Ad|Sponsored|Promoted|Buy now|Shop now|Learn more)',
            'social_media': r'(Facebook|Twitter|Instagram|LinkedIn|YouTube|TikTok)',
            'tracking_params': r'[?&](utm_|fbclid|gclid|msclkid|ref=|source=).*?(?=\s|$)',
            'html_entities': r'&[a-zA-Z0-9#]+;',
            'excessive_whitespace': r'\s{3,}',
            'repeated_chars': r'(.)\1{3,}',  # 4+ repeated characters
        }
        
        # Content quality indicators
        self.quality_indicators = {
            'substantive_content': [
                r'\b\d{4}\b',  # Years
                r'\b\d+%\b',   # Percentages
                r'\$\d+',      # Dollar amounts
                r'\b[A-Z]{2,}\b',  # Acronyms
                r'\b\d+[-–]\d+\b',  # Number ranges
            ],
            'technical_terms': [
                r'\b(PPP|BIM|IoT|AI|ML|API|SLA|KPI|ROI|VFM)\b',
                r'\b(infrastructure|project|finance|risk|governance|transparency)\b',
                r'\b(digital|transformation|automation|analytics|data|platform)\b',
            ]
        }
    
    def preprocess_evernote_clipping(self, content: str, file_path: Path) -> Dict[str, any]:
        """Preprocess Evernote web clipping to extract clean content."""
        original_length = len(content)
        
        # Step 1: Remove Evernote-specific clutter
        cleaned_content = self._remove_evernote_clutter(content)
        
        # Step 2: Extract metadata
        metadata = self._extract_metadata(content, file_path)
        
        # Step 3: Clean and structure content
        structured_content = self._structure_content(cleaned_content)
        
        # Step 4: Assess content quality
        quality_metrics = self._assess_content_quality(structured_content)
        
        return {
            'original_content': content,
            'cleaned_content': structured_content['text'],
            'metadata': metadata,
            'structure': structured_content['structure'],
            'quality_metrics': quality_metrics,
            'reduction_ratio': len(structured_content['text']) / original_length if original_length > 0 else 0
        }
    
    def _remove_evernote_clutter(self, content: str) -> str:
        """Remove Evernote web clipping clutter."""
        cleaned = content
        
        # Remove Evernote clipping headers and footers
        cleaned = re.sub(self.evernote_patterns['clipping_header'], '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(self.evernote_patterns['evernote_footer'], '', cleaned, flags=re.MULTILINE)
        
        # Remove web annotations and links
        cleaned = re.sub(self.evernote_patterns['web_annotations'], '', cleaned)
        
        # Remove navigation elements
        cleaned = re.sub(self.evernote_patterns['navigation_elements'], '', cleaned, flags=re.IGNORECASE)
        
        # Remove ad patterns
        cleaned = re.sub(self.evernote_patterns['ad_patterns'], '', cleaned, flags=re.IGNORECASE)
        
        # Remove social media references
        cleaned = re.sub(self.evernote_patterns['social_media'], '', cleaned, flags=re.IGNORECASE)
        
        # Remove tracking parameters from URLs
        cleaned = re.sub(self.evernote_patterns['tracking_params'], '', cleaned)
        
        # Clean up HTML entities
        cleaned = re.sub(self.evernote_patterns['html_entities'], ' ', cleaned)
        
        # Normalize whitespace
        cleaned = re.sub(self.evernote_patterns['excessive_whitespace'], ' ', cleaned)
        cleaned = re.sub(self.evernote_patterns['repeated_chars'], r'\1\1\1', cleaned)
        
        return cleaned.strip()
    
    def _extract_metadata(self, content: str, file_path: Path) -> Dict[str, any]:
        """Extract metadata from content."""
        metadata = {
            'source_url': None,
            'clipping_date': None,
            'author': None,
            'title': None,
            'tags': [],
            'categories': []
        }
        
        # Extract source URL
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, content)
        if urls:
            metadata['source_url'] = urls[0]
        
        # Extract clipping date
        date_patterns = [
            r'Clipped from.*?on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                metadata['clipping_date'] = match.group(1)
                break
        
        # Extract title (first line or filename)
        lines = content.split('\n')
        if lines and lines[0].strip():
            metadata['title'] = lines[0].strip()
        else:
            metadata['title'] = file_path.stem
        
        return metadata
    
    def _structure_content(self, content: str) -> Dict[str, any]:
        """Structure content into sections."""
        lines = content.split('\n')
        structure = {
            'text': '',
            'structure': {
                'sections': [],
                'key_points': [],
                'quotes': [],
                'lists': [],
                'data_points': []
            }
        }
        
        current_section = {'title': '', 'content': []}
        key_points = []
        quotes = []
        lists = []
        data_points = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            if re.match(r'^[A-Z][A-Z\s]+$', line) or re.match(r'^\d+\.\s+[A-Z]', line):
                if current_section['content']:
                    structure['structure']['sections'].append(current_section)
                current_section = {'title': line, 'content': []}
            
            # Detect key points
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                key_points.append(line)
                current_section['content'].append(line)
            
            # Detect quotes
            elif line.startswith('"') and line.endswith('"'):
                quotes.append(line)
                current_section['content'].append(line)
            
            # Detect lists
            elif re.match(r'^\d+\.\s+', line):
                lists.append(line)
                current_section['content'].append(line)
            
            # Detect data points
            elif re.search(r'\d+%|\$\d+|\d{4}', line):
                data_points.append(line)
                current_section['content'].append(line)
            
            else:
                current_section['content'].append(line)
        
        # Add final section
        if current_section['content']:
            structure['structure']['sections'].append(current_section)
        
        # Build clean text
        structure['text'] = '\n'.join([line for line in lines if line.strip()])
        
        # Store structured elements
        structure['structure']['key_points'] = key_points
        structure['structure']['quotes'] = quotes
        structure['structure']['lists'] = lists
        structure['structure']['data_points'] = data_points
        
        return structure
    
    def _assess_content_quality(self, structured_content: Dict[str, any]) -> Dict[str, any]:
        """Assess the quality of processed content."""
        text = structured_content['text']
        structure = structured_content['structure']
        
        metrics = {
            'word_count': len(text.split()),
            'sentence_count': len(re.split(r'[.!?]+', text)),
            'paragraph_count': len([s for s in structure['sections'] if s['content']]),
            'key_points_count': len(structure['key_points']),
            'quotes_count': len(structure['quotes']),
            'lists_count': len(structure['lists']),
            'data_points_count': len(structure['data_points']),
            'substantive_indicators': 0,
            'technical_terms': 0,
            'readability_score': 0
        }
        
        # Count substantive indicators
        for pattern in self.quality_indicators['substantive_content']:
            metrics['substantive_indicators'] += len(re.findall(pattern, text))
        
        # Count technical terms
        for pattern in self.quality_indicators['technical_terms']:
            metrics['technical_terms'] += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Calculate readability score (simplified)
        if metrics['sentence_count'] > 0 and metrics['word_count'] > 0:
            avg_sentence_length = metrics['word_count'] / metrics['sentence_count']
            metrics['readability_score'] = max(0, 100 - (avg_sentence_length * 2))
        
        return metrics
    
    def normalize_note_structure(self, content: str, note_type: str, pillar: str) -> str:
        """Normalize note structure based on type and pillar."""
        if not content.strip():
            return content
        
        # Add frontmatter
        frontmatter = self._generate_frontmatter(note_type, pillar)
        
        # Structure content based on type
        structured_content = self._apply_note_template(content, note_type, pillar)
        
        return f"{frontmatter}\n\n{structured_content}"
    
    def _generate_frontmatter(self, note_type: str, pillar: str) -> str:
        """Generate YAML frontmatter for the note."""
        now = datetime.now()
        
        frontmatter = f"""---
type: {note_type}
pillar: {pillar}
created: {now.strftime('%Y-%m-%d %H:%M:%S')}
status: processed
tags: [{note_type}, {pillar}]
---"""
        
        return frontmatter
    
    def _apply_note_template(self, content: str, note_type: str, pillar: str) -> str:
        """Apply template structure based on note type."""
        templates = {
            'literature_research': self._template_literature_research,
            'project_workflow': self._template_project_workflow,
            'personal_reflection': self._template_personal_reflection,
            'technical_code': self._template_technical_code,
            'meeting_template': self._template_meeting_template,
            'community_event': self._template_community_event
        }
        
        template_func = templates.get(note_type, self._template_default)
        return template_func(content, pillar)
    
    def _template_literature_research(self, content: str, pillar: str) -> str:
        """Template for literature/research notes."""
        return f"""# Literature Review: {pillar.replace('_', ' ').title()}

## Key Findings
{content}

## Implications
- 

## Related Topics
- 

## References
- 

## Notes
- """
    
    def _template_project_workflow(self, content: str, pillar: str) -> str:
        """Template for project/workflow notes."""
        return f"""# Project Workflow: {pillar.replace('_', ' ').title()}

## Overview
{content}

## Steps
1. 
2. 
3. 

## Resources
- 

## Lessons Learned
- 

## Next Steps
- """
    
    def _template_personal_reflection(self, content: str, pillar: str) -> str:
        """Template for personal reflection notes."""
        return f"""# Reflection: {pillar.replace('_', ' ').title()}

## Context
{content}

## Insights
- 

## Questions
- 

## Actions
- 

## Follow-up
- """
    
    def _template_technical_code(self, content: str, pillar: str) -> str:
        """Template for technical/code notes."""
        return f"""# Technical Note: {pillar.replace('_', ' ').title()}

## Problem
{content}

## Solution
```python
# Code here
```

## Usage
- 

## Notes
- 

## References
- """
    
    def _template_meeting_template(self, content: str, pillar: str) -> str:
        """Template for meeting notes."""
        return f"""# Meeting: {pillar.replace('_', ' ').title()}

## Participants
- 

## Agenda
{content}

## Discussion Points
- 

## Decisions
- 

## Action Items
- [ ] 
- [ ] 
- [ ] 

## Next Meeting
- """
    
    def _template_community_event(self, content: str, pillar: str) -> str:
        """Template for community/event notes."""
        return f"""# Event: {pillar.replace('_', ' ').title()}

## Event Details
{content}

## Key Takeaways
- 

## Connections Made
- 

## Follow-up Actions
- 

## Resources Shared
- """
    
    def _template_default(self, content: str, pillar: str) -> str:
        """Default template for unknown note types."""
        return f"""# {pillar.replace('_', ' ').title()}

{content}

## Notes
- 

## Related
- """ 