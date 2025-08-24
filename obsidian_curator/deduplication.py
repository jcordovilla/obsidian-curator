"""Duplicate and near-duplicate detection for content curation."""

import hashlib
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Set, Optional, Any

from loguru import logger

from .models import CurationResult, DeduplicationConfig


class DeduplicationManager:
    """Manages duplicate and near-duplicate detection."""
    
    def __init__(self, config: DeduplicationConfig):
        """Initialize the deduplication manager.
        
        Args:
            config: Deduplication configuration
        """
        self.config = config
        self.exact_hashes: Dict[str, CurationResult] = {}
        self.near_duplicate_clusters: List[List[CurationResult]] = []
        
        # Initialize MinHash if needed
        self.minhash_lsh = None
        if config.near.method == "minhash":
            try:
                from datasketch import MinHashLSH, MinHash
                self.MinHash = MinHash
                self.minhash_lsh = MinHashLSH(threshold=config.near.threshold, num_perm=128)
                logger.info("MinHash LSH initialized for near-duplicate detection")
            except ImportError:
                logger.warning("datasketch not available, falling back to difflib")
                config.near.method = "difflib"
    
    def normalize_content(self, content: str) -> str:
        """Normalize content for duplicate detection.
        
        Args:
            content: Raw content
            
        Returns:
            Normalized content
        """
        if not content:
            return ""
        
        # Remove excessive whitespace
        normalized = re.sub(r'\s+', ' ', content)
        
        # Remove common markdown artifacts
        normalized = re.sub(r'[#*_`\[\]]+', '', normalized)
        
        # Convert to lowercase
        normalized = normalized.lower().strip()
        
        return normalized
    
    def get_exact_hash(self, content: str) -> str:
        """Get SHA-256 hash for exact duplicate detection.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash
        """
        normalized = self.normalize_content(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def detect_duplicates(self, results: List[CurationResult]) -> Tuple[List[CurationResult], List[List[CurationResult]]]:
        """Detect exact and near duplicates in curation results.
        
        Args:
            results: List of curation results
            
        Returns:
            Tuple of (canonical_results, duplicate_clusters)
        """
        if not self.config.enabled:
            return results, []
        
        logger.info(f"Starting duplicate detection for {len(results)} results")
        
        # Phase 1: Exact duplicate detection
        exact_duplicates = {}
        canonical_results = []
        
        for result in results:
            if self.config.exact:
                content_hash = self.get_exact_hash(result.cleaned_content)
                
                if content_hash in exact_duplicates:
                    # This is an exact duplicate
                    canonical = exact_duplicates[content_hash]
                    
                    # Choose the better version as canonical
                    if self._is_better_version(result, canonical):
                        # Replace canonical
                        exact_duplicates[content_hash] = result
                        canonical_results = [r if r != canonical else result for r in canonical_results]
                        
                        # Mark old canonical as duplicate
                        canonical.is_duplicate = True
                        canonical.duplicate_info = {
                            "type": "exact",
                            "canonical_path": str(result.note.file_path),
                            "similarity": 1.0
                        }
                    else:
                        # Current result is duplicate
                        result.is_duplicate = True
                        result.duplicate_info = {
                            "type": "exact",
                            "canonical_path": str(canonical.note.file_path),
                            "similarity": 1.0
                        }
                else:
                    # First time seeing this content
                    exact_duplicates[content_hash] = result
                    canonical_results.append(result)
            else:
                canonical_results.append(result)
        
        logger.info(f"Exact duplicate detection: {len(canonical_results)} unique documents")
        
        # Phase 2: Near duplicate detection
        duplicate_clusters = []
        if self.config.near.method and len(canonical_results) > 1:
            duplicate_clusters = self._detect_near_duplicates(canonical_results)
            logger.info(f"Near duplicate detection: {len(duplicate_clusters)} clusters found")
        
        return canonical_results, duplicate_clusters
    
    def _is_better_version(self, result1: CurationResult, result2: CurationResult) -> bool:
        """Determine which result is the better canonical version.
        
        Args:
            result1: First result
            result2: Second result
            
        Returns:
            True if result1 is better than result2
        """
        # Priority 1: Higher overall quality score
        if result1.quality_scores.overall != result2.quality_scores.overall:
            return result1.quality_scores.overall > result2.quality_scores.overall
        
        # Priority 2: Higher professional writing score
        prof1 = result1.quality_scores.professional_writing_score
        prof2 = result2.quality_scores.professional_writing_score
        if prof1 != prof2:
            return prof1 > prof2
        
        # Priority 3: More recent modification date
        if result1.note.modified_date and result2.note.modified_date:
            return result1.note.modified_date > result2.note.modified_date
        
        # Priority 4: Longer content
        len1 = len(result1.cleaned_content)
        len2 = len(result2.cleaned_content)
        if len1 != len2:
            return len1 > len2
        
        # Default: keep first one
        return False
    
    def _detect_near_duplicates(self, results: List[CurationResult]) -> List[List[CurationResult]]:
        """Detect near duplicates using configured method.
        
        Args:
            results: List of results to check
            
        Returns:
            List of duplicate clusters
        """
        if self.config.near.method == "minhash" and self.minhash_lsh:
            return self._detect_near_duplicates_minhash(results)
        elif self.config.near.method == "simhash":
            return self._detect_near_duplicates_simhash(results)
        else:
            return self._detect_near_duplicates_difflib(results)
    
    def _detect_near_duplicates_minhash(self, results: List[CurationResult]) -> List[List[CurationResult]]:
        """Detect near duplicates using MinHash.
        
        Args:
            results: List of results to check
            
        Returns:
            List of duplicate clusters
        """
        try:
            result_to_minhash = {}
            
            # Create MinHash signatures
            for i, result in enumerate(results):
                minhash = self.MinHash(num_perm=128)
                
                # Create 5-word shingles
                normalized = self.normalize_content(result.cleaned_content)
                words = normalized.split()
                
                if len(words) < 5:
                    # Too short for meaningful shingles
                    continue
                
                for j in range(len(words) - 4):
                    shingle = ' '.join(words[j:j+5])
                    minhash.update(shingle.encode('utf-8'))
                
                result_to_minhash[i] = minhash
                self.minhash_lsh.insert(i, minhash)
            
            # Find clusters
            clusters = []
            processed = set()
            
            for i, result in enumerate(results):
                if i in processed or i not in result_to_minhash:
                    continue
                
                # Query for similar documents
                candidates = self.minhash_lsh.query(result_to_minhash[i])
                
                if len(candidates) > 1:
                    cluster = [results[j] for j in candidates if j not in processed]
                    if len(cluster) > 1:
                        clusters.append(cluster)
                        processed.update(candidates)
            
            return clusters
            
        except Exception as e:
            logger.warning(f"MinHash near-duplicate detection failed: {e}")
            return self._detect_near_duplicates_difflib(results)
    
    def _detect_near_duplicates_simhash(self, results: List[CurationResult]) -> List[List[CurationResult]]:
        """Detect near duplicates using SimHash.
        
        Args:
            results: List of results to check
            
        Returns:
            List of duplicate clusters
        """
        try:
            from simhash import Simhash
            
            result_to_simhash = {}
            
            # Create SimHash signatures
            for i, result in enumerate(results):
                normalized = self.normalize_content(result.cleaned_content)
                words = normalized.split()
                
                if len(words) < 10:
                    continue
                
                simhash = Simhash(words)
                result_to_simhash[i] = simhash
            
            # Find clusters based on Hamming distance
            clusters = []
            processed = set()
            
            for i, result in enumerate(results):
                if i in processed or i not in result_to_simhash:
                    continue
                
                cluster = [result]
                processed.add(i)
                
                for j, other_result in enumerate(results):
                    if j in processed or j not in result_to_simhash or i == j:
                        continue
                    
                    # Calculate similarity based on Hamming distance
                    distance = result_to_simhash[i].distance(result_to_simhash[j])
                    similarity = 1.0 - (distance / 64.0)  # 64-bit hash
                    
                    if similarity >= self.config.near.threshold:
                        cluster.append(other_result)
                        processed.add(j)
                
                if len(cluster) > 1:
                    clusters.append(cluster)
            
            return clusters
            
        except ImportError:
            logger.warning("simhash not available, falling back to difflib")
            return self._detect_near_duplicates_difflib(results)
        except Exception as e:
            logger.warning(f"SimHash near-duplicate detection failed: {e}")
            return self._detect_near_duplicates_difflib(results)
    
    def _detect_near_duplicates_difflib(self, results: List[CurationResult]) -> List[List[CurationResult]]:
        """Detect near duplicates using difflib (fallback method).
        
        Args:
            results: List of results to check
            
        Returns:
            List of duplicate clusters
        """
        clusters = []
        processed = set()
        
        for i, result in enumerate(results):
            if i in processed:
                continue
            
            cluster = [result]
            processed.add(i)
            
            content1 = self.normalize_content(result.cleaned_content)
            
            for j, other_result in enumerate(results):
                if j in processed or i == j:
                    continue
                
                content2 = self.normalize_content(other_result.cleaned_content)
                
                # Calculate similarity
                similarity = SequenceMatcher(None, content1, content2).ratio()
                
                if similarity >= self.config.near.threshold:
                    cluster.append(other_result)
                    processed.add(j)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def mark_duplicates_in_clusters(self, clusters: List[List[CurationResult]]) -> None:
        """Mark duplicates in clusters and set canonical versions.
        
        Args:
            clusters: List of duplicate clusters
        """
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            
            # Sort cluster to find best canonical version
            cluster.sort(key=lambda r: (
                r.quality_scores.overall,
                r.quality_scores.professional_writing_score,
                r.note.modified_date or 0,
                len(r.cleaned_content)
            ), reverse=True)
            
            canonical = cluster[0]
            duplicates = cluster[1:]
            
            # Mark duplicates
            for dup in duplicates:
                dup.is_duplicate = True
                dup.duplicate_info = {
                    "type": "near",
                    "canonical_path": str(canonical.note.file_path),
                    "similarity": self._calculate_similarity(canonical.cleaned_content, dup.cleaned_content),
                    "cluster_size": len(cluster)
                }
            
            # Add duplicate list to canonical's metadata
            if self.config.write_aliases:
                if not canonical.duplicate_info:
                    canonical.duplicate_info = {"duplicates": []}
                
                canonical.duplicate_info["duplicates"] = [
                    {
                        "path": str(dup.note.file_path),
                        "similarity": dup.duplicate_info["similarity"]
                    }
                    for dup in duplicates
                ]
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings.
        
        Args:
            content1: First content
            content2: Second content
            
        Returns:
            Similarity score between 0 and 1
        """
        norm1 = self.normalize_content(content1)
        norm2 = self.normalize_content(content2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def generate_duplicate_report(self, clusters: List[List[CurationResult]], output_path: str) -> None:
        """Generate a report of duplicate clusters.
        
        Args:
            clusters: List of duplicate clusters
            output_path: Path to write the report
        """
        try:
            from pathlib import Path
            
            report_lines = [
                "# Duplicate Detection Report",
                "",
                f"Generated on: {self._get_timestamp()}",
                f"Configuration: {self.config.dict()}",
                "",
                f"## Summary",
                "",
                f"- **Total Clusters**: {len(clusters)}",
                f"- **Total Duplicates**: {sum(len(cluster) - 1 for cluster in clusters)}",
                "",
                "## Duplicate Clusters",
                ""
            ]
            
            for i, cluster in enumerate(clusters):
                canonical = cluster[0]
                duplicates = cluster[1:]
                
                report_lines.extend([
                    f"### Cluster {i + 1}",
                    "",
                    f"**Canonical**: {canonical.note.title}",
                    f"- Path: `{canonical.note.file_path}`",
                    f"- Quality: {canonical.quality_scores.overall:.3f}",
                    "",
                    "**Duplicates**:",
                    ""
                ])
                
                for dup in duplicates:
                    similarity = dup.duplicate_info.get("similarity", 0.0)
                    report_lines.extend([
                        f"- {dup.note.title}",
                        f"  - Path: `{dup.note.file_path}`",
                        f"  - Similarity: {similarity:.3f}",
                        f"  - Quality: {dup.quality_scores.overall:.3f}",
                        ""
                    ])
                
                report_lines.append("")
            
            # Write report
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text('\n'.join(report_lines), encoding='utf-8')
            
            logger.info(f"Duplicate report written to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate duplicate report: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for reporting."""
        from datetime import datetime
        return datetime.now().isoformat()
