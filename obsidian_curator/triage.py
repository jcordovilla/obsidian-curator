"""Borderline triage system for human-in-the-loop curation decisions."""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from .models import TriageItem, TriageConfig, QualityScore, CurationResult, Note


class TriageManager:
    """Manages borderline triage decisions for curation."""
    
    def __init__(self, config: TriageConfig):
        """Initialize the triage manager.
        
        Args:
            config: Triage configuration
        """
        self.config = config
        self.triage_file = Path(config.persist_path)
        self.pending_items: Dict[str, TriageItem] = {}
        self.resolved_items: Dict[str, TriageItem] = {}
        
        # Load existing triage decisions
        self._load_existing_decisions()
    
    def _load_existing_decisions(self) -> None:
        """Load existing triage decisions from file."""
        if not self.triage_file.exists():
            return
        
        try:
            with open(self.triage_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                        item = TriageItem(**data)
                        fingerprint = item.fingerprint or self._generate_fingerprint(item.note_path)
                        
                        if item.user_decision:
                            self.resolved_items[fingerprint] = item
                        else:
                            self.pending_items[fingerprint] = item
            
            logger.info(f"Loaded {len(self.resolved_items)} resolved and {len(self.pending_items)} pending triage items")
            
        except Exception as e:
            logger.warning(f"Failed to load triage decisions: {e}")
    
    def _generate_fingerprint(self, note_path: str, content: str = "") -> str:
        """Generate a fingerprint for a note to avoid re-asking.
        
        Args:
            note_path: Path to the note
            content: Optional content for more specific fingerprint
            
        Returns:
            Fingerprint string
        """
        # Use path and basic content hash
        fingerprint_data = f"{note_path}:{len(content)}:{hash(content[:200])}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:12]
    
    def needs_triage(self, note: Note, quality_scores: QualityScore, 
                    thresholds: Dict[str, float]) -> bool:
        """Check if a note needs human triage.
        
        Args:
            note: Note being evaluated
            quality_scores: AI quality scores
            thresholds: Configured thresholds
            
        Returns:
            True if triage is needed
        """
        if not self.config.enabled:
            return False
        
        # Check if we already have a decision for this note
        fingerprint = self._generate_fingerprint(str(note.file_path), note.content)
        if fingerprint in self.resolved_items:
            logger.debug(f"Skipping triage for {note.title} - already decided")
            return False
        
        # Check if any configured dimension is in the gray zone
        scores_dict = {
            "overall": quality_scores.overall,
            "relevance": quality_scores.relevance,
            "professional_writing": quality_scores.professional_writing_score,
            "analytical_depth": quality_scores.analytical_depth,
            "clarity": quality_scores.clarity,
            "credibility": quality_scores.credibility
        }
        
        for dimension in self.config.dimensions:
            if dimension in scores_dict and dimension in thresholds:
                score = scores_dict[dimension]
                threshold = thresholds[dimension]
                
                if abs(score - threshold) <= self.config.margin:
                    logger.info(f"Triage needed for {note.title}: {dimension} score {score:.3f} near threshold {threshold:.3f}")
                    return True
        
        return False
    
    def create_triage_item(self, note: Note, quality_scores: QualityScore,
                          thresholds: Dict[str, float], suggested_decision: str,
                          reason: str) -> TriageItem:
        """Create a triage item for human decision.
        
        Args:
            note: Note requiring triage
            quality_scores: AI quality scores
            thresholds: Configured thresholds
            suggested_decision: AI suggested decision
            reason: Reason for triage
            
        Returns:
            TriageItem object
        """
        fingerprint = self._generate_fingerprint(str(note.file_path), note.content)
        
        scores_dict = {
            "overall": quality_scores.overall,
            "relevance": quality_scores.relevance,
            "professional_writing": quality_scores.professional_writing_score,
            "analytical_depth": quality_scores.analytical_depth,
            "clarity": quality_scores.clarity,
            "credibility": quality_scores.credibility
        }
        
        triage_item = TriageItem(
            note_path=str(note.file_path),
            scores=scores_dict,
            thresholds=thresholds,
            decision_suggested=suggested_decision,
            reason=reason,
            fingerprint=fingerprint
        )
        
        self.pending_items[fingerprint] = triage_item
        self._persist_item(triage_item)
        
        logger.info(f"Created triage item for {note.title}")
        return triage_item
    
    def resolve_triage_item(self, fingerprint: str, user_decision: str) -> bool:
        """Resolve a triage item with human decision.
        
        Args:
            fingerprint: Item fingerprint
            user_decision: Human decision: "keep" or "discard"
            
        Returns:
            True if resolved successfully
        """
        if fingerprint not in self.pending_items:
            logger.warning(f"No pending triage item found for fingerprint {fingerprint}")
            return False
        
        item = self.pending_items[fingerprint]
        item.user_decision = user_decision
        item.decided_at = datetime.now().isoformat()
        
        # Move to resolved
        self.resolved_items[fingerprint] = item
        del self.pending_items[fingerprint]
        
        # Update persisted data
        self._persist_item(item)
        
        logger.info(f"Resolved triage item {fingerprint}: {user_decision}")
        return True
    
    def get_pending_items(self) -> List[TriageItem]:
        """Get all pending triage items.
        
        Returns:
            List of pending triage items
        """
        return list(self.pending_items.values())
    
    def get_decision(self, note: Note) -> Optional[str]:
        """Get existing decision for a note.
        
        Args:
            note: Note to check
            
        Returns:
            User decision if available, None otherwise
        """
        fingerprint = self._generate_fingerprint(str(note.file_path), note.content)
        if fingerprint in self.resolved_items:
            return self.resolved_items[fingerprint].user_decision
        return None
    
    def _persist_item(self, item: TriageItem) -> None:
        """Persist a triage item to file.
        
        Args:
            item: Triage item to persist
        """
        try:
            # Ensure directory exists
            self.triage_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to JSONL file
            with open(self.triage_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(item.dict()) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to persist triage item: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get triage statistics.
        
        Returns:
            Dictionary with triage stats
        """
        total_resolved = len(self.resolved_items)
        kept = sum(1 for item in self.resolved_items.values() if item.user_decision == "keep")
        discarded = sum(1 for item in self.resolved_items.values() if item.user_decision == "discard")
        
        return {
            "pending": len(self.pending_items),
            "resolved": total_resolved,
            "kept": kept,
            "discarded": discarded,
            "keep_rate": (kept / total_resolved * 100) if total_resolved > 0 else 0
        }
