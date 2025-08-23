"""Data models for the Obsidian curation system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ContentType(str, Enum):
    """Types of content that can be processed."""
    WEB_CLIPPING = "web_clipping"
    URL_REFERENCE = "url_reference"
    PERSONAL_NOTE = "personal_note"
    ACADEMIC_PAPER = "academic_paper"
    PDF_ANNOTATION = "pdf_annotation"
    IMAGE_ANNOTATION = "image_annotation"
    PROFESSIONAL_PUBLICATION = "professional_publication"
    UNKNOWN = "unknown"


class QualityScore(BaseModel):
    """Quality assessment scores for content."""
    # Core quality metrics (existing)
    overall: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance to target themes")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Completeness of ideas")
    credibility: float = Field(..., ge=0.0, le=1.0, description="Credibility of source")
    clarity: float = Field(..., ge=0.0, le=1.0, description="Clarity of expression")
    
    # Professional writing metrics (NEW - targeting 9/10 readiness)
    analytical_depth: float = Field(default=0.5, ge=0.0, le=1.0, description="Argument sophistication and analytical complexity")
    evidence_quality: float = Field(default=0.5, ge=0.0, le=1.0, description="Quality and relevance of data, studies, and references")
    critical_thinking: float = Field(default=0.5, ge=0.0, le=1.0, description="Challenging assumptions and critical perspective")
    argument_structure: float = Field(default=0.5, ge=0.0, le=1.0, description="Logical flow and argument coherence")
    practical_value: float = Field(default=0.5, ge=0.0, le=1.0, description="Actionable insights and practical implications")
    
    @property
    def average_score(self) -> float:
        """Calculate average of all quality scores."""
        scores = [self.overall, self.relevance, self.completeness, self.credibility, self.clarity]
        return sum(scores) / len(scores)
    
    @property
    def professional_writing_score(self) -> float:
        """Calculate professional writing readiness score (0-1 scale)."""
        professional_metrics = [
            self.analytical_depth,
            self.evidence_quality,
            self.critical_thinking,
            self.argument_structure,
            self.practical_value
        ]
        return sum(professional_metrics) / len(professional_metrics)
    
    @property
    def is_professional_quality(self) -> bool:
        """Check if content meets professional writing standards (>=0.8)."""
        return self.professional_writing_score >= 0.8
    
    @property
    def is_thought_leadership(self) -> bool:
        """Check if content demonstrates thought leadership (>=0.9)."""
        return self.professional_writing_score >= 0.9


class Theme(BaseModel):
    """A content theme or category."""
    # Core theme fields (existing)
    name: str = Field(..., description="Theme name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in theme assignment")
    subthemes: List[str] = Field(default_factory=list, description="Sub-themes")
    keywords: List[str] = Field(default_factory=list, description="Keywords associated with theme")
    
    # Professional insight classification (NEW - targeting 90% accuracy)
    expertise_level: str = Field(default="intermediate", description="Level of expertise demonstrated: entry, intermediate, expert, thought_leader")
    content_category: str = Field(default="technical", description="Content type: strategic, tactical, policy, technical, operational")
    business_value: str = Field(default="operational", description="Business impact: operational, strategic, governance, innovation")
    
    @property
    def is_expert_level(self) -> bool:
        """Check if content demonstrates expert-level expertise."""
        return self.expertise_level in ["expert", "thought_leader"]
    
    @property
    def is_strategic_content(self) -> bool:
        """Check if content is strategic in nature."""
        return self.content_category in ["strategic", "policy", "governance"]
    
    @property
    def has_high_business_value(self) -> bool:
        """Check if content has high business impact."""
        return self.business_value in ["strategic", "governance", "innovation"]


class ContentStructure(BaseModel):
    """Analysis of content structure and logical flow."""
    # Structural elements (targeting 90% accuracy)
    has_clear_problem: bool = Field(default=False, description="Content clearly identifies a problem or question")
    has_evidence: bool = Field(default=False, description="Content provides supporting evidence or data")
    has_multiple_perspectives: bool = Field(default=False, description="Content considers multiple viewpoints or approaches")
    has_actionable_conclusions: bool = Field(default=False, description="Content provides actionable insights or recommendations")
    
    # Quality metrics
    logical_flow_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Quality of logical progression and flow")
    argument_coherence: float = Field(default=0.5, ge=0.0, le=1.0, description="Coherence and consistency of arguments")
    conclusion_strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Strength and validity of conclusions")
    
    @property
    def structure_quality_score(self) -> float:
        """Calculate overall structure quality score (0-1 scale)."""
        boolean_scores = [
            1.0 if self.has_clear_problem else 0.0,
            1.0 if self.has_evidence else 0.0,
            1.0 if self.has_multiple_perspectives else 0.0,
            1.0 if self.has_actionable_conclusions else 0.0
        ]
        boolean_avg = sum(boolean_scores) / len(boolean_scores)
        
        continuous_scores = [
            self.logical_flow_score,
            self.argument_coherence,
            self.conclusion_strength
        ]
        continuous_avg = sum(continuous_scores) / len(continuous_scores)
        
        # Weight: 60% structure elements, 40% quality metrics
        return (boolean_avg * 0.6) + (continuous_avg * 0.4)
    
    @property
    def is_well_structured(self) -> bool:
        """Check if content has good structural quality (>=0.7)."""
        return self.structure_quality_score >= 0.7
    
    @property
    def is_professionally_structured(self) -> bool:
        """Check if content meets professional structure standards (>=0.8)."""
        return self.structure_quality_score >= 0.8


class Note(BaseModel):
    """Represents a single note from the Obsidian vault."""
    file_path: Path = Field(..., description="Path to the note file")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Raw note content")
    content_type: ContentType = Field(..., description="Type of content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Note metadata")
    created_date: Optional[datetime] = Field(None, description="Creation date")
    modified_date: Optional[datetime] = Field(None, description="Last modification date")
    tags: List[str] = Field(default_factory=list, description="Note tags")
    source_url: Optional[str] = Field(None, description="Source URL if web clipping")
    
    @validator('title')
    def validate_title(cls, v):
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @property
    def word_count(self) -> int:
        """Calculate word count of content."""
        return len(self.content.split())
    
    @property
    def is_web_clipping(self) -> bool:
        """Check if note is a web clipping."""
        return self.content_type == ContentType.WEB_CLIPPING


class CurationResult(BaseModel):
    """Result of curating a single note."""
    note: Note = Field(..., description="Original note")
    cleaned_content: str = Field(..., description="Cleaned and processed content")
    quality_scores: QualityScore = Field(..., description="Quality assessment scores")
    themes: List[Theme] = Field(..., description="Identified themes")
    content_structure: Optional[ContentStructure] = Field(None, description="Analysis of content structure and logical flow")
    is_curated: bool = Field(..., description="Whether note meets curation criteria")
    curation_reason: str = Field(..., description="Reason for curation decision")
    processing_notes: List[str] = Field(default_factory=list, description="Processing notes and warnings")
    
    @property
    def primary_theme(self) -> Optional[Theme]:
        """Get the primary theme with highest confidence."""
        if not self.themes:
            return None
        return max(self.themes, key=lambda t: t.confidence)
    
    @property
    def professional_quality_summary(self) -> Dict[str, Any]:
        """Get comprehensive professional quality summary."""
        return {
            "overall_quality": self.quality_scores.overall,
            "professional_writing_score": self.quality_scores.professional_writing_score,
            "is_professional_quality": self.quality_scores.is_professional_quality,
            "is_thought_leadership": self.quality_scores.is_thought_leadership,
            "structure_quality": self.content_structure.structure_quality_score if self.content_structure else 0.0,
            "is_professionally_structured": self.content_structure.is_professionally_structured if self.content_structure else False,
            "expert_themes": [t for t in self.themes if t.is_expert_level],
            "strategic_content": [t for t in self.themes if t.is_strategic_content],
            "high_business_value": [t for t in self.themes if t.has_high_business_value]
        }


class TaskModels(BaseModel):
    """Task-specific model configuration for optimized performance."""
    
    content_curation: str = Field(default="phi3:mini", description="Model for binary content filtering decisions")
    quality_analysis: str = Field(default="llama3.1:8b", description="Model for quality scoring and analysis")
    theme_classification: str = Field(default="llama3.1:8b", description="Model for theme identification and categorization")
    structure_analysis: str = Field(default="phi3:mini", description="Model for content structure analysis")
    fallback: str = Field(default="gpt-oss:20b", description="Fallback model for complex edge cases")


class CurationConfig(BaseModel):
    """Configuration for the curation process."""
    ai_model: str = Field(default="gpt-oss:20b", description="Default/fallback AI model")
    models: TaskModels = Field(default_factory=TaskModels, description="Task-specific model configuration")
    reasoning_level: str = Field(default="low", description="AI reasoning level: low, medium, high")
    
    @validator('reasoning_level')
    def validate_reasoning_level(cls, v):
        """Validate reasoning level is one of the allowed values."""
        allowed_levels = {'low', 'medium', 'high'}
        if v.lower() not in allowed_levels:
            raise ValueError(f"Reasoning level must be one of: {', '.join(allowed_levels)}")
        return v.lower()
    quality_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum quality score for curation")
    relevance_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum relevance score for curation")
    analytical_depth_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum analytical depth for publication-ready content")
    professional_writing_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum professional writing score for curation")
    min_content_length: int = Field(default=300, ge=50, description="Minimum content length (characters) for useful notes")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens for AI analysis")
    target_themes: List[str] = Field(default_factory=list, description="Target themes to focus on")
    sample_size: Optional[int] = Field(default=None, gt=0, description="Number of notes to process (random sample for testing)")
    preserve_metadata: bool = Field(default=True, description="Whether to preserve original metadata")
    clean_html: bool = Field(default=True, description="Whether to clean HTML content")
    remove_duplicates: bool = Field(default=True, description="Whether to remove duplicate content")
    theme_similarity_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for fuzzy theme matching",
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class CurationStats(BaseModel):
    """Statistics about the curation process."""
    total_notes: int = Field(..., description="Total notes processed")
    curated_notes: int = Field(..., description="Number of notes that passed curation")
    rejected_notes: int = Field(..., description="Number of notes rejected")
    processing_time: float = Field(..., description="Total processing time in seconds")
    themes_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of themes")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of quality scores")
    
    # Professional quality statistics (NEW)
    professional_quality_stats: Dict[str, Any] = Field(default_factory=dict, description="Professional writing quality statistics")
    structure_quality_stats: Dict[str, Any] = Field(default_factory=dict, description="Content structure quality statistics")
    expertise_level_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of expertise levels")
    content_category_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of content categories")
    
    @property
    def curation_rate(self) -> float:
        """Calculate the percentage of notes that were curated."""
        if self.total_notes == 0:
            return 0.0
        return (self.curated_notes / self.total_notes) * 100
    
    @property
    def professional_writing_readiness(self) -> float:
        """Calculate overall professional writing readiness score (0-1 scale)."""
        if not self.professional_quality_stats:
            return 0.0
        
        avg_professional_score = self.professional_quality_stats.get('average_professional_score', 0.0)
        avg_structure_score = self.structure_quality_stats.get('average_structure_score', 0.0)
        
        # Weight: 70% professional quality, 30% structure quality
        return (avg_professional_score * 0.7) + (avg_structure_score * 0.3)
    
    @property
    def thought_leadership_rate(self) -> float:
        """Calculate percentage of notes demonstrating thought leadership."""
        if self.total_notes == 0:
            return 0.0
        
        thought_leadership_count = self.professional_quality_stats.get('thought_leadership_count', 0)
        return (thought_leadership_count / self.total_notes) * 100


class VaultStructure(BaseModel):
    """Structure of the curated vault."""
    root_path: Path = Field(..., description="Root path of curated vault")
    theme_folders: Dict[str, Path] = Field(default_factory=dict, description="Theme folder paths")
    metadata_folder: Path = Field(..., description="Metadata folder path")
    curation_log_path: Path = Field(..., description="Path to curation log")
    theme_analysis_path: Path = Field(..., description="Path to theme analysis")


class ProcessingCheckpoint(BaseModel):
    """Checkpoint for resuming interrupted processing."""
    timestamp: datetime = Field(default_factory=datetime.now, description="Checkpoint timestamp")
    processed_notes: List[str] = Field(default_factory=list, description="Paths of processed notes")
    total_notes: int = Field(..., description="Total notes to process")
    current_step: str = Field(..., description="Current processing step")
    config_hash: str = Field(..., description="Hash of configuration for validation")
    
    @property
    def progress(self) -> float:
        """Calculate progress percentage."""
        if self.total_notes == 0:
            return 0.0
        return (len(self.processed_notes) / self.total_notes) * 100
