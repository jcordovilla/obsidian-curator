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
    overall: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance to target themes")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Completeness of ideas")
    credibility: float = Field(..., ge=0.0, le=1.0, description="Credibility of source")
    clarity: float = Field(..., ge=0.0, le=1.0, description="Clarity of expression")
    
    @property
    def average_score(self) -> float:
        """Calculate average of all quality scores."""
        scores = [self.overall, self.relevance, self.completeness, self.credibility, self.clarity]
        return sum(scores) / len(scores)


class Theme(BaseModel):
    """A content theme or category."""
    name: str = Field(..., description="Theme name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in theme assignment")
    subthemes: List[str] = Field(default_factory=list, description="Sub-themes")
    keywords: List[str] = Field(default_factory=list, description="Keywords associated with theme")


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
    is_curated: bool = Field(..., description="Whether note meets curation criteria")
    curation_reason: str = Field(..., description="Reason for curation decision")
    processing_notes: List[str] = Field(default_factory=list, description="Processing notes and warnings")
    
    @property
    def primary_theme(self) -> Optional[Theme]:
        """Get the primary theme with highest confidence."""
        if not self.themes:
            return None
        return max(self.themes, key=lambda t: t.confidence)


class CurationConfig(BaseModel):
    """Configuration for the curation process."""
    ai_model: str = Field(default="gpt-oss:20b", description="AI model to use for analysis")
    reasoning_level: str = Field(default="low", description="AI reasoning level: low, medium, high")
    
    @validator('reasoning_level')
    def validate_reasoning_level(cls, v):
        """Validate reasoning level is one of the allowed values."""
        allowed_levels = {'low', 'medium', 'high'}
        if v.lower() not in allowed_levels:
            raise ValueError(f"Reasoning level must be one of: {', '.join(allowed_levels)}")
        return v.lower()
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum quality score for curation")
    relevance_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum relevance score for curation")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens for AI analysis")
    target_themes: List[str] = Field(default_factory=list, description="Target themes to focus on")
    sample_size: Optional[int] = Field(default=None, gt=0, description="Number of notes to process (random sample for testing)")
    preserve_metadata: bool = Field(default=True, description="Whether to preserve original metadata")
    clean_html: bool = Field(default=True, description="Whether to clean HTML content")
    remove_duplicates: bool = Field(default=True, description="Whether to remove duplicate content")
    
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
    
    @property
    def curation_rate(self) -> float:
        """Calculate the percentage of notes that were curated."""
        if self.total_notes == 0:
            return 0.0
        return (self.curated_notes / self.total_notes) * 100


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
