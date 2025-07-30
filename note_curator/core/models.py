"""Data models for the note classification system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class PillarType(str, Enum):
    """Expert knowledge pillars."""
    PPP_FUNDAMENTALS = "ppp_fundamentals"
    OPERATIONAL_RISK = "operational_risk"
    VALUE_FOR_MONEY = "value_for_money"
    DIGITAL_TRANSFORMATION = "digital_transformation"
    GOVERNANCE_TRANSPARENCY = "governance_transparency"


class NoteType(str, Enum):
    """Types of notes."""
    LITERATURE_RESEARCH = "literature_research"
    PROJECT_WORKFLOW = "project_workflow"
    PERSONAL_REFLECTION = "personal_reflection"
    TECHNICAL_CODE = "technical_code"
    MEETING_TEMPLATE = "meeting_template"
    COMMUNITY_EVENT = "community_event"


class CurationAction(str, Enum):
    """Possible curation actions."""
    KEEP = "keep"
    REFINE = "refine"
    ARCHIVE = "archive"
    DELETE = "delete"


class QualityScore(BaseModel):
    """Quality assessment scores."""
    relevance: float = Field(ge=0.0, le=1.0, description="Relevance to expert domains")
    depth: float = Field(ge=0.0, le=1.0, description="Depth of analysis")
    actionability: float = Field(ge=0.0, le=1.0, description="Actionability")
    uniqueness: float = Field(ge=0.0, le=1.0, description="Uniqueness of insight")
    structure: float = Field(ge=0.0, le=1.0, description="Structure and organization")
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall score."""
        weights = {
            'relevance': 0.3,
            'depth': 0.25,
            'actionability': 0.2,
            'uniqueness': 0.15,
            'structure': 0.1
        }
        return sum(getattr(self, attr) * weight for attr, weight in weights.items())


class PillarAnalysis(BaseModel):
    """Analysis of a note's relevance to a specific pillar."""
    pillar: PillarType
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    keywords_found: List[str] = Field(default_factory=list)


class NoteAnalysis(BaseModel):
    """Complete analysis of a note."""
    file_path: Path
    file_name: str
    file_size: int
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    
    # Content analysis
    word_count: int
    character_count: int
    has_frontmatter: bool
    has_attachments: bool
    attachment_count: int = 0
    
    # Classification
    primary_pillar: Optional[PillarType] = None
    secondary_pillars: List[PillarType] = Field(default_factory=list)
    note_type: Optional[NoteType] = None
    
    # Quality assessment
    quality_scores: QualityScore
    
    # Pillar analysis
    pillar_analyses: List[PillarAnalysis] = Field(default_factory=list)
    
    # Curation decision
    curation_action: CurationAction
    curation_reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Metadata
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str = "llama-3.1-8b-instruct"
    
    @property
    def overall_score(self) -> float:
        """Get the overall quality score."""
        return self.quality_scores.overall_score
    
    @property
    def is_high_value(self) -> bool:
        """Check if note is high value (score > 0.7)."""
        return self.overall_score > 0.7
    
    @property
    def needs_refinement(self) -> bool:
        """Check if note needs refinement (score 0.5-0.7)."""
        return 0.5 <= self.overall_score <= 0.7


class ProcessingBatch(BaseModel):
    """A batch of notes being processed."""
    batch_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: List[NoteAnalysis] = Field(default_factory=list)
    total_notes: int = 0
    processed_notes: int = 0
    failed_notes: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_notes == 0:
            return 0.0
        return (self.processed_notes - self.failed_notes) / self.total_notes


class ClassificationResults(BaseModel):
    """Complete classification results."""
    vault_path: Path
    processing_date: datetime = Field(default_factory=datetime.now)
    total_notes_processed: int
    batches: List[ProcessingBatch] = Field(default_factory=list)
    
    # Summary statistics
    notes_by_action: Dict[CurationAction, int] = Field(default_factory=dict)
    notes_by_pillar: Dict[PillarType, int] = Field(default_factory=dict)
    notes_by_type: Dict[NoteType, int] = Field(default_factory=dict)
    
    # Quality distribution
    high_value_notes: int = 0
    medium_value_notes: int = 0
    low_value_notes: int = 0
    
    @property
    def average_quality_score(self) -> float:
        """Calculate average quality score across all notes."""
        if not self.batches:
            return 0.0
        
        all_notes = []
        for batch in self.batches:
            all_notes.extend(batch.notes)
        
        if not all_notes:
            return 0.0
        
        return sum(note.overall_score for note in all_notes) / len(all_notes)


@dataclass
class ProcessingConfig:
    """Configuration for note processing."""
    max_notes_per_batch: int = 20
    max_note_chars: int = 3000
    process_attachments: bool = False
    include_frontmatter: bool = True
    detailed_logging: bool = True 